import pygame
from simulation.simulation import Simulation
from rendering.renderer import Renderer


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 800))
    clock = pygame.time.Clock()

    sim = Simulation()
    renderer = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        dt = clock.tick(60) / 1000.0
        sim.update(dt)
        renderer.draw(sim)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
