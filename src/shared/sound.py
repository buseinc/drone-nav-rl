"""Sound effects generated with numpy - no audio files needed.

If there is no audio device the game simply stays silent.
"""

import numpy as np
import pygame

RATE = 44100


def _wave(freq, ms, volume=0.3, shape="sine", decay=4.0):
    n = int(RATE * ms / 1000)
    t = np.arange(n) / RATE
    if shape == "square":
        w = np.sign(np.sin(2 * np.pi * freq * t))
    elif shape == "noise":
        w = np.random.uniform(-1, 1, n)
        # crude low-pass filter: makes the noise sound like a "boom"
        w = np.convolve(w, np.ones(12) / 12, mode="same")
        w /= np.abs(w).max() or 1
    else:
        w = np.sin(2 * np.pi * freq * t)
    env = np.exp(-decay * t / (ms / 1000))          # fade out
    attack = np.minimum(1, np.arange(n) / (RATE * 0.004))  # avoid clicks
    return w * env * attack * volume


def _seq(notes, gap_ms=0, **kw):
    parts = []
    for f, ms in notes:
        parts.append(_wave(f, ms, **kw))
        if gap_ms:
            parts.append(np.zeros(int(RATE * gap_ms / 1000)))
    return np.concatenate(parts)


class Sounds:
    def __init__(self):
        self.enabled = True
        self.bank = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 2, 512)
            _, _, channels = pygame.mixer.get_init()
            waves = {
                "move": _wave(520, 45, 0.06, decay=6),
                "beep": _wave(440, 140, 0.25, "square", decay=3),
                "go": _wave(880, 320, 0.25, "square", decay=3),
                "goal": _seq([(523, 80), (659, 80), (784, 80), (1047, 220)],
                             volume=0.25),
                "crash": _wave(0, 450, 0.6, "noise", decay=5),
                "win": _seq([(523, 120), (659, 120), (784, 120), (1047, 120),
                             (784, 100), (1047, 400)], volume=0.25),
                "lose": _seq([(392, 180), (330, 180), (262, 420)],
                             volume=0.25, shape="square"),
                "click": _wave(700, 35, 0.12, decay=5),
            }
            for name, w in waves.items():
                pcm = (w * 32767).astype(np.int16)
                if channels == 2:
                    pcm = np.ascontiguousarray(np.column_stack([pcm, pcm]))
                self.bank[name] = pygame.sndarray.make_sound(pcm)
        except (pygame.error, ValueError, TypeError):
            self.bank = {}

    def play(self, name):
        if self.enabled and name in self.bank:
            self.bank[name].play()
