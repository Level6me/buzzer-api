import asyncio
import collections
import json
import os
import time
from typing import Optional, List, Any, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from buzzer import Buzzer, NOTES
from melodies import MELODIES, MELODY_META

app = FastAPI(title='Raspberry Pi Buzzer API & Web Console', version='2.0.0')
buzzer = Buzzer()
play_lock = asyncio.Lock()
API_TOKEN = os.environ.get('BUZZER_API_TOKEN', '')
MAX_DUTY = 0.3  # volume=100 时对应的占空比（避免破音）

# SSE 广播订阅管理
main_event_loop: Optional[asyncio.AbstractEventLoop] = None
sse_subscribers: set = set()

def on_buzzer_status_change(status_dict):
    global main_event_loop
    if main_event_loop and not main_event_loop.is_closed():
        for q in list(sse_subscribers):
            try:
                main_event_loop.call_soon_threadsafe(
                    lambda queue=q, data=status_dict: queue.put_nowait(data) if not queue.full() else None
                )
            except Exception:
                pass

buzzer.add_listener(on_buzzer_status_change)

@app.on_event('startup')
async def on_startup():
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()

# 内存日志队列（保留最近 50 条播放记录）
history_log = collections.deque(maxlen=50)

def record_history(event_type: str, detail: str, duration: float, volume: Optional[int], duty: Optional[float], client_ip: str):
    record = {
        'id': f"log_{int(time.time() * 1000)}",
        'time': time.strftime('%H:%M:%S'),
        'type': event_type,
        'detail': detail,
        'duration': round(duration, 2) if duration else None,
        'volume': volume if volume is not None else (int((duty or 0.1) / MAX_DUTY * 100) if duty else 33),
        'duty': round(duty, 4) if duty is not None else None,
        'client': client_ip or '127.0.0.1'
    }
    history_log.appendleft(record)


def get_system_metrics():
    """获取树莓派底层硬件与运行指标"""
    metrics = {
        'temperature': 0.0,
        'load_avg': [0.0, 0.0, 0.0],
        'memory_used_mb': 0,
        'memory_total_mb': 0,
        'uptime_hours': 0.0,
    }
    try:
        # 温度
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                metrics['temperature'] = round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass

    try:
        # 负载
        if os.path.exists('/proc/loadavg'):
            with open('/proc/loadavg', 'r') as f:
                parts = f.read().strip().split()
                metrics['load_avg'] = [float(parts[0]), float(parts[1]), float(parts[2])]
    except Exception:
        pass

    try:
        # 内存
        if os.path.exists('/proc/meminfo'):
            mem = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    p = line.split(':')
                    if len(p) == 2:
                        k = p[0].strip()
                        v = p[1].strip().split()[0]
                        mem[k] = int(v)
            total = mem.get('MemTotal', 0) // 1024
            avail = mem.get('MemAvailable', 0) // 1024
            metrics['memory_total_mb'] = total
            metrics['memory_used_mb'] = max(0, total - avail)
    except Exception:
        pass

    try:
        # 运行时长
        if os.path.exists('/proc/uptime'):
            with open('/proc/uptime', 'r') as f:
                up_sec = float(f.read().split()[0])
                metrics['uptime_hours'] = round(up_sec / 3600.0, 1)
    except Exception:
        pass

    return metrics


def resolve_duty(volume=None, duty=None):
    """音量百分比(0-100) → 占空比；显式 duty 优先。"""
    if duty is not None:
        return duty
    if volume is not None:
        return min(MAX_DUTY, max(0.005, volume / 100 * MAX_DUTY))
    return None


class ToneRequest(BaseModel):
    frequency: float
    duration: float = 0.5
    volume: Optional[int] = None
    duty: Optional[float] = None


class MelodyRequest(BaseModel):
    name: Optional[str] = None
    notes: Optional[List[Any]] = None
    volume: Optional[int] = None
    duty: Optional[float] = None


@app.middleware('http')
async def token_check(request: Request, call_next):
    # 静态文件、根路径与只读状态/SSE接口免 Token 验证
    path = request.url.path
    if (path == '/' or 
        path == '/health' or 
        path == '/api/status' or 
        path == '/api/events' or 
        path == '/api/melodies' or 
        path == '/api/notes' or 
        path == '/api/system' or 
        path == '/api/history' or 
        path.startswith('/static') or 
        path == '/favicon.ico'):
        return await call_next(request)

    if API_TOKEN:
        token = request.headers.get('X-API-Token') or request.query_params.get('token')
        if token != API_TOKEN:
            return JSONResponse({'error': 'unauthorized', 'message': 'Invalid or missing API Token'}, status_code=401)
            
    return await call_next(request)


