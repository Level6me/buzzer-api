import os
import time
import threading

PWMCHIP = '/sys/class/pwm/pwmchip0'
PWM0 = f'{PWMCHIP}/pwm0'
GPIO_PIN = 18

NOTES = {
    # Octave 3
    'C3': 131, 'C#3': 139, 'DB3': 139, 'D3': 147, 'D#3': 156, 'EB3': 156,
    'E3': 165, 'F3': 175, 'F#3': 185, 'GB3': 185, 'G3': 196, 'G#3': 208,
    'AB3': 208, 'A3': 220, 'A#3': 233, 'BB3': 233, 'B3': 247,
    # Octave 4 (Middle C)
    'C4': 262, 'C#4': 277, 'DB4': 277, 'D4': 294, 'D#4': 311, 'EB4': 311,
    'E4': 330, 'F4': 349, 'F#4': 370, 'GB4': 370, 'G4': 392, 'G#4': 415,
    'AB4': 415, 'A4': 440, 'A#4': 466, 'BB4': 466, 'B4': 494,
    # Octave 5
    'C5': 523, 'C#5': 554, 'DB5': 554, 'D5': 587, 'D#5': 622, 'EB5': 622,
    'E5': 659, 'F5': 698, 'F#5': 740, 'GB5': 740, 'G5': 784, 'G#5': 830,
    'AB5': 830, 'A5': 880, 'A#5': 932, 'BB5': 932, 'B5': 988,
    # Octave 6
    'C6': 1047, 'C#6': 1109, 'DB6': 1109, 'D6': 1175, 'D#6': 1245, 'EB6': 1245,
    'E6': 1319, 'F6': 1397, 'F#6': 1480, 'GB6': 1480, 'G6': 1568, 'G#6': 1661,
    'AB6': 1661, 'A6': 1760, 'A#6': 1865, 'BB6': 1865, 'B6': 1976,
    # Rest / Silence
    'REST': 0, 'P': 0, '0': 0, '': 0,
}

def freq_to_note_name(freq):
    if not freq or freq <= 0:
        return 'REST'
    best_note = None
    min_diff = float('inf')
    for n, f in NOTES.items():
        if f > 0:
            diff = abs(f - freq)
            if diff < min_diff:
                min_diff = diff
                best_note = n
    if min_diff <= 10:
        return best_note
    return f"{int(freq)}Hz"

class Buzzer:
    def __init__(self, duty_default=0.1):
        self.duty_default = duty_default
        self._stop_flag = False
        self._lock = threading.Lock()
        self.is_playing = False
        self.current_frequency = 0
        self.current_duty = 0.0
        self.current_note = None
        self.current_item = None
        self._listeners = []
        self._ensure()

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self):
        st = self.get_status()
        for cb in list(self._listeners):
            try:
                cb(st)
            except Exception:
                pass

    def _ensure(self):
        if not os.path.exists(PWM0):
            try:
                with open(f'{PWMCHIP}/export', 'w') as f:
                    f.write('0')
            except Exception:
                pass
        # GPIO18 -> ALT5 (PWM0)，信号真正接到引脚
        os.system(f'raspi-gpio set {GPIO_PIN} a5 2>/dev/null || pinctrl set {GPIO_PIN} a5 2>/dev/null')

    def _set_tone(self, frequency, duty):
        if frequency <= 0:
            self._disable_pwm()
            return
        period_ns = int(1e9 / frequency)
        duty_ns = int(period_ns * duty)
        try:
            with open(f'{PWM0}/period', 'w') as f:
                f.write(str(period_ns))
            with open(f'{PWM0}/duty_cycle', 'w') as f:
                f.write(str(duty_ns))
            with open(f'{PWM0}/enable', 'w') as f:
                f.write('1')
        except Exception:
            pass

    def _disable_pwm(self):
        try:
            with open(f'{PWM0}/enable', 'w') as f:
                f.write('0')
        except Exception:
            pass

    def play_tone(self, frequency, duration, duty=None):
        duty = self.duty_default if duty is None else duty
        self._stop_flag = False
        self._ensure()
        self.is_playing = True
        self.current_frequency = frequency
        self.current_duty = duty
        self.current_note = freq_to_note_name(frequency)
        self.current_item = f"{int(frequency)}Hz ({self.current_note})"
        self._notify()
        try:
            self._set_tone(frequency, duty)
            elapsed = 0.0
            step = 0.02
            dur = float(duration)
            while elapsed < dur and not self._stop_flag:
                time.sleep(min(step, dur - elapsed))
                elapsed += step
        finally:
            self.stop()

    def play_melody(self, notes, duty=None, name=None):
        duty = self.duty_default if duty is None else duty
        self._stop_flag = False
        self._ensure()
        self.is_playing = True
        self.current_item = name or "自定义旋律"
        self.current_duty = duty
        try:
            for item in notes:
                if self._stop_flag:
                    break
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    note, duration = item[0], item[1]
                    freq = note if isinstance(note, (int, float)) else NOTES.get(str(note).strip().upper(), 440)
                    self.current_frequency = freq
                    self.current_note = str(note).strip().upper() if not isinstance(note, (int, float)) else freq_to_note_name(freq)
                    if freq <= 0 or str(note).upper() in ('REST', 'P', '0'):
                        self._disable_pwm()
                    else:
                        self._set_tone(freq, duty)
                    self._notify()
                    
                    elapsed = 0.0
                    step = 0.02
                    dur = float(duration)
                    while elapsed < dur and not self._stop_flag:
                        time.sleep(min(step, dur - elapsed))
                        elapsed += step
                    
                    # 音符间微小静音断音，避免相同音连成一体
                    self._disable_pwm()
                    self.current_frequency = 0
                    self.current_note = 'REST'
                    self._notify()
                    time.sleep(0.015)
        finally:
            self.stop()

    def stop(self):
        self._stop_flag = True
        self._disable_pwm()
        was_playing = self.is_playing
        self.is_playing = False
        self.current_frequency = 0
        self.current_duty = 0.0
        self.current_note = None
        self.current_item = None
        if was_playing:
            self._notify()

    def get_status(self):
        return {
            'gpio': GPIO_PIN,
            'pwm_channel': 'pwm0',
            'is_playing': self.is_playing,
            'frequency': self.current_frequency,
            'note': self.current_note,
            'duty': round(self.current_duty, 4),
            'current_item': self.current_item,
        }
