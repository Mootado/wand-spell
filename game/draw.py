"""Storybook scenes, the spell card, and the wand-trace sparkles."""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

from camera.tracker import CAM_H, CAM_W
from game.story import PROMPTS, TITLES

ART_DIR = Path(__file__).resolve().parent.parent / "assets" / "art"

INK = (14, 10, 20)
NIGHT = (22, 14, 36)
GOLD = (232, 196, 122)
CREAM = (236, 226, 204)
STONE = (86, 76, 92)
STONE_DARK = (48, 40, 56)
TIDE = (78, 198, 216)
FLAME = (232, 112, 48)
FROST = (198, 230, 242)
STRIKE = (244, 228, 186)
MOSS = (42, 68, 48)
WATER = (28, 72, 118)
WATER_LIT = (64, 130, 168)

SPELL_COLOR = {
    "tide": TIDE,
    "flame": FLAME,
    "frost": FROST,
    "strike": STRIKE,
    "fire": FLAME,
    "ice": FROST,
    "water": TIDE,
}


class Renderer:
    def __init__(self):
        self.t = 0.0
        self.fonts: dict[int, pygame.font.Font] = {}
        self.vignette = None
        self.stars = None
        self.particles = Particles()
        self.art_size = None
        self.bg_night = None
        self.bg_river = None
        self.gate = None
        self.gate_opening = pygame.Rect(0, 0, 10, 10)
        self.hero = None
        self.foe = None

    def update(self, dt: float) -> None:
        self.t += dt
        self.particles.update(dt)

    def celebrate(self, spell: str, where: tuple[float, float] | None = None) -> None:
        x, y = where or (500, 380)
        self.particles.spawn(x, y, SPELL_COLOR.get(spell, GOLD), n=22, speed=140, life=0.7)

    def draw(self, surf: pygame.Surface, session) -> None:
        self._ensure_art(surf.get_size())
        kind = "river" if session.mode == "story" and session.story.scene == "river" else "night"
        self._backdrop(surf, kind)
        if session.mode == "calibrate":
            self._calibrate(surf, session)
        elif session.mode == "victory":
            self._victory(surf)
        elif session.mode == "duel":
            self._duel(surf, session)
        else:
            self._story(surf, session)
        if session.mode != "calibrate":
            self._traces(surf, session)
            self.particles.draw(surf)
            if session.mode != "victory":
                self._panel(surf, session)
                self._banner(surf, session)
        if session.debug and session.mask is not None and session.mode != "calibrate":
            self._inset(surf, session.mask, session.blob)
        self._vignette_blit(surf)
        if session.mode == "duel" and session.duel.flash > 0 and session.duel.phase in ("hurt", "lost"):
            shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            shade.fill((140, 24, 32, int(90 * session.duel.flash)))
            surf.blit(shade, (0, 0))

    def _ensure_art(self, size: tuple[int, int]) -> None:
        if self.art_size == size:
            return
        self.art_size = size
        self.bg_night = _background(ART_DIR / "bg_night.jpg", size)
        self.bg_river = _background(ART_DIR / "bg_river.jpg", size)
        gate, opening = _keyed_sprite(ART_DIR / "gate.jpg")
        self.gate, self.gate_opening = _fit(gate, 540, opening)
        self.gate_interior = _door_mask(self.gate)
        hero, _hole = _keyed_sprite(ART_DIR / "hero.jpg")
        self.hero = _fit(hero, 280, None)[0]
        foe, _hole = _keyed_sprite(ART_DIR / "foe.jpg")
        self.foe = _fit(foe, 460, None)[0]

    def _backdrop(self, surf: pygame.Surface, kind: str) -> None:
        image = self.bg_river if kind == "river" else self.bg_night
        if image is not None:
            surf.blit(image, (0, 0))
            return
        self._sky(surf)

    def _place(self, image: pygame.Surface, feet: tuple[int, int]) -> pygame.Rect:
        rect = image.get_rect()
        rect.midbottom = feet
        return rect

    def _shadow(self, surf: pygame.Surface, center: tuple[int, int], width: int) -> None:
        blob = pygame.Surface((width, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(blob, (0, 0, 0, 90), blob.get_rect())
        surf.blit(blob, (center[0] - width // 2, center[1] - 10))

    def _sky(self, surf: pygame.Surface) -> None:
        width, height = surf.get_size()
        for y in range(0, height, 4):
            blend = y / height
            color = (
                int(NIGHT[0] * (1 - blend) + 18 * blend),
                int(NIGHT[1] * (1 - blend) + 16 * blend),
                int(NIGHT[2] * (1 - blend) + 28 * blend),
            )
            pygame.draw.rect(surf, color, (0, y, width, 4))
        if self.stars is None:
            rng = random.Random(7)
            self.stars = [
                (rng.randrange(0, width), rng.randrange(0, int(height * 0.5)), rng.choice((1, 1, 2)))
                for _ in range(80)
            ]
        for index, (x, y, radius) in enumerate(self.stars):
            twinkle = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(self.t * 1.4 + index))
            value = int(180 * twinkle)
            pygame.draw.circle(surf, (value, value, value + 20), (x, y), radius)
        pygame.draw.circle(surf, (232, 214, 170), (width - 360, 92), 28)
        pygame.draw.circle(surf, NIGHT, (width - 348, 84), 24)

    def _story(self, surf: pygame.Surface, session) -> None:
        story = session.story
        self._text(surf, TITLES.get(story.scene, ""), 48, (70, 36), GOLD)
        if story.scene == "practice":
            self._practice(surf, story)
        elif story.scene == "gate":
            self._gate(surf, story)
        elif story.scene == "ice":
            self._frozen(surf, story)
        elif story.scene == "river":
            self._river(surf, story)

    def _practice(self, surf: pygame.Surface, story) -> None:
        spell = story.needed() or "frost"
        self._blit_hero(surf, (210, 690))
        rect = pygame.Rect(390, 210, 260, 260)
        glow = pygame.Surface((300, 300), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*SPELL_COLOR[spell], 50), (150, 150), 140)
        surf.blit(glow, (rect.centerx - 150, rect.centery - 150))
        pygame.draw.circle(surf, GOLD, rect.center, 128, 4)
        self._shape(surf, spell, rect.inflate(-70, -70), SPELL_COLOR[spell], 8)
        done = min(story.step, 3)
        for i in range(3):
            color = GOLD if i < done else (150, 140, 120)
            pygame.draw.circle(surf, color, (rect.centerx - 36 + i * 36, rect.bottom + 16), 7)

    def _gate(self, surf: pygame.Surface, story) -> None:
        gate_rect = self._place(self.gate, (560, 700))
        if story.fire > 0.04 or story.flare > 0:
            self._in_arch(surf, gate_rect, lambda layer, rect: self._flames(layer, rect, story.fire, story.flare))
            self.particles.spawn(
                gate_rect.centerx,
                gate_rect.bottom - 70,
                (255, 190, 80),
                n=2,
                speed=40,
                life=0.6,
                upward=True,
                gravity=10,
            )
        self._shadow(surf, (gate_rect.centerx, gate_rect.bottom), int(gate_rect.w * 0.7))
        surf.blit(self.gate, gate_rect)
        self._blit_hero(surf, (170, 700))

    def _frozen(self, surf: pygame.Surface, story) -> None:
        gate_rect = self._place(self.gate, (560, 700))
        self._in_arch(surf, gate_rect, lambda layer, rect: self._ice(layer, rect, story.ice))
        self._shadow(surf, (gate_rect.centerx, gate_rect.bottom), int(gate_rect.w * 0.7))
        surf.blit(self.gate, gate_rect)
        self._blit_hero(surf, (170, 700))

    def _in_arch(self, surf: pygame.Surface, gate_rect: pygame.Rect, paint) -> None:
        layer = pygame.Surface(self.gate.get_size(), pygame.SRCALPHA)
        paint(layer, layer.get_rect())
        alpha = pygame.surfarray.pixels_alpha(layer)
        if self.gate_interior is not None:
            alpha[~self.gate_interior] = 0
        else:
            alpha[pygame.surfarray.array_alpha(self.gate) > 24] = 0
        del alpha
        surf.blit(layer, gate_rect.topleft)

    def _river(self, surf: pygame.Surface, story) -> None:
        deck = int(story.bridge * 640)
        bridge_y = 548
        if deck > 4:
            slab = pygame.Surface((deck, 64), pygame.SRCALPHA)
            near, far = 58, 34
            body = [(0, 64 - near), (deck, 64 - far), (deck, 64 - far + 26), (0, 64)]
            pygame.draw.polygon(slab, (176, 216, 230, 220), body)
            shine = [(4, 64 - near + 6), (deck - 4, 64 - far + 4), (deck - 4, 64 - far + 12), (4, 64 - near + 16)]
            pygame.draw.polygon(slab, (232, 246, 255, 200), shine)
            if deck > 36:
                cracks = random.Random(5)
                for _ in range(max(2, deck // 80)):
                    x1 = cracks.randrange(12, deck - 12)
                    pygame.draw.line(
                        slab,
                        (140, 186, 206, 160),
                        (x1, 64 - near + 10),
                        (x1 + cracks.randint(-18, 18), 64 - 8),
                        2,
                    )
            surf.blit(slab, (180, bridge_y))
        if story.walk <= 0:
            self._blit_hero(surf, (150, 640))
        else:
            self._blit_hero(surf, (int(200 + story.walk * 560), bridge_y + 28))

    def _hole(self, gate_rect: pygame.Rect) -> pygame.Rect:
        opening = self.gate_opening
        return pygame.Rect(gate_rect.x + opening.x, gate_rect.y + opening.y, opening.w, opening.h)

    def _blit_hero(self, surf: pygame.Surface, feet: tuple[int, int]) -> None:
        if self.hero is None:
            return
        rect = self._place(self.hero, feet)
        self._shadow(surf, (rect.centerx, rect.bottom), int(rect.w * 0.55))
        surf.blit(self.hero, rect)

    def _flames(self, surf: pygame.Surface, bounds, intensity: float, flare: float) -> None:
        x, y, w, h = bounds
        power = min(1.2, intensity + flare * 0.45)
        if power < 0.04:
            return
        sheet = pygame.Surface((w, h), pygame.SRCALPHA)
        glow_h = int(h * (0.28 + 0.12 * power))
        pygame.draw.ellipse(sheet, (170, 48, 16, int(100 * power)), (int(w * 0.16), h - glow_h, int(w * 0.68), glow_h))
        for i in range(5):
            sway = math.sin(self.t * 6 + i * 1.4) * w * 0.02
            tongue_w = w * (0.18 if i % 2 == 0 else 0.13)
            tongue_h = h * power * (0.5 + 0.38 * (0.5 + 0.5 * math.sin(self.t * 5 + i * 1.7)))
            cx = w * (i + 0.5) / 5 + sway
            top = h - tongue_h
            pygame.draw.ellipse(sheet, (150, 36, 16, 210), (cx - tongue_w / 2, top, tongue_w, tongue_h))
            pygame.draw.ellipse(
                sheet,
                FLAME + (230,),
                (cx - tongue_w * 0.32, h - tongue_h * 0.7, tongue_w * 0.64, tongue_h * 0.7),
            )
            pygame.draw.ellipse(
                sheet,
                (255, 214, 130, 235),
                (cx - tongue_w * 0.14, h - tongue_h * 0.36, tongue_w * 0.28, tongue_h * 0.38),
            )
        surf.blit(sheet, (x, y))
        if power > 0.15 and surf.get_width() > 600:
            for _ in range(2):
                px = x + random.uniform(w * 0.3, w * 0.7)
                self.particles.spawn(px, y + h * 0.72, (255, 180, 70), n=1, speed=50, life=0.5, upward=True, gravity=20)

    def _ice(self, surf: pygame.Surface, bounds, thickness: float) -> None:
        if thickness < 0.03:
            return
        x, y, w, h = bounds
        sheet = pygame.Surface((w, h), pygame.SRCALPHA)
        alpha = int(200 * thickness)
        sheet.fill((168, 214, 232, alpha))
        cracks = random.Random(3)
        for _ in range(int(10 + thickness * 14)):
            x1 = cracks.randrange(16, max(17, w - 16))
            y1 = cracks.randrange(24, max(25, h - 24))
            x2 = x1 + cracks.randint(-36, 36)
            y2 = y1 + cracks.randint(12, 48)
            pygame.draw.line(sheet, (236, 248, 255, int(150 * thickness)), (x1, y1), (x2, y2), 2)
        surf.blit(sheet, (x, y))
        icicles = int(4 + thickness * 6)
        for i in range(icicles):
            ix = x + 12 + i * (w - 20) / max(1, icicles - 1)
            length = (18 + (i % 3) * 14) * thickness
            pygame.draw.polygon(
                surf,
                FROST,
                [(ix - 6, y + h * 0.18), (ix + 6, y + h * 0.18), (ix, y + h * 0.18 + length)],
            )

    def _duel(self, surf: pygame.Surface, session) -> None:
        duel = session.duel
        self._text(surf, "The Shadow", 48, (70, 36), GOLD)
        shift = int(duel.knock * 40)
        foe_rect = self._place(self.foe, (620 + shift, 690))
        self._shadow(surf, (foe_rect.centerx, foe_rect.bottom), int(foe_rect.w * 0.45))
        surf.blit(self.foe, foe_rect)
        self._blit_hero(surf, (150, 690))
        self._hearts(surf, duel.player_hp, (70, 100))
        self._pips(surf, duel.enemy_hp, (70, 146))
        if duel.phase == "windup":
            mark = (foe_rect.centerx, max(78, foe_rect.top - 70))
            self._text(surf, duel.element.title(), 28, None, SPELL_COLOR[duel.element], center=(mark[0], mark[1] - 46))
            self._glyph(surf, mark[0], mark[1], duel.element, duel.timer / 2.4)
        elif duel.phase == "dazed":
            self._text(surf, "STRIKE", 42, None, GOLD, center=(foe_rect.centerx, foe_rect.top - 16))
            for i in range(3):
                angle = self.t * 3 + i * 2.1
                self._star(
                    surf,
                    foe_rect.centerx + math.cos(angle) * 70,
                    foe_rect.top + 30 + math.sin(angle) * 16,
                    8,
                    GOLD,
                )

    def _victory(self, surf: pygame.Surface) -> None:
        self._text(surf, "The way is clear", 56, (70, 28), GOLD)
        gate_rect = self._place(self.gate, (560, 700))
        self._shadow(surf, (gate_rect.centerx, gate_rect.bottom), int(gate_rect.w * 0.7))
        surf.blit(self.gate, gate_rect)
        self._blit_hero(surf, (250, 700))
        self._text(surf, "Enter plays it again", 32, None, CREAM, center=(480, 640))
        if int(self.t * 2) % 2 == 0 and len(self.particles.items) < 20:
            self.particles.spawn(random.uniform(240, 860), 80, GOLD, n=2, speed=30, life=1.6, gravity=24)

    def _glyph(self, surf: pygame.Surface, x: int, y: int, element: str, remain: float) -> None:
        color = SPELL_COLOR[element]
        pygame.draw.circle(surf, (20, 14, 28), (x, y), 34)
        pygame.draw.circle(surf, color, (x, y), 34, 3)
        if element == "fire":
            self._shape(surf, "flame", pygame.Rect(x - 18, y - 16, 36, 32), color, 3)
        elif element == "ice":
            for angle in (0, math.pi / 3, 2 * math.pi / 3):
                dx = math.cos(angle) * 16
                dy = math.sin(angle) * 16
                pygame.draw.line(surf, color, (x - dx, y - dy), (x + dx, y + dy), 3)
        else:
            pygame.draw.arc(surf, color, (x - 16, y - 8, 32, 16), math.pi, math.tau, 3)
            pygame.draw.arc(surf, color, (x - 16, y + 2, 32, 16), 0, math.pi, 3)
        start = -math.pi / 2
        end = start + max(0.05, remain) * math.tau
        pygame.draw.arc(surf, GOLD, (x - 48, y - 48, 96, 96), start, end, 4)

    def _hearts(self, surf: pygame.Surface, hp: int, origin: tuple[int, int]) -> None:
        x, y = origin
        for i in range(3):
            color = (196, 64, 78) if i < hp else (60, 40, 48)
            self._heart(surf, x + i * 36, y, color)

    def _heart(self, surf, x, y, color) -> None:
        pygame.draw.circle(surf, color, (x, y), 8)
        pygame.draw.circle(surf, color, (x + 12, y), 8)
        pygame.draw.polygon(surf, color, [(x - 8, y + 2), (x + 20, y + 2), (x + 6, y + 20)])

    def _pips(self, surf: pygame.Surface, hp: int, origin: tuple[int, int]) -> None:
        x, y = origin
        for i in range(3):
            color = GOLD if i < hp else (60, 52, 40)
            pygame.draw.circle(surf, color, (x + 8 + i * 28, y), 7)

    def _calibrate(self, surf: pygame.Surface, session) -> None:
        width, height = surf.get_size()
        self._text(surf, "Wand Spell", 64, None, GOLD, center=(width // 2, 54))
        if session.mask is not None:
            preview = self._mask_surface(session.mask)
            scale = 2
            preview = pygame.transform.scale(preview, (CAM_W * scale, CAM_H * scale))
            origin = ((width - preview.get_width()) // 2, 100)
            surf.blit(preview, origin)
            if session.blob is not None:
                bx = origin[0] + int(session.blob[0] * scale)
                by = origin[1] + int(session.blob[1] * scale)
                pygame.draw.circle(surf, GOLD, (bx, by), 12, 2)
            if session.live_stroke:
                mapped = [
                    (origin[0] + int(px * scale), origin[1] + int(py * scale))
                    for px, py in session.live_stroke
                ]
                if len(mapped) > 1:
                    pygame.draw.lines(surf, CREAM, False, mapped, 3)
            self._text(
                surf,
                f"Only the wand tip should be white.  [ ] threshold {session.threshold}",
                28,
                None,
                CREAM,
                center=(width // 2, height - 110),
            )
        else:
            lines = (
                "No camera on this computer.",
                "1 Tide circle    2 Flame zigzag",
                "3 Frost line     4 Strike slash",
                "On the Pi, this screen shows the camera.",
            )
            for index, line in enumerate(lines):
                self._text(surf, line, 32, None, CREAM, center=(width // 2, 240 + index * 48))
        self._text(surf, "Enter begins", 32, None, GOLD, center=(width // 2, height - 58))
        if session.note_t > 0 and session.note:
            self._text(surf, session.note, 28, None, GOLD, center=(width // 2, height - 150))

    def _panel(self, surf: pygame.Surface, session) -> None:
        width, _height = surf.get_size()
        panel = pygame.Rect(width - 280, 70, 250, 420)
        pygame.draw.rect(surf, (24, 18, 32), panel, border_radius=18)
        pygame.draw.rect(surf, GOLD, panel, 2, border_radius=18)
        needed = _needed(session)
        title = PROMPTS.get(needed, "Watch the story") if needed else "Watch"
        if session.mode == "story" and session.story.phase == "walk":
            title = "Cross"
        if session.mode == "duel" and session.duel.phase == "dazed":
            title = "Slash diagonally"
        self._text(surf, title, 26, (panel.x + 24, panel.y + 18), GOLD)
        if needed:
            shape_rect = pygame.Rect(panel.x + 35, panel.y + 70, 180, 180)
            self._shape(surf, needed, shape_rect, SPELL_COLOR[needed], 6)
            label = {"tide": "Tide", "flame": "Flame", "frost": "Frost", "strike": "Strike"}[needed]
            self._text(surf, label, 32, (panel.x + 24, panel.y + 270), SPELL_COLOR[needed])
        self._strip(surf, needed, session.show_keys, pygame.Rect(panel.x + 16, panel.y + 320, 218, 80))

    def _strip(self, surf, needed, show_keys, rect: pygame.Rect) -> None:
        labels = (("tide", "1"), ("flame", "2"), ("frost", "3"), ("strike", "4"))
        for index, (spell, key) in enumerate(labels):
            cell = pygame.Rect(rect.x + index * 54, rect.y, 50, 50)
            color = SPELL_COLOR[spell]
            width = 4 if spell == needed else 2
            pygame.draw.rect(surf, (40, 32, 52), cell, border_radius=8)
            self._shape(surf, spell, cell.inflate(-14, -14), color, width)
            if show_keys:
                self._text(surf, key, 16, (cell.x + 4, cell.bottom - 2), CREAM)

    def _shape(self, surf, kind: str, rect: pygame.Rect, color, width: int) -> None:
        points = _shape_points(kind, rect)
        if len(points) > 1:
            pygame.draw.lines(surf, color, False, points, width)

    def _traces(self, surf: pygame.Surface, session) -> None:
        traces = list(session.traces)
        if session.live_stroke:
            traces.append({"points": session.live_stroke, "color": (255, 244, 210), "life": 1.0, "max": 1.0})
        for trace in traces:
            points = trace["points"]
            if len(points) < 2:
                continue
            fade = max(0.0, trace["life"] / trace["max"])
            color = tuple(int(channel * fade) for channel in trace["color"])
            mapped = [_cam_to_screen(point, surf) for point in points]
            pygame.draw.lines(surf, color, False, mapped, 4)
            end = mapped[-1]
            pygame.draw.circle(surf, color, end, 5)

    def _banner(self, surf: pygame.Surface, session) -> None:
        if session.note_t > 0 and session.note:
            text = session.note
        elif session.mode == "duel" and session.duel.banner_t > 0:
            text = session.duel.banner
        elif session.mode == "story" and session.story.banner_t > 0:
            text = session.story.banner
        else:
            return
        font = self._font(36)
        image = font.render(text, True, CREAM)
        x = 470 - image.get_width() // 2
        y = 628
        pad = pygame.Surface((image.get_width() + 28, image.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(pad, (12, 8, 16, 170), pad.get_rect(), border_radius=10)
        surf.blit(pad, (x - 14, y - 6))
        self._text(surf, text, 36, (x, y), CREAM)

    def _inset(self, surf, mask, blob) -> None:
        preview = pygame.transform.scale(self._mask_surface(mask), (160, 120))
        surf.blit(preview, (24, 24))
        pygame.draw.rect(surf, GOLD, (24, 24, 160, 120), 1)
        if blob is not None:
            pygame.draw.circle(
                surf,
                GOLD,
                (24 + int(blob[0] * 160 / CAM_W), 24 + int(blob[1] * 120 / CAM_H)),
                4,
                1,
            )

    def _mask_surface(self, mask) -> pygame.Surface:
        import numpy as np

        height, width = mask.shape[:2]
        rgb = np.zeros((height, width, 3), dtype=np.uint8)
        rgb[:, :, 1] = 18
        rgb[:, :, 0] = 8
        lit = mask > 0
        rgb[lit] = (236, 255, 236)
        return pygame.image.frombuffer(rgb.tobytes(), (width, height), "RGB")

    def _vignette_blit(self, surf: pygame.Surface) -> None:
        if self.vignette is None or self.vignette.get_size() != surf.get_size():
            self.vignette = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            width, height = surf.get_size()
            for i, alpha in enumerate((70, 40, 18)):
                pad = i * 18
                pygame.draw.rect(self.vignette, (0, 0, 0, alpha), (pad, pad, width - pad * 2, height - pad * 2), 18)
        surf.blit(self.vignette, (0, 0))

    def _star(self, surf, x, y, radius, color) -> None:
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            dist = radius if i % 2 == 0 else radius * 0.4
            points.append((x + math.cos(angle) * dist, y + math.sin(angle) * dist))
        pygame.draw.polygon(surf, color, points)

    def _text(self, surf, text, size, pos, color, center=None) -> None:
        if not text:
            return
        font = self._font(size)
        image = font.render(text, True, color)
        shadow = font.render(text, True, (0, 0, 0))
        if center is not None:
            x = center[0] - image.get_width() // 2
            y = center[1]
        else:
            x, y = pos
        surf.blit(shadow, (x + 2, y + 2))
        surf.blit(image, (x, y))

    def _font(self, size: int) -> pygame.font.Font:
        cached = self.fonts.get(size)
        if cached is not None:
            return cached
        path = None
        for name in ("georgia", "garamond", "palatino", "timesnewroman", "liberationserif", "dejavuserif", "freeserif"):
            path = pygame.font.match_font(name)
            if path:
                break
        font = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
        self.fonts[size] = font
        return font


class Particles:
    def __init__(self):
        self.items: list[dict] = []

    def spawn(self, x, y, color, n=12, speed=90, life=0.6, upward=False, gravity=20) -> None:
        for _ in range(n):
            if len(self.items) > 360:
                break
            angle = random.uniform(-math.pi, 0) if upward else random.uniform(0, math.tau)
            fast = random.uniform(speed * 0.35, speed)
            self.items.append(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(angle) * fast,
                    "vy": math.sin(angle) * fast,
                    "life": random.uniform(life * 0.6, life),
                    "age": 0.0,
                    "color": color,
                    "r": random.uniform(2.0, 4.5),
                    "g": gravity,
                }
            )

    def update(self, dt: float) -> None:
        alive = []
        for particle in self.items:
            particle["age"] += dt
            if particle["age"] >= particle["life"]:
                continue
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += particle["g"] * dt
            alive.append(particle)
        self.items = alive

    def draw(self, surf: pygame.Surface) -> None:
        for particle in self.items:
            fade = 1.0 - particle["age"] / particle["life"]
            color = tuple(int(channel * fade) for channel in particle["color"])
            pygame.draw.circle(
                surf,
                color,
                (int(particle["x"]), int(particle["y"])),
                max(1, int(particle["r"] * fade + 0.4)),
            )


def _needed(session) -> str | None:
    if session.mode == "story":
        return session.story.needed()
    if session.mode == "duel":
        return session.duel.needed()
    return None


def _shape_points(kind: str, rect: pygame.Rect) -> list[tuple[float, float]]:
    x, y, w, h = rect
    if kind == "tide":
        points = []
        for i in range(40):
            angle = i / 39 * math.tau
            points.append((x + w / 2 + math.cos(angle) * w * 0.4, y + h / 2 + math.sin(angle) * h * 0.4))
        return points
    if kind == "flame":
        return [
            (x + w * 0.08, y + h * 0.18),
            (x + w * 0.92, y + h * 0.18),
            (x + w * 0.12, y + h * 0.84),
            (x + w * 0.92, y + h * 0.84),
        ]
    if kind == "frost":
        return [(x + w * 0.06, y + h * 0.5), (x + w * 0.94, y + h * 0.5)]
    if kind == "strike":
        return [(x + w * 0.16, y + h * 0.16), (x + w * 0.86, y + h * 0.86)]
    return []


def _cam_to_screen(point, surf: pygame.Surface) -> tuple[int, int]:
    width, height = surf.get_size()
    return int(point[0] / CAM_W * width), int(point[1] / CAM_H * height)


def _background(path: Path, size: tuple[int, int]):
    if not path.exists():
        return None
    image = pygame.image.load(str(path)).convert()
    return pygame.transform.smoothscale(image, size)


def _fit(image: pygame.Surface, height: int, opening: pygame.Rect | None):
    scale = height / image.get_height()
    size = (max(1, int(image.get_width() * scale)), height)
    scaled = pygame.transform.smoothscale(image, size)
    if opening is None:
        return scaled, None
    fitted = pygame.Rect(
        int(opening.x * scale),
        int(opening.y * scale),
        max(1, int(opening.w * scale)),
        max(1, int(opening.h * scale)),
    )
    return scaled, fitted


def _keyed_sprite(path: Path):
    """Remove the flat magenta backdrop and crop to the painted figure."""
    if not path.exists():
        return None, None
    import numpy as np

    image = pygame.image.load(str(path)).convert_alpha()
    rgb = pygame.surfarray.array3d(image)
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)
    # JPEG turns pure magenta into a pink that is redder than it is blue.
    pink = (green < 90) & (red > 150) & (blue > 80) & (red + 15 > blue) & ((red - green) > 100)
    mask = np.ascontiguousarray(pink.T.astype(np.uint8))
    try:
        import cv2

        _count, labels = cv2.connectedComponents(mask, connectivity=4)
    except ImportError:
        labels = mask
    border = np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    # Backdrop pink inside a tattered edge is not connected to the border, so clear every key pixel.
    remove = np.isin(labels, border[border != 0]) | pink.T
    alpha = np.full(remove.shape, 255, dtype=np.uint8)
    alpha[remove] = 0
    _clear_halo(alpha, red.T, green.T, blue.T)
    out = image.copy()
    pixels = pygame.surfarray.pixels_alpha(out)
    pixels[:, :] = np.ascontiguousarray(alpha.T)
    del pixels
    _despill(out, alpha)
    cropped = out.subsurface(out.get_bounding_rect()).copy()
    hole = pygame.surfarray.array_alpha(cropped)
    xs, ys = np.where(hole < 16)
    opening = None
    if len(xs) > 30:
        opening = pygame.Rect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min()), int(ys.max() - ys.min()))
    return cropped, opening


def _clear_halo(alpha, red, green, blue) -> None:
    """Drop the magenta fringe that stays connected to the backdrop after a JPEG key."""
    import numpy as np

    hot = (red > 140) & (blue > 90) & (green < 130) & ((red - green) > 35) & ((blue - green) > 20)
    region = np.ascontiguousarray(((alpha == 0) | hot).astype(np.uint8))
    try:
        import cv2

        _count, labels = cv2.connectedComponents(region, connectivity=8)
        border = np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
        linked = np.isin(labels, border[border != 0])
        alpha[linked & hot] = 0
    except ImportError:
        for _ in range(28):
            edge = _near(alpha == 0) & hot & (alpha > 0)
            if not edge.any():
                break
            alpha[edge] = 0


def _despill(image: pygame.Surface, alpha) -> None:
    """Turn any leftover pink rim into the dark color beside it."""
    import numpy as np

    rim = alpha == 0
    for _ in range(12):
        rim = _near(rim)
    rim = rim & (alpha > 0)
    if not rim.any():
        return
    rgb = pygame.surfarray.pixels3d(image)
    where = rim.T
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)
    tinted = where & ((red - green) > 12) & ((blue - green) > 8)
    rgb[:, :, 0][tinted] = np.minimum(red[tinted], green[tinted] + 28).astype(np.uint8)
    rgb[:, :, 2][tinted] = np.minimum(blue[tinted], green[tinted] + 36).astype(np.uint8)
    del rgb


def _door_mask(image: pygame.Surface):
    """True only inside the arch, not in the transparent corners around the stones."""
    import numpy as np

    alpha = pygame.surfarray.array_alpha(image)
    transparent = np.ascontiguousarray((alpha < 24).T.astype(np.uint8))
    try:
        import cv2

        _count, labels = cv2.connectedComponents(transparent, connectivity=4)
    except ImportError:
        return alpha < 24
    height, width = labels.shape
    touching = np.unique(np.concatenate([labels[0, :], labels[:, 0], labels[:, -1]]))
    touching = touching[touching != 0]
    exterior = np.isin(labels, touching)
    interior = (transparent > 0) & ~exterior
    interior[-max(8, height // 18) :, :] = False
    return np.ascontiguousarray(interior.T)


def _near(mask):
    import numpy as np

    padded = np.pad(mask, 1, constant_values=False)
    near = np.zeros(mask.shape, dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            near |= padded[1 + dy : 1 + dy + mask.shape[0], 1 + dx : 1 + dx + mask.shape[1]]
    return near
