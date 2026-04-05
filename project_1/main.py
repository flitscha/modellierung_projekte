import pygame
from simulation.simulation import Simulation
from rendering.renderer import Renderer
from gui.hud import Hud
from gui.menu import Menu, MenuAction
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
    hud = Hud(screen)
    menu = Menu(screen)
    input_handler = InputHandler(camera, sim.ship)
    menu_open = False

    while not input_handler.quit_requested:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()

        if menu_open:
            action = menu.handle_events(events)
            if action == MenuAction.RESUME:
                menu_open = False
            elif action == MenuAction.RESET:
                sim.reset_ship()
                autopilot.reset()
                menu_open = False
            elif action == MenuAction.QUIT:
                break
        else:
            input_handler.handle_events(events)
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        menu_open = True
                    elif event.key == pygame.K_a and not autopilot.is_active:
                        autopilot.start(sim)
                    elif event.key == pygame.K_r:
                        sim.reset_ship()
                        autopilot.reset()

            # Only update simulation when menu is closed
            time_passed = dt * input_handler.sim_speed
            autopilot.update(sim, time_passed)
            sim.update(time_passed)

        # Always draw – menu renders as overlay on top
        renderer.draw(sim)
        hud.draw(sim, sim_speed=input_handler.sim_speed, autopilot=autopilot, visible=input_handler.hud_visible)
        if menu_open:
            menu.draw()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
