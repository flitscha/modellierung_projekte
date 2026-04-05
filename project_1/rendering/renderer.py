import numpy as np
import pygame

from utils.config import (
    COLOR_BG, COLOR_PLANET, COLOR_SHIP, COLOR_START_ORBIT,
    COLOR_TARGET_ORBIT, COLOR_TRAIL_HEAD, COLOR_TRAIL_TAIL
)
from core.camera import Camera
from core.orbit import Orbit


class Renderer:
    def __init__(self, screen: pygame.Surface, camera: Camera):
        self.screen = screen
        self.camera = camera
        self.width, self.height = screen.get_size()

    def _orbit_screen_points(self, orbit: Orbit, n_points: int = 256) -> list:
        """
        Sample n_points positions along the orbit and convert to screen coords.
 
        Uses the polar equation of an ellipse in the focus:
            r(theta) = p / (1 + e*cos(theta))
        where:
            p is the semi-latus-rectus: p = a * (1 - e^2)
            a is the semi-major-axis
            e is the eccentricity
        """
        e = orbit.eccentricity
        a = orbit.semi_major_axis
        w = orbit.argument_of_periapsis
 
        thetas = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
        if e < 1.0:
            rs = a * (1 - e**2) / (1 + e * np.cos(thetas))
        else:
            return []  # hyperbolic, skip
 
        # World positions (planet at origin)
        xs = rs * np.cos(thetas + w)
        ys = rs * np.sin(thetas + w)
 
        return [self.camera.world_to_screen((x, y)) for x, y in zip(xs, ys)]
 
    def _draw_orbit_solid(self, orbit: Orbit, color):
        pts = self._orbit_screen_points(orbit)
        if len(pts) >= 2:
            pygame.draw.lines(self.screen, color, closed=True, points=pts, width=1)
 
    def _draw_orbit_dashed(self, orbit: Orbit, color, dash: int = 6, gap: int = 4):
        pts = self._orbit_screen_points(orbit)
        n   = len(pts)
        if n < 2:
            return
        step = dash + gap
        for i in range(0, n, step):
            segment = pts[i: i + dash]
            if len(segment) >= 2:
                pygame.draw.lines(self.screen, color, closed=False, points=segment, width=1)
 
    def _draw_trail(self, trail):
        points = list(trail)
        n = len(points)
        if n < 2:
            return
 
        for i in range(1, n):
            t  = i / (n - 1)
            r  = int(COLOR_TRAIL_TAIL[0] + t * (COLOR_TRAIL_HEAD[0] - COLOR_TRAIL_TAIL[0]))
            g  = int(COLOR_TRAIL_TAIL[1] + t * (COLOR_TRAIL_HEAD[1] - COLOR_TRAIL_TAIL[1]))
            b  = int(COLOR_TRAIL_TAIL[2] + t * (COLOR_TRAIL_HEAD[2] - COLOR_TRAIL_TAIL[2]))
            p0 = self.camera.world_to_screen(points[i - 1])
            p1 = self.camera.world_to_screen(points[i])
            pygame.draw.line(self.screen, (r, g, b), p0, p1, 1)


    def draw(self, sim, override_start: Orbit | None = None, override_target: Orbit | None = None):
        """
        override_start / override_target let the orbit editor pass in
        preview orbits so the user sees live feedback while dragging sliders.
        """

        start_orbit  = override_start or sim.start_orbit
        target_orbit = override_target or sim.target_orbit

        self.screen.fill(COLOR_BG)
 
        planet_pos = sim.planet.pos
 
        # Target orbits
        self._draw_orbit_dashed(start_orbit, COLOR_START_ORBIT)
        self._draw_orbit_dashed(target_orbit, COLOR_TARGET_ORBIT)
 
        # Trail
        self._draw_trail(sim.trail)
 
        # Planet
        pygame.draw.circle(self.screen, COLOR_PLANET, self.camera.world_to_screen(planet_pos), 8)
 
        # Ship
        pygame.draw.circle(self.screen, COLOR_SHIP, self.camera.world_to_screen(sim.ship.pos), 3)

