"""The short adventure: practice, burning gate, frozen lock, river."""

from __future__ import annotations

PRACTICE = ("tide", "flame", "frost")

TITLES = {
    "practice": "Practice",
    "gate": "The Burning Gate",
    "ice": "The Frozen Lock",
    "river": "The Wide River",
}

PROMPTS = {
    "tide": "Draw a circle",
    "flame": "Draw a Z",
    "frost": "Draw a flat line",
    "strike": "Slash diagonally",
}


class Story:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.scene = "practice"
        self.step = 0
        self.phase = "play"
        self.timer = 0.0
        self.fire = 1.0
        self.fire_target = 1.0
        self.ice = 1.0
        self.ice_target = 1.0
        self.bridge = 0.0
        self.bridge_target = 0.0
        self.walk = 0.0
        self.flare = 0.0
        self.banner = "Copy the gold shape"
        self.banner_t = 3.0
        self.done = False

    def needed(self) -> str | None:
        if self.done or self.phase != "play":
            return None
        if self.scene == "practice":
            if self.step >= len(PRACTICE):
                return None
            return PRACTICE[self.step]
        if self.scene == "gate":
            return "tide"
        if self.scene == "ice":
            return "flame"
        if self.scene == "river":
            return "frost"
        return None

    def cast(self, spell: str) -> str:
        if self.phase != "play":
            return "ignore"
        need = self.needed()
        if need is None:
            return "ignore"
        if spell != need:
            self._wrong(spell)
            return "wrong"
        self._right()
        return "ok"

    def update(self, dt: float) -> None:
        self.banner_t = max(0.0, self.banner_t - dt)
        self.flare = max(0.0, self.flare - dt * 1.6)
        self.fire = _approach(self.fire, self.fire_target, dt, 2.4)
        self.ice = _approach(self.ice, self.ice_target, dt, 2.2)
        self.bridge = _approach(self.bridge, self.bridge_target, dt, 1.6)

        if self.phase == "resolving":
            ready = (
                (self.scene == "gate" and self.fire < 0.05)
                or (self.scene == "ice" and self.ice < 0.05)
                or (self.scene == "river" and self.bridge > 0.96)
            )
            if ready:
                if self.scene == "river":
                    self.phase = "walk"
                    self.banner = "Cross"
                    self.banner_t = 2.0
                else:
                    self.phase = "hold"
                    self.timer = 1.35
        elif self.phase == "walk":
            self.walk = min(1.0, self.walk + dt * 0.32)
            if self.walk >= 1.0:
                self.phase = "hold"
                self.timer = 0.7
                self.banner = "Across"
                self.banner_t = 1.2
        elif self.phase == "hold":
            self.timer -= dt
            if self.timer <= 0:
                self._advance()

    def _wrong(self, spell: str) -> None:
        if self.scene == "practice":
            self.banner = "Follow the drawing"
            self.banner_t = 1.3
        elif self.scene == "gate" and spell == "flame":
            self.fire_target = min(1.0, self.fire_target + 0.45)
            self.flare = 1.0
            self.banner = "The flames roar higher"
            self.banner_t = 1.4
        elif self.scene == "ice" and spell == "tide":
            self.ice_target = min(1.0, self.ice_target + 0.35)
            self.banner = "The ice grows thicker"
            self.banner_t = 1.4
        else:
            self.banner = "That spell does nothing here"
            self.banner_t = 1.2

    def _right(self) -> None:
        if self.scene == "practice":
            self.step += 1
            if self.step >= len(PRACTICE):
                self.phase = "hold"
                self.timer = 1.15
                self.banner = "The path ahead stirs"
                self.banner_t = 1.5
            else:
                self.banner = "Yes"
                self.banner_t = 0.8
            return
        if self.scene == "gate":
            self.fire_target = 0.0
            self.banner = "The fire dies"
        elif self.scene == "ice":
            self.ice_target = 0.0
            self.banner = "The ice melts"
        elif self.scene == "river":
            self.bridge_target = 1.0
            self.banner = "A bridge of frost"
        self.banner_t = 1.8
        self.phase = "resolving"

    def _advance(self) -> None:
        order = ("practice", "gate", "ice", "river", "done")
        self.scene = order[order.index(self.scene) + 1]
        self.phase = "play"
        self.walk = 0.0
        if self.scene == "gate":
            self.fire = 1.0
            self.fire_target = 1.0
            self.banner = "Water puts the gate out"
        elif self.scene == "ice":
            self.ice = 1.0
            self.ice_target = 1.0
            self.banner = "Fire melts the lock"
        elif self.scene == "river":
            self.bridge = 0.0
            self.bridge_target = 0.0
            self.banner = "Frost can freeze a path"
        elif self.scene == "done":
            self.done = True
            self.banner = ""
        self.banner_t = 2.4


def _approach(current: float, target: float, dt: float, speed: float) -> float:
    return current + (target - current) * min(1.0, dt * speed)
