"""Counter the enemy's element, then strike while they are dazed."""

from __future__ import annotations

import random

COUNTER = {"fire": "tide", "ice": "flame", "water": "frost"}

HINTS = {
    "fire": "Draw a circle — Tide",
    "ice": "Draw a Z — Flame",
    "water": "Draw a flat line — Frost",
}

WINDUP = 2.4
DAZE = 2.5


class Duel:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.player_hp = 3
        self.enemy_hp = 3
        self.phase = "windup"
        self.timer = WINDUP
        self.element = "fire"
        self.banner = HINTS["fire"]
        self.banner_t = 2.0
        self.flash = 0.0
        self.knock = 0.0
        self._last = None
        self._next_element()

    def needed(self) -> str | None:
        if self.phase == "windup":
            return COUNTER[self.element]
        if self.phase == "dazed":
            return "strike"
        return None

    def cast(self, spell: str) -> str:
        if self.phase == "windup":
            if spell == COUNTER[self.element]:
                self.phase = "dazed"
                self.timer = DAZE
                self.banner = "Dazed — slash!"
                self.banner_t = DAZE
                return "daze"
            self._hurt("The counter missed")
            return "hurt"
        if self.phase == "dazed":
            if spell != "strike":
                self.banner = "Slash while they stumble"
                self.banner_t = 0.9
                return "fizzle"
            self.enemy_hp -= 1
            self.knock = 1.0
            self.flash = 0.25
            if self.enemy_hp <= 0:
                self.phase = "won"
                self.banner = "The shadow breaks"
                self.banner_t = 2.0
                return "win"
            self.phase = "hitstun"
            self.timer = 0.65
            self.banner = "A clean hit"
            self.banner_t = 0.7
            return "hit"
        return "ignore"

    def update(self, dt: float) -> None:
        self.banner_t = max(0.0, self.banner_t - dt)
        self.flash = max(0.0, self.flash - dt * 1.4)
        self.knock = max(0.0, self.knock - dt * 1.5)
        if self.phase in ("won", "lost"):
            return
        self.timer -= dt
        if self.timer > 0:
            return
        if self.phase == "windup":
            self._hurt("The spell lands")
        elif self.phase == "dazed":
            self.phase = "recover"
            self.timer = 0.7
            self.banner = "They shook it off"
            self.banner_t = 0.9
        elif self.phase in ("hitstun", "hurt", "recover"):
            self._next_element()

    def _hurt(self, message: str) -> None:
        self.player_hp -= 1
        self.flash = 0.55
        if self.player_hp <= 0:
            self.phase = "lost"
            self.banner = "The shadow holds — Enter retries"
            self.banner_t = 6.0
            return
        self.phase = "hurt"
        self.timer = 0.85
        self.banner = message
        self.banner_t = 0.9

    def _next_element(self) -> None:
        choices = ["fire", "ice", "water"]
        if self._last in choices:
            choices.remove(self._last)
        self.element = random.choice(choices)
        self._last = self.element
        self.phase = "windup"
        self.timer = WINDUP
        self.banner = HINTS[self.element]
        self.banner_t = WINDUP
