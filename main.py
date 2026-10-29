"""Wand Spell: an interactive-movie adventure driven by a Universal wand."""

from __future__ import annotations

import argparse

import pygame

from camera.gestures import classify, sample_path
from camera.tracker import WandTracker, open_source
from game.audio import Audio
from game.draw import Renderer, SPELL_COLOR
from game.duel import Duel
from game.story import Story

WIDTH = 1280
HEIGHT = 720

KEYS = {
    pygame.K_1: "tide",
    pygame.K_2: "flame",
    pygame.K_3: "frost",
    pygame.K_4: "strike",
}


def main() -> None:
    args = parse_args()
    pygame.mixer.pre_init(22050, -16, 2, 512)
    pygame.init()
    flags = pygame.FULLSCREEN if args.fullscreen else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Wand Spell")
    clock = pygame.time.Clock()

    tracker = None
    if not args.keyboard:
        source = open_source(prefer_webcam=args.webcam)
        if source is not None:
            tracker = WandTracker(source)
            tracker.start()

    session = Session(show_keys=args.keyboard or tracker is None, debug=args.debug, tracker=tracker)
    session.audio = Audio()
    session.renderer = Renderer()

    running = True
    while running:
        dt = min(0.05, clock.tick(60) / 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                running = session.on_key(event.key) and running
        session.update(dt)
        session.renderer.update(dt)
        session.renderer.draw(screen, session)
        pygame.display.flip()

    if tracker is not None:
        tracker.stop()
    pygame.quit()


class Session:
    def __init__(self, show_keys: bool, debug: bool, tracker: WandTracker | None):
        self.mode = "calibrate"
        self.story = Story()
        self.duel = Duel()
        self.show_keys = show_keys
        self.debug = debug
        self.tracker = tracker
        self.audio = None
        self.note = ""
        self.note_t = 0.0
        self.traces: list[dict] = []
        self.live_stroke: list = []
        self.mask = None
        self.blob = None
        self.threshold = 185
        self.renderer = None

    def on_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return True
        if key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET) and self.tracker is not None:
            self.tracker.adjust_threshold(-8 if key == pygame.K_LEFTBRACKET else 8)
            return True
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            self._confirm()
            return True
        if key == pygame.K_r and self.mode != "calibrate":
            self._restart()
            return True
        spell = KEYS.get(key)
        if spell is not None:
            self._add_trace(sample_path(spell), spell)
            self._cast(spell)
        return True

    def update(self, dt: float) -> None:
        self.note_t = max(0.0, self.note_t - dt)
        self.traces = [trace for trace in self.traces if trace["life"] > 0]
        for trace in self.traces:
            trace["life"] -= dt
        if self.tracker is not None:
            snap = self.tracker.snapshot()
            self.live_stroke = snap["stroke"]
            self.mask = snap["mask"]
            self.blob = snap["blob"]
            self.threshold = snap["threshold"]
            for path in self.tracker.poll():
                spell, _confidence, _scores = classify(path)
                self._add_trace(path, spell)
                self._cast(spell)
        if self.mode == "story":
            self.story.update(dt)
            if self.story.done:
                self.mode = "duel"
                self.duel.reset()
                self.note = "Counter, then strike"
                self.note_t = 1.6
        elif self.mode == "duel":
            self.duel.update(dt)
            if self.duel.phase == "won":
                self.mode = "victory"

    def _confirm(self) -> None:
        if self.mode == "calibrate":
            self.mode = "story"
            self.story.reset()
            self.note = ""
            self.note_t = 0.0
            self.traces.clear()
        elif self.mode == "victory":
            self._restart()
        elif self.mode == "duel" and self.duel.phase == "lost":
            self.duel.reset()

    def _restart(self) -> None:
        self.story.reset()
        self.duel.reset()
        self.mode = "story"
        self.note = ""
        self.note_t = 0.0
        self.traces.clear()

    def _cast(self, spell: str | None) -> None:
        if spell is None:
            self.note = "The spell fizzles"
            self.note_t = 1.1
            self._play("fizzle")
            return
        if self.mode == "calibrate":
            self.note = f"That reads as {spell.title()}"
            self.note_t = 1.4
            self._play(spell)
            return
        if self.mode == "story":
            result = self.story.cast(spell)
            if result == "ok":
                self._play("success" if self.story.phase != "play" else spell)
                if self.renderer is not None:
                    self.renderer.celebrate(spell)
            elif result == "wrong":
                self._play("fizzle")
        elif self.mode == "duel":
            result = self.duel.cast(spell)
            sound = {"daze": "daze", "hit": "hit", "win": "success", "hurt": "hurt", "fizzle": "fizzle"}.get(result)
            if sound:
                self._play(sound)
            if result in ("daze", "hit", "win") and self.renderer is not None:
                self.renderer.celebrate("strike" if result != "daze" else spell)

    def _add_trace(self, points, spell: str | None) -> None:
        color = SPELL_COLOR.get(spell or "", (170, 170, 180))
        self.traces.append({"points": list(points), "color": color, "life": 1.15, "max": 1.15})

    def _play(self, name: str) -> None:
        if self.audio is not None:
            self.audio.play(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wand Spell adventure")
    parser.add_argument("--keyboard", action="store_true", help="Skip the camera and cast with 1-4")
    parser.add_argument("--webcam", action="store_true", help="Use a webcam instead of the Pi camera")
    parser.add_argument("--debug", action="store_true", help="Show the threshold image while playing")
    parser.add_argument("--fullscreen", action="store_true", help="Fill the TV")
    return parser.parse_args()


if __name__ == "__main__":
    main()
