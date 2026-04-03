import pygame
from utils.config import VISUALISATION_SCALE


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

    def world_to_screen(self, pos):
        x = self.width // 2 + int(pos[0] * VISUALISATION_SCALE)
        y = self.height // 2 + int(pos[1] * VISUALISATION_SCALE)
        return (x, y)

    def draw(self, sim):
        self.screen.fill((0, 0, 0))

        # planet
        pygame.draw.circle(
            self.screen,
            (0, 100, 255),
            self.world_to_screen(sim.planet.pos),
            8
        )

        # spaceship
        pygame.draw.circle(
            self.screen,
            (255, 255, 255),
            self.world_to_screen(sim.ship.pos),
            3
        )
