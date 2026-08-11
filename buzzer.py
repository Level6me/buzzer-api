import os
import time

PWMCHIP = '/sys/class/pwm/pwmchip0'
PWM0 = f'{PWMCHIP}/pwm0'
GPIO_PIN = 18

NOTES = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349,
    'G4': 392, 'A4': 440, 'B4': 494, 'C5': 523, 'D5': 587,
}

class Buzzer:
    def __init__(self, duty_default=0.1):
        self.duty_default = duty_default
        self._ensure()

    def _ensure(self):
        if not os.path.exists(PWM0):
            with open(f'{PWMCHIP}/export', 'w') as f:
                f.write('0')
        # GPIO18 -> ALT5 (PWM0)，信号真正接到引脚
        os.system(f'raspi-gpio set {GPIO_PIN} a5')

    def _set_tone(self, frequency, duty):
        period_ns = int(1e9 / frequency)
        duty_ns = int(period_ns * duty)
        with open(f'{PWM0}/period', 'w') as f:
            f.write(str(period_ns))
        with open(f'{PWM0}/duty_cycle', 'w') as f:
            f.write(str(duty_ns))
        with open(f'{PWM0}/enable', 'w') as f:
            f.write('1')

    def play_tone(self, frequency, duration, duty=None):
        duty = self.duty_default if duty is None else duty
        self._ensure()
        self._set_tone(frequency, duty)
        time.sleep(duration)
        self.stop()

    def play_melody(self, notes, duty=None):
        for item in notes:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                note, duration = item[0], item[1]
                freq = note if isinstance(note, (int, float)) else NOTES.get(str(note), 440)
                self.play_tone(freq, float(duration), duty)

    def stop(self):
        try:
            with open(f'{PWM0}/enable', 'w') as f:
                f.write('0')
        except Exception:
            pass
