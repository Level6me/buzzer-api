import asyncio
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from buzzer import Buzzer
from melodies import MELODIES

app = FastAPI(title='Raspberry Pi Buzzer API', version='1.1.0')
buzzer = Buzzer()
play_lock = asyncio.Lock()
API_TOKEN = os.environ.get('BUZZER_API_TOKEN', '')
MAX_DUTY = 0.3  # volume=100 时对应的占空比（避免破音）


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
    volume: int | None = None
    duty: float | None = None

class MelodyRequest(BaseModel):
    name: str | None = None
    notes: list | None = None
    volume: int | None = None
    duty: float | None = None

@app.middleware('http')
async def token_check(request, call_next):
    if API_TOKEN:
        if request.headers.get('X-API-Token') != API_TOKEN:
            from fastapi.responses import JSONResponse
            return JSONResponse({'error': 'unauthorized'}, status_code=401)
    return await call_next(request)

@app.get('/health')
async def health():
    return {'status': 'ok'}

@app.get('/api/melodies')
async def list_melodies():
    return {'melodies': list(MELODIES.keys())}

@app.post('/api/play/tone')
async def play_tone(req: ToneRequest):
    if not (20 <= req.frequency <= 5000):
        raise HTTPException(400, 'frequency must be 20-5000 Hz')
    if req.volume is not None and not (0 <= req.volume <= 100):
        raise HTTPException(400, 'volume must be 0-100')
    async with play_lock:
        duty = resolve_duty(req.volume, req.duty)
        await asyncio.to_thread(buzzer.play_tone, req.frequency, req.duration, duty)
    return {'ok': True, 'frequency': req.frequency, 'duration': req.duration}

@app.post('/api/play/melody')
async def play_melody(req: MelodyRequest):
    if req.name:
        if req.name not in MELODIES:
            raise HTTPException(404, f'melody not found: {req.name}')
        notes = MELODIES[req.name]
    elif req.notes:
        notes = req.notes
    else:
        raise HTTPException(400, 'provide name or notes')
    if req.volume is not None and not (0 <= req.volume <= 100):
        raise HTTPException(400, 'volume must be 0-100')
    async with play_lock:
        duty = resolve_duty(req.volume, req.duty)
        await asyncio.to_thread(buzzer.play_melody, notes, duty)
    return {'ok': True, 'melody': req.name or 'custom'}

@app.post('/api/stop')
async def stop():
    await asyncio.to_thread(buzzer.stop)
    return {'ok': True}

@app.get('/api/status')
async def status():
    return {'gpio': 18, 'melodies': list(MELODIES.keys())}
