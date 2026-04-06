import numpy as np
import pygame
from utils.config import (
    COLOR_BG, COLOR_PLANET, COLOR_SHIP, COLOR_START_ORBIT,
    COLOR_TARGET_ORBIT, COLOR_TRAIL_HEAD, COLOR_TRAIL_TAIL
)
from core.camera import Camera
from core.orbit import Orbit
from core.constants import PLANET_RADIUS
from rendering.particles import ParticleSystem


COLOR_PLANET_BORDER = (80, 140, 255)
COLOR_PLANET_FILL = (*COLOR_PLANET[:3], 100)  # semi-transparent


class Renderer:
    def __init__(self, screen: pygame.Surface, camera: Camera):
        self.screen = screen
        self.camera = camera
        self.width, self.height = screen.get_size()
        self.particles = ParticleSystem()

    def notify_impulse(self, ship):
        """Spawns a particle burst at the ship's current position."""
        self.particles.spawn_burst(
            world_pos=np.array(ship.pos, dtype=float),
            thrust_direction=ship.last_thrust_dir,
            delta_v_magnitude=ship.last_delta_v_mag,
        )
 
    def update(self, real_dt: float):
        """Advance particles. Call every frame with real dt (not sim dt)."""
        self.particles.update(real_dt)

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

        xs = rs * np.cos(thetas + w)
        ys = rs * np.sin(thetas + w)

        return [self.camera.world_to_screen((x, y)) for x, y in zip(xs, ys)]

    def _draw_orbit_solid(self, orbit: Orbit, color):
        pts = self._orbit_screen_points(orbit)
        if len(pts) >= 2:
            pygame.draw.lines(self.screen, color, closed=True, points=pts, width=1)

    def _draw_orbit_dashed(self, orbit: Orbit, color, dash: int = 6, gap: int = 4):
        pts = self._orbit_screen_points(orbit)
        n = len(pts)
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

    def _draw_planet(self, planet_pos):
        center    = self.camera.world_to_screen(planet_pos)
        radius_px = self.camera.world_len_to_screen(PLANET_RADIUS)

        # Always visible, even when zoomed far out
        radius_px = max(radius_px, 6)

        # Semi-transparent fill so ship remains visible if inside the planet
        surf = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, COLOR_PLANET_FILL, (radius_px, radius_px), radius_px)
        self.screen.blit(surf, (center[0] - radius_px, center[1] - radius_px))

        # Solid border
        pygame.draw.circle(self.screen, COLOR_PLANET_BORDER, center, radius_px, 1)


    def draw(self, sim, override_start: Orbit | None = None,
             override_target: Orbit | None = None):
        """
        override_start / override_target let the orbit editor pass in
        preview orbits so the user sees live feedback while dragging sliders.
        """
        start_orbit  = override_start or sim.start_orbit
        target_orbit = override_target or sim.target_orbit

        self.screen.fill(COLOR_BG)

        # Orbits (bottom layer)
        self._draw_orbit_dashed(start_orbit, COLOR_START_ORBIT)
        self._draw_orbit_dashed(target_orbit, COLOR_TARGET_ORBIT)

        # Planet
        self._draw_planet(sim.planet.pos)

        # Trail
        self._draw_trail(sim.trail)

        # Particles
        self.particles.draw(self.screen, self.camera)

        # Ship
        pygame.draw.circle(self.screen, COLOR_SHIP,
                           self.camera.world_to_screen(sim.ship.pos), 3)
