import pygame
from simulation.simulation import Simulation
from rendering.renderer import Renderer
from rendering.hud import Hud
from core.camera import Camera
from input.input_handler import InputHandler
from simulation.autopilot import Autopilot


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Hohmann Transfer Simulator")
    clock = pygame.time.Clock()

    sim = Simulation()
    autopilot = Autopilot()
    camera = Camera(screen_width=800, screen_height=800)
    renderer = Renderer(screen, camera)
    ship = sim.ship
    input_handler = InputHandler(camera, ship)
    hud = Hud(screen)

    while not input_handler.quit_requested:
        events = pygame.event.get()
        input_handler.handle_events(events)

        # Autopilot trigger – needs sim, so handled here rather than in InputHandler
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                if not autopilot.is_active:
                    autopilot.start(sim)
 
        dt = clock.tick(60) / 1000.0
        time_passed = dt * input_handler.sim_speed

        autopilot.update(sim, time_passed)
        sim.update(time_passed)
        renderer.draw(sim)
        hud.draw(sim, sim_speed=input_handler.sim_speed, autopilot=autopilot, visible=input_handler.hud_visible)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