# 挂载静态文件目录
static_dir = os.path.join(os.path.dirname(__file__), 'public')
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.get('/')
async def index():
    index_file = os.path.join(static_dir, 'index.html')
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {'message': 'Raspberry Pi Buzzer API is running. Web UI not generated yet.'}


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/api/status')
async def status():
    st = buzzer.get_status()
    st['token_required'] = bool(API_TOKEN)
    st['system'] = get_system_metrics()
    return st


@app.get('/api/events')
async def events_stream(request: Request):
    """Server-Sent Events (SSE) 实时毫秒级推送蜂鸣器频率/波形/音符及系统指标"""
    q = asyncio.Queue(maxsize=50)
    sse_subscribers.add(q)

    # 初次连接时推送一次当前完整状态
    init_state = buzzer.get_status()
    init_state['token_required'] = bool(API_TOKEN)
    init_state['system'] = get_system_metrics()
    await q.put(init_state)

    async def event_generator():
        last_sys_heartbeat = time.time()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    now = time.time()
                    if now - last_sys_heartbeat >= 2.5:
                        last_sys_heartbeat = now
                        heartbeat = buzzer.get_status()
                        heartbeat['token_required'] = bool(API_TOKEN)
                        heartbeat['system'] = get_system_metrics()
                        yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
                    else:
                        yield f": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            sse_subscribers.discard(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get('/api/system')
async def system_metrics():
    return get_system_metrics()


@app.get('/api/notes')
async def list_notes():
    return {'notes': NOTES}


@app.get('/api/melodies')
async def list_melodies():
    melodies_data = []
    for k, v in MELODIES.items():
        meta = MELODY_META.get(k, {})
        est_duration = sum(item[1] for item in v if isinstance(item, (list, tuple)) and len(item) >= 2)
        melodies_data.append({
            'id': k,
            'title': meta.get('title', k),
            'category': meta.get('category', '自定义'),
            'desc': meta.get('desc', f'{len(v)} 个音符序列'),
            'icon': meta.get('icon', '🎵'),
            'note_count': len(v),
            'duration': round(meta.get('duration', est_duration), 2),
            'notes': v
        })
    return {'melodies': melodies_data}


@app.get('/api/history')
async def get_history():
    return {'history': list(history_log)}


@app.post('/api/play/tone')
async def play_tone(req: ToneRequest, request: Request):
    if not (20 <= req.frequency <= 5000):
        raise HTTPException(400, 'frequency must be 20-5000 Hz')
    if req.volume is not None and not (0 <= req.volume <= 100):
        raise HTTPException(400, 'volume must be 0-100')

    client_ip = request.client.host if request.client else '127.0.0.1'
    duty = resolve_duty(req.volume, req.duty)
    record_history('单音 (Tone)', f'{int(req.frequency)} Hz', req.duration, req.volume, duty, client_ip)

    async with play_lock:
        await asyncio.to_thread(buzzer.play_tone, req.frequency, req.duration, duty)
    return {'ok': True, 'frequency': req.frequency, 'duration': req.duration}


@app.post('/api/play/melody')
async def play_melody(req: MelodyRequest, request: Request):
    melody_title = req.name or '自定义旋律'
    if req.name:
        if req.name not in MELODIES:
            raise HTTPException(404, f'melody not found: {req.name}')
        notes = MELODIES[req.name]
        meta = MELODY_META.get(req.name, {})
        melody_title = meta.get('title', req.name)
    elif req.notes:
        notes = req.notes
    else:
        raise HTTPException(400, 'provide name or notes')

    if req.volume is not None and not (0 <= req.volume <= 100):
        raise HTTPException(400, 'volume must be 0-100')

    est_duration = sum(item[1] for item in notes if isinstance(item, (list, tuple)) and len(item) >= 2)
    client_ip = request.client.host if request.client else '127.0.0.1'
    duty = resolve_duty(req.volume, req.duty)
    record_history('旋律 (Melody)', melody_title, est_duration, req.volume, duty, client_ip)

    async with play_lock:
        await asyncio.to_thread(buzzer.play_melody, notes, duty, melody_title)
    return {'ok': True, 'melody': melody_title, 'notes_count': len(notes)}


@app.post('/api/stop')
async def stop(request: Request):
    client_ip = request.client.host if request.client else '127.0.0.1'
    record_history('操作 (Control)', '紧急静音/停止', 0, 0, 0, client_ip)
    await asyncio.to_thread(buzzer.stop)
    return {'ok': True, 'message': 'Buzzer playback stopped'}
