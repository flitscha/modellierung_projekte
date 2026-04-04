import numpy as np
import pygame

from utils.config import (
    COLOR_BG, COLOR_PLANET, COLOR_SHIP,
    COLOR_TARGET_ORBIT, COLOR_TRAIL_HEAD, COLOR_TRAIL_TAIL
)
from core.camera import Camera


class Renderer:
    def __init__(self, screen: pygame.Surface, camera: Camera):
        self.screen = screen
        self.camera = camera
        self.width, self.height = screen.get_size()

    def _draw_dashed_circle(self, color, center_world, radius_world: float,
                            dash_count: int = 60, dash_fraction: float = 0.55):
        center_screen = self.camera.world_to_screen(center_world)
        radius_px     = self.camera.world_len_to_screen(radius_world)
        if radius_px < 2:
            return
 
        angle_step = 2 * np.pi / dash_count
        dash_angle  = angle_step * dash_fraction
 
        for i in range(dash_count):
            start_angle = i * angle_step
            end_angle   = start_angle + dash_angle
            rect = pygame.Rect(
                center_screen[0] - radius_px,
                center_screen[1] - radius_px,
                radius_px * 2,
                radius_px * 2,
            )
            pygame.draw.arc(self.screen, color, rect, start_angle, end_angle, 1)
 
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


    def draw(self, sim):
        self.screen.fill(COLOR_BG)
 
        planet_pos = sim.planet.pos
 
        # Target orbit (dashed, green)
        self._draw_dashed_circle(COLOR_TARGET_ORBIT, planet_pos, sim.target_orbit.semi_major_axis)
 
        # Trail
        self._draw_trail(sim.trail)
 
        # Planet
        pygame.draw.circle(self.screen, COLOR_PLANET, self.camera.world_to_screen(planet_pos), 8)
 
        # Ship
        pygame.draw.circle(self.screen, COLOR_SHIP, self.camera.world_to_screen(sim.ship.pos), 3)

