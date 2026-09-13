# Raspberry Pi Buzzer API

树莓派 GPIO18（硬件 PWM）驱动的蜂鸣器/喇叭播放 API。其他服务（飞书 bot、Web 前端、自动化脚本）通过 HTTP 即可触发播放旋律、提示音或自定义音符序列。

---

## 目录

- [Web 控制台 (Web Console)](#web-控制台-web-console)
- [硬件接线](#硬件接线)
- [音量与音质](#音量与音质)
- [部署](#部署)
- [API 文档](#api-文档)
- [调用示例](#调用示例)
- [故障排查](#故障排查)
- [扩展](#扩展)

---

## Web 控制台 (Web Console)

本项目内置了类似 `pi_led_api` 的 Apple 风格毛玻璃极简现代 **Web 控制台**，部署后直接在局域网浏览器打开即可使用：

* **访问地址**：`http://<树莓派IP>:8001/` 或 `http://127.0.0.1:8001/`
* **核心功能模块**：
  1. **实时音频示波器与状态监控**：实时捕捉发声状态，动态绘制音频方波/正弦示波动画，呈现树莓派 CPU 温度、负载与系统运行指标；
  2. **预设旋律一键点播**：包含单哔、双哔、系统通知、成功、失败、紧急告警、超级马里奥、星球大战、俄罗斯方块、欢乐颂、小星星等丰富预设，支持全局音量无级滑动调节；
  3. **双八度交互式钢琴键盘 (C4 ~ B5)**：支持触控与电脑物理键盘快捷键（A~K 键白键，W/E/T/Y/U 黑键）实时弹奏硬件发声；
  4. **单音频信号发生器**：20Hz ~ 5000Hz 连续频点无级调节，支持 440Hz、1000Hz 等快捷预设芯片；
  5. **自定义旋律编曲器**：支持在线可视化编曲及 JSON 序列实时试听；
  6. **API 调试与 Token 密钥管理**：内置一键复制 cURL / Python 代码，支持保存 `X-API-Token` 到本地浏览器；
  7. **审计日志追踪**：实时滚动记录最近 50 条音频播放与操作来源记录。

---

## 硬件接线

模块为 PH2.0 三线制（G / V / S）：

| 引脚 | 模块 | 树莓派 |
|---|---|---|
| G | 电源负极 | GND（如 40Pin 第 6 脚） |
| V | 电源正极（3.3–5.5V） | 3.3V（第 1 脚）或 5V（第 2 脚） |
| S | 信号输入 | **GPIO18（物理第 12 脚）** |

> 本服务将 GPIO18 设为 **ALT5（PWM0）**，信号由树莓派硬件 PWM 驱动。

### 前置系统配置（必须，否则无声）

1. **禁用板载音频**（3.5mm 口占用 GPIO18/19）：
   ```bash
   sudo sed -i 's/^dtparam=audio=on$/#dtparam=audio=on/' /boot/firmware/config.txt
   ```
2. **启用硬件 PWM 并把 PWM0 指定到 GPIO18**：
   ```bash
   echo "dtoverlay=pwm-2chan,pins_0=18,pins_1=19" | sudo tee -a /boot/firmware/config.txt
   ```
3. **重启**：`sudo reboot`
4. 重启后确认：
   ```bash
   ls /sys/class/pwm/                 # 应出现 pwmchip0
   sudo raspi-gpio set 18 a5          # 运行时把 GPIO18 设为 PWM0（服务每次播放也会自动执行）
   ```

> ⚠️ 如果树莓派上有其他 GPIO 服务（如 `CyberPi-GPIO-Commander`，用 LGPIO 声明全部引脚），会占用 GPIO18 导致 PWM 不可用，需先停止（`pm2 stop cyberpi-gpio`）。

---

## 音量与音质

蜂鸣器音量由 **占空比（`duty`）** 控制：**值越小，声音越小、越干净**；值越大越响，但容易破音。

### 常用 duty 对照

| duty | 音量 | 音质 |
|---|---|---|
| 0.01（1%） | 很小 | 干净 |
| 0.03（3%） | 小 | 干净（推荐默认） |
| 0.05（5%） | 较小 | 干净 |
| 0.1（10%） | 中等 | 良好（当前服务默认） |
| 0.2（20%） | 较大 | 开始有谐波/破音 |
| 0.3（30%）+ | 大 | 破音明显 |

### 如何调音量

**推荐：用 `volume`（0–100 百分比）**——服务自动换算为占空比（100 对应占空比 0.3，避免破音）：

```bash
# 20% 音量播放提示音
curl -X POST http://127.0.0.1:8001/api/play/tone \
  -H "Content-Type: application/json" \
  -d '{"frequency":1000,"duration":0.3,"volume":20}'

# 60% 音量播放旋律
curl -X POST http://127.0.0.1:8001/api/play/melody \
  -H "Content-Type: application/json" \
  -d '{"name":"ode_to_joy","volume":60}'
```

**或直接指定占空比 `"duty"`**（更精细，`duty` 优先于 `volume`）：

```bash
# 小音量播放提示音
curl -X POST http://127.0.0.1:8001/api/play/tone \
  -H "Content-Type: application/json" \
  -d '{"frequency":1000,"duration":0.3,"duty":0.03}'
```

**永久（改服务默认值）**：编辑 `buzzer.py` 里的 `Buzzer(duty_default=0.1)` 为想要的默认值（如 `0.03`），然后重启：

```bash
sudo systemctl restart buzzer-api
```

### 关于"破音"

- 破音主要来自**软件 PWM 频率抖动**和**音符切换瞬态**；本服务已改用**硬件 PWM**（GPIO18 = PWM0），大幅改善；
- 若仍感觉不干净，把 `duty` 降到 0.03–0.05 即可；
- 蜂鸣器本身是"单音+谐波"设备，适合提示音/简单旋律；要高质量音频需外接 DAC/功放。

---

## 部署

```bash
cd ~/buzzer-api
python3 -m venv venv
./venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi uvicorn

sudo cp buzzer-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now buzzer-api
```

- 服务监听 **`127.0.0.1:8001`**（仅本机）；
- 以 **root** 运行（需要写 `/sys/class/pwm` 和执行 `raspi-gpio`）；
- 开机自启（`systemctl enable`）。

常用管理命令：

```bash
sudo systemctl status buzzer-api   # 状态
sudo systemctl restart buzzer-api  # 重启
sudo systemctl stop buzzer-api     # 停止
journalctl -u buzzer-api -n 50     # 日志
```

---

## API 文档

### 端点总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/melodies` | 预置旋律列表 |
| GET | `/api/status` | 服务状态 |
| POST | `/api/play/melody` | 播放旋律（预置或自定义） |
| POST | `/api/play/tone` | 播放单音（提示音） |
| POST | `/api/stop` | 立即停止播放 |

### `POST /api/play/tone`

播放单个频率的音。

请求体：

```json
{
  "frequency": 1000,
  "duration": 0.3,
  "duty": 0.1
}
```

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `frequency` | number | 是 | 频率（Hz），范围 20–5000 |
| `duration` | number | 否 | 时长（秒），默认 0.5 |
| `volume` | int | 否 | 音量百分比 0–100（推荐，自动换算占空比） |
| `duty` | number | 否 | 占空比 0–1，默认 0.1（见[音量与音质](#音量与音质)） |

响应：

```json
{"ok": true, "frequency": 1000.0, "duration": 0.3}
```

### `POST /api/play/melody`

播放旋律。两种模式：预置旋律（`name`）或自定义音符序列（`notes`）。

**播放预置旋律：**

```json
{"name": "ode_to_joy", "duty": 0.1}
```

**自定义旋律：**

```json
{
  "notes": [["C4", 0.4], ["E4", 0.4], ["G4", 0.4], ["C5", 0.8]],
  "duty": 0.1
}
```

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 二选一 | 预置旋律名，见 `/api/melodies` |
| `notes` | array | 二选一 | 音符序列 `[[音符或频率, 时长秒], ...]` |
| `volume` | int | 否 | 音量百分比 0–100（推荐） |
| `duty` | number | 否 | 占空比，默认 0.1 |

支持的音符名：

```
C4=262  D4=294  E4=330  F4=349  G4=392  A4=440  B4=494  C5=523  D5=587
```

也可以直接用频率数字：`[[440, 0.5], [523, 0.5]]`。

### `POST /api/stop`

立即停止当前播放（无请求体）。

### 错误响应

| 状态码 | 场景 |
|---|---|
| 400 | 频率越界 / 未提供 `name` 或 `notes` |
| 404 | 预置旋律不存在 |
| 401 | 未提供正确的 `X-API-Token`（启用 token 后） |

错误响应格式：

```json
{"detail": "melody not found: xxx"}
```

---

## 调用示例

**播放预置旋律《欢乐颂》：**

```bash
curl -X POST http://127.0.0.1:8001/api/play/melody \
  -H "Content-Type: application/json" \
  -d '{"name":"ode_to_joy","duty":0.03}'
```

**播放《小星星》：**

```bash
curl -X POST http://127.0.0.1:8001/api/play/melody \
  -H "Content-Type: application/json" \
  -d '{"name":"twinkle","duty":0.03}'
```

**提示音（如告警）：**

```bash
curl -X POST http://127.0.0.1:8001/api/play/tone \
  -H "Content-Type: application/json" \
  -d '{"frequency":1000,"duration":0.3,"duty":0.03}'
```

**自定义旋律：**

```bash
curl -X POST http://127.0.0.1:8001/api/play/melody \
  -H "Content-Type: application/json" \
  -d '{"notes":[["C4",0.4],["E4",0.4],["G4",0.4],["C5",0.8]],"duty":0.03}'
```

**Python（requests）：**

```python
import requests

requests.post(
    "http://127.0.0.1:8001/api/play/melody",
    json={"name": "ode_to_joy", "duty": 0.03},
)
```

**飞书 bot / 自动化：** 直接在同机调用上述接口即可（同机免认证）。

---

## 故障排查

### 完全没有声音

1. 检查 GPIO18 是否为 PWM 功能：
   ```bash
   raspi-gpio get 18
   # 期望输出：18: a5 ... (PWM0_0)
   # 如果是 "op"（普通输出），执行：sudo raspi-gpio set 18 a5
   ```
2. 检查 PWM 通道：
   ```bash
   ls /sys/class/pwm/   # 应有 pwmchip0
   ```
3. 检查板载音频是否禁用（`dtparam=audio=on` 已注释）；
4. 检查是否有其他服务占用 GPIO18（如 `CyberPi-GPIO-Commander`）：
   ```bash
   pm2 list | grep -i cyber
   # 若有：pm2 stop cyberpi-gpio
   ```
5. 检查接线：G→GND、V→3.3V/5V、S→GPIO18；
6. 有源蜂鸣器只响/不响（不受频率控制）；确认是无源蜂鸣器/喇叭。

### 声音小

调大 `duty`（0.1–0.2）；或确认 V 接的是 5V（而非 3.3V）。

### 破音 / 杂音

调低 `duty`（0.03–0.05）；确认使用硬件 PWM（GPIO18 为 `a5`）。

---

## 扩展

### 启用 token（外部访问）

编辑 `/etc/systemd/system/buzzer-api.service`，在 `[Service]` 加环境变量，并把绑定改为 `0.0.0.0`：

```ini
Environment=BUZZER_API_TOKEN=你的token
ExecStart=/home/user/buzzer-api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
```

重启后请求需带请求头：

```bash
curl -X POST http://<树莓派IP>:8001/api/play/tone \
  -H "Content-Type: application/json" \
  -H "X-API-Token: 你的token" \
  -d '{"frequency":1000,"duration":0.3}'
```

> 开放外部访问前请务必设置 token，并确认树莓派防火墙/安全组。

### 目录结构

```
buzzer-api/
├── main.py            # FastAPI 应用与路由
├── buzzer.py          # 硬件 PWM 播放核心（sysfs + raspi-gpio）
├── melodies.py        # 音符表与预置旋律
├── requirements.txt
├── buzzer-api.service # systemd 单元
└── README.md
```
