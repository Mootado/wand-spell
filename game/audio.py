"""Short generated tones. A matching file in assets/audio replaces a tone."""

from __future__ import annotations

from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "assets" / "audio"

NAMES = ("tide", "flame", "frost", "strike", "fizzle", "success", "hurt", "daze", "hit")


class Audio:
    def __init__(self):
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.enabled = pygame.mixer.get_init() is not None
        if not self.enabled:
            return
        try:
            import numpy as np
        except ImportError:
            self.enabled = False
            return
        self._np = np
        generated = {
            "tide": self._notes((523, 659, 784), 80, 0.22),
            "flame": self._notes((349, 440, 523), 70, 0.22),
            "frost": self._notes((784, 988, 1175), 90, 0.18),
            "strike": self._notes((196, 130), 70, 0.28),
            "fizzle": self._notes((220, 160), 110, 0.16),
            "success": self._notes((523, 659, 784, 1047), 90, 0.24),
            "hurt": self._notes((196, 147, 110), 100, 0.26),
            "daze": self._notes((659, 880), 100, 0.2),
            "hit": self._thud(),
        }
        for name in NAMES:
            file_path = AUDIO_DIR / f"{name}.ogg"
            if file_path.exists():
                self.sounds[name] = pygame.mixer.Sound(str(file_path))
            else:
                self.sounds[name] = generated[name]

    def play(self, name: str) -> None:
        sound = self.sounds.get(name)
        if self.enabled and sound is not None:
            sound.play()

    def _notes(self, freqs: tuple[int, ...], ms: int, volume: float):
        chunks = [self._tone(freq, ms, volume) for freq in freqs]
        return self._sound(self._np.concatenate(chunks))

    def _tone(self, freq: float, ms: int, volume: float):
        np = self._np
        rate = pygame.mixer.get_init()[0]
        count = max(1, int(rate * ms / 1000))
        t = np.linspace(0, ms / 1000, count, False)
        wave = np.sin(2 * np.pi * freq * t)
        envelope = np.linspace(1.0, 0.15, count)
        attack = max(1, min(count // 6, int(rate * 0.012)))
        envelope[:attack] *= np.linspace(0.0, 1.0, attack)
        return wave * envelope * volume

    def _thud(self):
        np = self._np
        rate = pygame.mixer.get_init()[0]
        count = int(rate * 0.12)
        noise = np.random.uniform(-1.0, 1.0, count)
        envelope = np.linspace(1.0, 0.0, count) ** 2
        low = np.sin(2 * np.pi * 90 * np.linspace(0, 0.12, count, False))
        return self._sound((noise * 0.35 + low * 0.65) * envelope * 0.35)

    def _sound(self, mono):
        np = self._np
        channels = pygame.mixer.get_init()[2]
        clipped = np.clip(mono, -1.0, 1.0)
        if channels == 1:
            pcm = (clipped * 32767).astype(np.int16)
        else:
            column = (clipped * 32767).astype(np.int16)
            pcm = np.column_stack([column] * channels)
        return pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
