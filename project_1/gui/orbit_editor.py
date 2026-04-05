import pygame
import numpy as np
from dataclasses import dataclass
from core.orbit import Orbit


# Colors
COLOR_PANEL_BG      = (15, 15, 40, 230)
COLOR_PANEL_BORDER  = (60, 60, 100)
COLOR_TITLE         = (255, 255, 255)
COLOR_LABEL         = (180, 180, 180)
COLOR_VALUE         = (255, 220, 100)
COLOR_SLIDER_BG     = (40, 40, 70)
COLOR_SLIDER_START  = (80, 140, 255)
COLOR_SLIDER_TARGET = (80, 220, 120)
COLOR_HANDLE        = (255, 255, 255)
COLOR_CHECKBOX_ON   = (80, 220, 120)
COLOR_CHECKBOX_OFF  = (60, 60, 90)
COLOR_SECTION       = (120, 140, 180)
COLOR_BTN_BG        = (30, 30, 60, 220)
COLOR_BTN_BORDER    = (60, 60, 100)
COLOR_BTN_HOVER     = (255, 220, 100)
COLOR_BTN_DEFAULT   = (180, 180, 180)

# Panel layout
PANEL_WIDTH     = 340
PANEL_MARGIN    = 16  # from screen edge
FONT_TITLE      = 18
FONT_LABEL      = 14
FONT_BTN        = 15
SLIDER_WIDTH    = 280
SLIDER_H        = 6
HANDLE_R        = 5
ROW_H           = 38
CHECKBOX_SIZE   = 14
SECTION_H       = 24
BTN_W           = 110
BTN_H           = 28
BTN_GAP         = 8
PADDING         = 20

# parameter ranges
ALT_MIN   = 100e3
ALT_MAX   = 50_000e3
ECC_MIN   = 0.0
ECC_MAX   = 0.95
OMEGA_MIN = 0.0
OMEGA_MAX = 2 * np.pi


@dataclass
class SliderDef:
    label: str
    min_val: float
    max_val: float
    value: float
    fmt: str


def _fmt_alt(v):
    return f"{v/1e3:,.0f} km"

def _fmt_ecc(v):
    return f"{v:.3f}"

def _fmt_omega(v):
    return f"{np.degrees(v):.1f}°"


