import pygame
import ctypes
from input.input_reader import InputReader
from game import Game


def main():
    # Windows DPI-Fix
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except AttributeError:
        pass

    pygame.init()
    screen = pygame.display.set_mode((500, 500), pygame.RESIZABLE)
    pygame.display.set_caption("Hohmann Transfer Simulator")
    clock = pygame.time.Clock()

    game = Game(screen)
    reader = InputReader()

    while game.running:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()

        inputs = reader.read(events)
        game.update(inputs, dt)
        game.draw(dt)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
