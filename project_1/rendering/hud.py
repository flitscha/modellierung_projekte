import pygame
import numpy as np

from core.constants import G, PLANET_MASS, PLANET_RADIUS
from simulation.autopilot import Autopilot, AutopilotState

MARGIN = 12  # px from screen edge
LINE_HEIGHT = 18
FONT_SIZE = 15
PANEL_PADDING = 8
PANEL_COLOR = (20, 20, 40, 180)  # semi-transparent dark blue
TEXT_COLOR = (210, 210, 210)
LABEL_COLOR = (120, 140, 180)  # dimmer, for labels
HIGHLIGHT_COLOR = (255, 220, 100)  # yellow, for important values
SUCCESS_COLOR = (80, 220, 120)


def _orbital_period(semi_major_axis: float) -> float:
    """
    Keplerian orbital period in seconds.
    see https://en.wikipedia.org/wiki/Orbital_period
    """
    return 2 * np.pi * np.sqrt(semi_major_axis**3 / (G * PLANET_MASS))


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


class Hud:
    """
    Renders simulation info as overlay panels.

    Panels:
    - Simulation speed (top-left)
    - Start / target orbit info (top-right)
    - Ship telemetry (bottom-left)
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("monospace", FONT_SIZE)
        self.width, self.height = screen.get_size()

        # Pre-create a reusable surface for panel backgrounds
        self._panel_surf = pygame.Surface((1, 1), pygame.SRCALPHA)

    def draw(self, sim, sim_speed: float, autopilot: Autopilot, visible: bool):
        if not visible:
            return

        w, h = self.screen.get_size()
        self._draw_sim_speed(sim_speed, w, h)
        self._draw_orbit_info(sim, w, h)
        self._draw_ship_telemetry(sim, w, h)
        self._draw_autopilot(autopilot, w, h)

    def _draw_sim_speed(self, sim_speed: float, w: int, h: int):
        lines = [
            ("SIM SPEED", None),
            (f"{sim_speed:g}×", HIGHLIGHT_COLOR),
            ("[ - / + ]", LABEL_COLOR),
        ]
        self._draw_panel(lines, x=MARGIN, y=MARGIN)

    def _draw_orbit_info(self, sim, w: int, h: int):
        def orbit_lines(label: str, orbit) -> list:
            r      = orbit.semi_major_axis
            alt_km = (r - PLANET_RADIUS) / 1000
            period = _orbital_period(r)
            return [
                (label, None),
                (f"  Alt:    {alt_km:,.0f} km", TEXT_COLOR),
                (f"  SMA:    {r/1e6:.3f} Mm", TEXT_COLOR),
                (f"  Period: {_format_time(period)}", TEXT_COLOR),
            ]

        lines = (
            orbit_lines("START ORBIT", sim.start_orbit) + [("", None)] + orbit_lines("TARGET ORBIT", sim.target_orbit)
        )

        # Anchor to top-right
        panel_w = 210
        self._draw_panel(lines, x=w - panel_w - MARGIN, y=MARGIN, fixed_width=panel_w)

    def _draw_ship_telemetry(self, sim, w: int, h: int):
        vel = sim.ship.vel
        speed = np.linalg.norm(vel)
        r = np.linalg.norm(sim.ship.pos - sim.planet.pos)
        alt_km = (r - PLANET_RADIUS) / 1000

        lines = [
            ("SHIP", None),
            (f"  Speed:  {speed:.0f} m/s", TEXT_COLOR),
            (f"  Alt:    {alt_km:,.0f} km", TEXT_COLOR),
        ]
        # Anchor to bottom-left
        panel_h = LINE_HEIGHT * len(lines) + PANEL_PADDING * 2
        self._draw_panel(lines, x=MARGIN, y=h - panel_h - MARGIN)

    def _draw_autopilot(self, autopilot: Autopilot, w: int, h: int):
        state = autopilot.state
        t     = autopilot.transfer
 
        if state == AutopilotState.IDLE:
            lines = [
                ("AUTOPILOT", None),
                ("  IDLE", LABEL_COLOR),
                ("  [A] start", LABEL_COLOR),
            ]
        elif state == AutopilotState.WAITING:
            lines = [
                ("AUTOPILOT", None),
                ("  WAITING FOR BURN 1", HIGHLIGHT_COLOR),
                (f"  r_burn1: {t.r_burn1/1e6:.3f} Mm", TEXT_COLOR),
                (f"  dv1: {t.delta_v1:+.1f} m/s", TEXT_COLOR),
            ]
        elif state == AutopilotState.COASTING:
            eta = autopilot.time_to_burn2
            lines = [
                ("AUTOPILOT", None),
                ("  WAITING FOR BURN 2", HIGHLIGHT_COLOR),
                (f"  dv1: {t.delta_v1:+.1f} m/s (DONE)", TEXT_COLOR),
                (f"  dv2:  {t.delta_v2:+.1f} m/s", TEXT_COLOR),
                (f"  ETA:  {_format_time(eta)}", HIGHLIGHT_COLOR),
            ]
        elif state == AutopilotState.DONE:
            lines = [
                ("AUTOPILOT", None),
                ("  DONE", SUCCESS_COLOR),
                (f"  dv1: {t.delta_v1:+.1f} m/s", TEXT_COLOR),
                (f"  dv2: {t.delta_v2:+.1f} m/s", TEXT_COLOR),
                (f"  dvT: {t.delta_v_total:.1f} m/s", HIGHLIGHT_COLOR),
            ]
        else:
            return
 
        ship_lines   = 5
        ship_panel_h = LINE_HEIGHT * ship_lines + PANEL_PADDING * 2
        ap_panel_h   = LINE_HEIGHT * len(lines)  + PANEL_PADDING * 2
        y = h - ship_panel_h - ap_panel_h - MARGIN * 2
        self._draw_panel(lines, x=MARGIN, y=y)


    def _draw_panel(self, lines: list, x: int, y: int, fixed_width: int | None = None):
        """
        Draw a semi-transparent panel with text lines.

        Each entry in `lines` is (text, color). If color is None, the
        line is treated as a section header (label color + small gap above).
        """
        if fixed_width:
            panel_w = fixed_width
        else:
            max_w   = max(self.font.size(text)[0] for text, _ in lines if text)
            panel_w = max_w + PANEL_PADDING * 2

        panel_h = LINE_HEIGHT * len(lines) + PANEL_PADDING * 2

        # Background
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_COLOR)
        self.screen.blit(bg, (x, y))

        # Text
        ty = y + PANEL_PADDING
        for text, color in lines:
            if not text:
                ty += LINE_HEIGHT // 2  # empty line -> half gap
                continue
            if color is None:
                color = LABEL_COLOR  # section headers use label color
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (x + PANEL_PADDING, ty))
            ty += LINE_HEIGHT