class OrbitEditor:
    """
    Compact side-panel orbit editor.
    The simulation and orbits remain visible behind it.

    handle_events() returns 'apply', 'cancel', or None.
    Use preview_start_orbit / preview_target_orbit for live rendering.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.title_font = pygame.font.SysFont("monospace", FONT_TITLE, bold=True)
        self.label_font = pygame.font.SysFont("monospace", FONT_LABEL)
        self.btn_font = pygame.font.SysFont("monospace", FONT_BTN)

        self.start_orbit: Orbit | None = None
        self.target_orbit: Orbit | None = None

        self._circular = [True, True]
        self._sliders: list[list[SliderDef]] = [[], []]
        self._dragging: tuple[int, int] | None = None


    def open(self, start_orbit: Orbit, target_orbit: Orbit):
        self.start_orbit = start_orbit
        self.target_orbit = target_orbit
        for i, orbit in enumerate([start_orbit, target_orbit]):
            self._circular[i] = (orbit.eccentricity == 0.0)
            self._sliders[i] = self._make_sliders(orbit)

    @property
    def preview_start_orbit(self) -> Orbit:
        return self._orbit_from_sliders(0)

    @property
    def preview_target_orbit(self) -> Orbit:
        return self._orbit_from_sliders(1)

    def handle_events(self, events: list[pygame.event.Event]) -> str | None:
        panel_rect = self._panel_rect()

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return 'cancel'

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                result = self._on_click(event.pos, panel_rect)
                if result:
                    return result

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging = None

            if event.type == pygame.MOUSEMOTION and self._dragging:
                oi, si = self._dragging
                sx, sy = self._slider_pos(panel_rect, oi, si)
                self._sliders[oi][si].value = self._pos_to_value(
                    event.pos[0], sx, self._sliders[oi][si]
                )

        return None

    def draw(self):
        panel = self._panel_rect()

        # Panel background
        bg = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        bg.fill(COLOR_PANEL_BG)
        self.screen.blit(bg, panel.topleft)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, panel, 1)

        y = panel.y + PADDING

        # Title
        t = self.title_font.render("ORBIT EDITOR", True, COLOR_TITLE)
        self.screen.blit(t, (panel.x + PADDING, y))
        y += t.get_height() + PADDING

        # Each orbit section
        for oi, label in enumerate(["START ORBIT", "TARGET ORBIT"]):
            y = self._draw_section(oi, label, panel, y)
            y += PADDING

        # Buttons
        bx = panel.x + PADDING
        self._draw_btn("Apply", pygame.Rect(bx, y, BTN_W, BTN_H))
        self._draw_btn("Cancel", pygame.Rect(bx + BTN_W + BTN_GAP, y, BTN_W, BTN_H))


    def _panel_rect(self) -> pygame.Rect:
        _, h = self.screen.get_size()
        panel_h = self._calc_panel_height()
        x = PANEL_MARGIN
        y = h // 2 - panel_h // 2
        return pygame.Rect(x, y, PANEL_WIDTH, panel_h)

    def _calc_panel_height(self) -> int:
        h = PADDING  # top padding
        h += self.title_font.get_height() + PADDING
        for oi in range(2):
            h += SECTION_H  # section label
            h += ROW_H  # checkbox row
            for si in range(len(self._sliders[oi])):
                if self._slider_visible(oi, si):
                    h += ROW_H
            h += PADDING
        h += BTN_H + PADDING  # buttons + bottom padding
        return h

    def _slider_pos(self, panel: pygame.Rect, oi: int, si: int) -> tuple[int, int]:
        """Return (x, y) of the slider track start."""
        y = panel.y + PADDING
        y += self.title_font.get_height() + PADDING
        for o in range(oi + 1):
            y += SECTION_H + ROW_H  # section label + checkbox
            for s in range(len(self._sliders[o])):
                if not self._slider_visible(o, s):
                    continue
                if o == oi and s == si:
                    return panel.x + PADDING, y + ROW_H // 2
                y += ROW_H
            y += PADDING
        return panel.x + PADDING, y


    # ---------------- Drawing -----------------------
    def _draw_section(self, oi: int, label: str, panel: pygame.Rect, y: int) -> int:
        x = panel.x + PADDING
        color = COLOR_SLIDER_START if oi == 0 else COLOR_SLIDER_TARGET

        # Section label
        s = self.label_font.render(label, True, color)
        self.screen.blit(s, (x, y))
        y += SECTION_H

        # Checkbox
        cb_rect = pygame.Rect(x, y + 2, CHECKBOX_SIZE, CHECKBOX_SIZE)
        pygame.draw.rect(
            self.screen,
            COLOR_CHECKBOX_ON if self._circular[oi] else COLOR_CHECKBOX_OFF,
            cb_rect
        )
        if self._circular[oi]:
            pygame.draw.line(
                self.screen, (0, 0, 0),
                (cb_rect.x+2, cb_rect.centery),
                (cb_rect.x+CHECKBOX_SIZE-2, cb_rect.centery), 2
            )
        cb_lbl = self.label_font.render("Circular", True, COLOR_LABEL)
        self.screen.blit(cb_lbl, (x + CHECKBOX_SIZE + 6, y))
        y += ROW_H

        # Sliders
        for si, sl in enumerate(self._sliders[oi]):
            if not self._slider_visible(oi, si):
                continue
            sx = x
            sy = y + ROW_H // 2
            self._draw_slider(sl, sx, sy, color)
            y += ROW_H

        return y

    def _draw_slider(self, sl: SliderDef, sx: int, sy: int, fill_color):
        # Label
        lbl = self.label_font.render(sl.label, True, COLOR_LABEL)
        self.screen.blit(lbl, (sx, sy - 20))

        # Value
        val = self.label_font.render(self._fmt(sl), True, COLOR_VALUE)
        self.screen.blit(val, (sx + SLIDER_WIDTH - val.get_width(), sy - 14))

        # Track
        pygame.draw.rect(self.screen, COLOR_SLIDER_BG, pygame.Rect(sx, sy, SLIDER_WIDTH, SLIDER_H), border_radius=3)

        # Fill
        t = (sl.value - sl.min_val) / (sl.max_val - sl.min_val)
        fw = int(t * SLIDER_WIDTH)
        if fw > 0:
            pygame.draw.rect(self.screen, fill_color, pygame.Rect(sx, sy, fw, SLIDER_H), border_radius=3)

        # Handle
        pygame.draw.circle(self.screen, COLOR_HANDLE, (sx + fw, sy + SLIDER_H // 2), HANDLE_R)

    def _draw_btn(self, label: str, rect: pygame.Rect):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill(COLOR_BTN_BG)
        self.screen.blit(bg, rect.topleft)
        pygame.draw.rect(self.screen, COLOR_BTN_BORDER, rect, 1)
        color = COLOR_BTN_HOVER if hovered else COLOR_BTN_DEFAULT
        s = self.btn_font.render(label, True, color)
        self.screen.blit(s, (rect.centerx - s.get_width()//2, rect.centery - s.get_height()//2))


    # ------------- interaction --------------------
    def _on_click(self, pos, panel: pygame.Rect) -> str | None:
        # Buttons
        y_btn = panel.bottom - BTN_H - PADDING
        apply_rect  = pygame.Rect(panel.x + PADDING, y_btn, BTN_W, BTN_H)
        cancel_rect = pygame.Rect(panel.x + PADDING + BTN_W + BTN_GAP, y_btn, BTN_W, BTN_H)

        if apply_rect.collidepoint(pos):
            self._apply()
            return 'apply'
        if cancel_rect.collidepoint(pos):
            return 'cancel'

        # Checkboxes + sliders
        for oi in range(2):
            # Checkbox hit area
            sx0, _ = self._slider_pos(panel, oi, 0)
            cb_y = self._checkbox_y(panel, oi)
            cb_rect = pygame.Rect(panel.x + PADDING, cb_y, CHECKBOX_SIZE + 60, ROW_H)
            if cb_rect.collidepoint(pos):
                self._circular[oi] = not self._circular[oi]
                if self._circular[oi]:
                    self._sliders[oi][1].value = 0.0
                    self._sliders[oi][2].value = 0.0
                return None

            # Sliders
            for si in range(len(self._sliders[oi])):
                if not self._slider_visible(oi, si):
                    continue
                sx, sy = self._slider_pos(panel, oi, si)
                hit = pygame.Rect(sx - HANDLE_R, sy - HANDLE_R * 2,
                                  SLIDER_WIDTH + HANDLE_R * 2, SLIDER_H + HANDLE_R * 4)
                if hit.collidepoint(pos):
                    self._sliders[oi][si].value = self._pos_to_value(
                        pos[0], sx, self._sliders[oi][si]
                    )
                    self._dragging = (oi, si)
                    return None

        return None

    def _checkbox_y(self, panel: pygame.Rect, oi: int) -> int:
        """Return the y of the checkbox row for orbit oi."""
        y = panel.y + PADDING + self.title_font.get_height() + PADDING
        for o in range(oi):
            y += SECTION_H + ROW_H
            for si in range(len(self._sliders[o])):
                if self._slider_visible(o, si):
                    y += ROW_H
            y += PADDING
        y += SECTION_H
        return y

    def _apply(self):
        self.start_orbit  = self._orbit_from_sliders(0)
        self.target_orbit = self._orbit_from_sliders(1)

    def _orbit_from_sliders(self, oi: int) -> Orbit:
        sl = self._sliders[oi]
        return Orbit(
            semi_major_axis=sl[0].value,
            eccentricity=0.0 if self._circular[oi] else sl[1].value,
            argument_of_periapsis=0.0 if self._circular[oi] else sl[2].value,
        )

    def _pos_to_value(self, mx: int, sx: int, sl: SliderDef) -> float:
        t = np.clip((mx - sx) / SLIDER_WIDTH, 0.0, 1.0)
        return sl.min_val + t * (sl.max_val - sl.min_val)

    def _slider_visible(self, oi: int, si: int) -> bool:
        return si == 0 or not self._circular[oi]


    def _make_sliders(self, orbit: Orbit) -> list[SliderDef]:
        return [
            SliderDef("Semi-major axis", ALT_MIN, ALT_MAX, orbit.semi_major_axis, "alt"),
            SliderDef("Eccentricity", ECC_MIN, ECC_MAX, orbit.eccentricity, "ecc"),
            SliderDef("Arg. periapsis", OMEGA_MIN, OMEGA_MAX, orbit.argument_of_periapsis, "omega"),
        ]

    def _fmt(self, sl: SliderDef) -> str:
        if sl.fmt == "alt":
            return _fmt_alt(sl.value)
        if sl.fmt == "ecc":
            return _fmt_ecc(sl.value)
        if sl.fmt == "omega":
            return _fmt_omega(sl.value)
        return str(sl.value)
