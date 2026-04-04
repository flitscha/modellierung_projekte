import pygame
from simulation.simulation import Simulation
from rendering.renderer import Renderer
from core.camera import Camera
from input.input_handler import InputHandler


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("Hohmann Transfer Simulator")
    clock = pygame.time.Clock()

    sim = Simulation()
    camera = Camera(screen_width=800, screen_height=800)
    renderer = Renderer(screen, camera)
    input_handler = InputHandler(camera)

    while not input_handler.quit_requested:
        events = pygame.event.get()
        input_handler.handle_events(events)

        dt = clock.tick(60) / 1000.0
        sim.update(dt)
        renderer.draw(sim)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
