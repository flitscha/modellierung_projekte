import numpy as np
import pygame

from utils.config import (
    VISUALISATION_SCALE, COLOR_BG, COLOR_PLANET, COLOR_SHIP, COLOR_START_ORBIT,
    COLOR_TARGET_ORBIT, COLOR_TRAIL_HEAD, COLOR_TRAIL_TAIL
)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

    def world_to_screen(self, pos):
        x = self.width // 2 + int(pos[0] * VISUALISATION_SCALE)
        y = self.height // 2 + int(pos[1] * VISUALISATION_SCALE)
        return (x, y)

    def world_len_to_screen(self, length: float) -> int:
        """Convert a world-space length (metres) to screen pixels."""
        return max(1, int(length * VISUALISATION_SCALE))

    def _draw_dashed_circle(
        self,
        color,
        center_screen: tuple[int, int],
        radius_px: int,
        dash_count: int = 60,
        dash_fraction: float = 0.55,
    ):
        """Draw a circle made of small arcs"""
        if radius_px < 2:
            return
 
        angle_step = 2 * np.pi / dash_count
        dash_angle  = angle_step * dash_fraction
 
        for i in range(dash_count):
            start_angle = i * angle_step
            end_angle   = start_angle + dash_angle
 
            # Build a bounding rect for pygame.draw.arc
            rect = pygame.Rect(
                center_screen[0] - radius_px,
                center_screen[1] - radius_px,
                radius_px * 2,
                radius_px * 2,
            )
            pygame.draw.arc(self.screen, color, rect, start_angle, end_angle, 1)
 
    def _draw_trail(self, trail):
        """Draw the ship trail with a fade from tail to head."""
        points = list(trail)
        n = len(points)
        if n < 2:
            return
 
        for i in range(1, n):
            t = i / (n - 1)          # 0 at tail, 1 at head
 
            # Lerp colour
            r = int(COLOR_TRAIL_TAIL[0] + t * (COLOR_TRAIL_HEAD[0] - COLOR_TRAIL_TAIL[0]))
            g = int(COLOR_TRAIL_TAIL[1] + t * (COLOR_TRAIL_HEAD[1] - COLOR_TRAIL_TAIL[1]))
            b = int(COLOR_TRAIL_TAIL[2] + t * (COLOR_TRAIL_HEAD[2] - COLOR_TRAIL_TAIL[2]))
 
            p0 = self.world_to_screen(points[i - 1])
            p1 = self.world_to_screen(points[i])
            pygame.draw.line(self.screen, (r, g, b), p0, p1, 1)


    def draw(self, sim):
        self.screen.fill(COLOR_BG)
 
        center = self.world_to_screen(sim.planet.pos)
 
        # Start orbit (solid, dim)
        #r_start = self.world_len_to_screen(sim.start_orbit.semi_major_axis)
        #pygame.draw.circle(self.screen, COLOR_START_ORBIT, center, r_start, 1)

        # Target orbit (dashed, green)
        r_target = self.world_len_to_screen(sim.target_orbit.semi_major_axis)
        self._draw_dashed_circle(COLOR_TARGET_ORBIT, center, r_target)
 
        # Trail
        self._draw_trail(sim.trail)
 
        # Planet
        pygame.draw.circle(self.screen, COLOR_PLANET, center, 8)
 
        # Ship
        ship_screen = self.world_to_screen(sim.ship.pos)
        pygame.draw.circle(self.screen, COLOR_SHIP, ship_screen, 3)
