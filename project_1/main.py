import pygame
from input.input_reader import InputReader
from game import Game


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 800), pygame.RESIZABLE)
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
