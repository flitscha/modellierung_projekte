import pygame
from input.input_state import InputState


class InputReader:
    """Reads raw pygame events and produces an InputState each frame"""

    def __init__(self):
        self._panning = False
        self._pan_last_pos = (0, 0)

    def read(self, events: list[pygame.event.Event]) -> InputState:
        state = InputState(events=[])
        state.events = events
        state.mouse_pos = pygame.mouse.get_pos()

        for event in events:
            self._process(event, state)

        # Held keys
        keys = pygame.key.get_pressed()
        state.thrust_up = keys[pygame.K_UP]
        state.thrust_down = keys[pygame.K_DOWN]

        return state


    def _process(self, event: pygame.event.Event, state: InputState):
        if event.type == pygame.QUIT:
            state.quit = True

        elif event.type == pygame.MOUSEWHEEL:
            state.scroll_delta = event.y
            state.scroll_pos = pygame.mouse.get_pos()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (2, 3):
                self._panning = True
                self._pan_last_pos = event.pos
                state.pan_started = True
            elif event.button == 1:
                state.mouse_button_down = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (2, 3):
                self._panning = False
                state.pan_ended = True
            elif event.button == 1:
                state.mouse_button_up = True

        elif event.type == pygame.MOUSEMOTION:
            state.mouse_moved = True
            if self._panning:
                dx = event.pos[0] - self._pan_last_pos[0]
                dy = event.pos[1] - self._pan_last_pos[1]
                state.pan_delta = (dx, dy)
                self._pan_last_pos = event.pos

        elif event.type == pygame.KEYDOWN:
            self._process_key(event.key, state)

    def _process_key(self, key: int, state: InputState):
        if key == pygame.K_ESCAPE:
            state.escape_pressed = True
        elif key == pygame.K_a:
            state.a_pressed = True
        elif key == pygame.K_r:
            state.r_pressed = True
        elif key == pygame.K_h:
            state.h_pressed = True
        elif key == pygame.K_c:
            state.c_pressed = True
        elif key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
            state.plus_pressed = True
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            state.minus_pressed = True

