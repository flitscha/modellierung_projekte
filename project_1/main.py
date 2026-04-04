import pygame
from simulation.simulation import Simulation
from rendering.renderer import Renderer
from rendering.hud import Hud
from core.camera import Camera
from input.input_handler import InputHandler


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Hohmann Transfer Simulator")
    clock = pygame.time.Clock()

    sim = Simulation()
    camera = Camera(screen_width=800, screen_height=800)
    renderer = Renderer(screen, camera)
    input_handler = InputHandler(camera)
    hud = Hud(screen)

    while not input_handler.quit_requested:
        events = pygame.event.get()
        input_handler.handle_events(events)

        dt = clock.tick(60) / 1000.0
        time_passed = dt * input_handler.sim_speed
        sim.update(time_passed)
        renderer.draw(sim)
        hud.draw(sim, sim_speed=input_handler.sim_speed, visible=input_handler.hud_visible)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
