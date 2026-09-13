"""Preset melodies and metadata for Raspberry Pi Buzzer API."""

ODE_TO_JOY = [
    ('E4', 0.4), ('E4', 0.4), ('F4', 0.4), ('G4', 0.4),
    ('G4', 0.4), ('F4', 0.4), ('E4', 0.4), ('D4', 0.4),
    ('C4', 0.4), ('C4', 0.4), ('D4', 0.4), ('E4', 0.4),
    ('E4', 0.6), ('D4', 0.2), ('D4', 0.8),
    ('E4', 0.4), ('E4', 0.4), ('F4', 0.4), ('G4', 0.4),
    ('G4', 0.4), ('F4', 0.4), ('E4', 0.4), ('D4', 0.4),
    ('C4', 0.4), ('C4', 0.4), ('D4', 0.4), ('E4', 0.4),
    ('D4', 0.6), ('C4', 0.2), ('C4', 0.8),
]

TWINKLE = [
    ('C4', 0.35), ('C4', 0.35), ('G4', 0.35), ('G4', 0.35),
    ('A4', 0.35), ('A4', 0.35), ('G4', 0.7),
    ('F4', 0.35), ('F4', 0.35), ('E4', 0.35), ('E4', 0.35),
    ('D4', 0.35), ('D4', 0.35), ('C4', 0.7),
]

NOTIFY = [
    ('C5', 0.12), ('G4', 0.12), ('C5', 0.12), ('G4', 0.25)
]

BEEP = [
    ('C5', 0.15)
]

TWO_BEEPS = [
    ('C5', 0.1), ('REST', 0.08), ('C5', 0.1)
]

SUCCESS = [
    ('C4', 0.1), ('E4', 0.1), ('G4', 0.1), ('C5', 0.3)
]

ERROR = [
    ('F4', 0.12), ('D4', 0.12), ('C4', 0.12), ('A3', 0.3)
]

ALERT = [
    ('A5', 0.1), ('A4', 0.1), ('A5', 0.1), ('A4', 0.1),
    ('A5', 0.1), ('A4', 0.1), ('A5', 0.1), ('A4', 0.2)
]

SUPER_MARIO = [
    ('E5', 0.12), ('E5', 0.12), ('REST', 0.12), ('E5', 0.12),
    ('REST', 0.12), ('C5', 0.12), ('E5', 0.2), ('G5', 0.25),
    ('REST', 0.2), ('G4', 0.25)
]

STAR_WARS = [
    ('A4', 0.4), ('A4', 0.4), ('A4', 0.4), ('F4', 0.3), ('C5', 0.15),
    ('A4', 0.4), ('F4', 0.3), ('C5', 0.15), ('A4', 0.8)
]

TETRIS = [
    ('E5', 0.3), ('B4', 0.15), ('C5', 0.15), ('D5', 0.3), ('C5', 0.15), ('B4', 0.15),
    ('A4', 0.3), ('A4', 0.15), ('C5', 0.15), ('E5', 0.3), ('D5', 0.15), ('C5', 0.15),
    ('B4', 0.45), ('C5', 0.15), ('D5', 0.3), ('E5', 0.3),
    ('C5', 0.3), ('A4', 0.3), ('A4', 0.4)
]

MELODIES = {
    'beep': BEEP,
    'two_beeps': TWO_BEEPS,
    'notify': NOTIFY,
    'success': SUCCESS,
    'error': ERROR,
    'alert': ALERT,
    'super_mario': SUPER_MARIO,
    'star_wars': STAR_WARS,
    'tetris': TETRIS,
    'ode_to_joy': ODE_TO_JOY,
    'twinkle': TWINKLE,
}

MELODY_META = {
    'beep': {'title': '单哔提示 (Beep)', 'category': '提示音', 'desc': '标准 1000Hz 经典短哔', 'icon': '🔔', 'duration': 0.15},
    'two_beeps': {'title': '双哔确认 (Two Beeps)', 'category': '提示音', 'desc': '短促双连音操作确认', 'icon': '✌️', 'duration': 0.28},
    'notify': {'title': '系统消息通知 (Notify)', 'category': '提示音', 'desc': '四音调消息送达提示', 'icon': '💬', 'duration': 0.61},
    'success': {'title': '操作成功 (Success)', 'category': '状态音', 'desc': '上升和弦欢快完成音', 'icon': '✅', 'duration': 0.6},
    'error': {'title': '操作失败 (Error)', 'category': '状态音', 'desc': '低沉降音告警提示', 'icon': '❌', 'duration': 0.66},
    'alert': {'title': '紧急警报 (Alert)', 'category': '状态音', 'desc': '高低频急速交替警示', 'icon': '🚨', 'duration': 0.9},
    'super_mario': {'title': '超级马里奥 (Super Mario)', 'category': '经典游戏', 'desc': '任天堂水管工经典通关前奏', 'icon': '🍄', 'duration': 1.6},
    'star_wars': {'title': '星球大战 (Imperial March)', 'category': '经典影视', 'desc': '达斯维达帝国进行曲标志段', 'icon': '⚔️', 'duration': 2.9},
    'tetris': {'title': '俄罗斯方块 (Tetris)', 'category': '经典游戏', 'desc': '经典方块 Korobeiniki 经典旋律', 'icon': '🧱', 'duration': 4.2},
    'ode_to_joy': {'title': '欢乐颂 (Ode to Joy)', 'category': '名曲旋律', 'desc': '贝多芬第九交响曲经典主旋律', 'icon': '🎼', 'duration': 13.0},
    'twinkle': {'title': '小星星 (Twinkle Star)', 'category': '名曲旋律', 'desc': '欢快悦耳的经典世界童谣', 'icon': '✨', 'duration': 5.6},
}

