import pygame
from core.camera import Camera
from utils.config import SIMULATION_SPEED_STEPS, DEFAULT_SIMULATION_SPEED_INDEX, BASE_SIMULATION_SPEED


class InputHandler:
    """
    Translates raw pygame events into actions on the camera (and other UI stuff)

    Usage in main loop
    ------------------
        handler.handle_events(events)  # call once per frame
        if handler.quit_requested:
            running = False
    """

    def __init__(self, camera: Camera):
        self.camera = camera
        self.quit_requested = False
        self.hud_visible = True

        self._speed_index = DEFAULT_SIMULATION_SPEED_INDEX
        self._panning = False
        self._pan_last_pos = (0, 0)

    @property
    def sim_speed(self) -> float:
        return SIMULATION_SPEED_STEPS[self._speed_index] * BASE_SIMULATION_SPEED

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            self._handle(event)

    def _handle(self, event: pygame.event.Event):
        if event.type == pygame.QUIT:
            self.quit_requested = True

        elif event.type == pygame.MOUSEWHEEL:
            self._on_scroll(event)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._on_mouse_down(event)

        elif event.type == pygame.MOUSEBUTTONUP:
            self._on_mouse_up(event)

        elif event.type == pygame.MOUSEMOTION:
            self._on_mouse_motion(event)

        elif event.type == pygame.KEYDOWN:
            self._on_key(event)

    def _on_scroll(self, event: pygame.event.Event):
        mouse_pos = pygame.mouse.get_pos()
        self.camera.zoom_at(mouse_pos, direction=event.y)

    def _on_mouse_down(self, event: pygame.event.Event):
        # Middle mouse button or right mouse button -> start panning
        if event.button in (2, 3):
            self._panning = True
            self._pan_last_pos = event.pos

    def _on_mouse_up(self, event: pygame.event.Event):
        if event.button in (2, 3):
            self._panning = False

    def _on_mouse_motion(self, event: pygame.event.Event):
        if self._panning:
            dx = event.pos[0] - self._pan_last_pos[0]
            dy = event.pos[1] - self._pan_last_pos[1]
            self.camera.pan((dx, dy))
            self._pan_last_pos = event.pos

    def _on_key(self, event: pygame.event.Event):
        if event.key == pygame.K_r:
            self.camera.reset()
 
        elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
            self._speed_index = min(self._speed_index + 1, len(SIMULATION_SPEED_STEPS) - 1)
 
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._speed_index = max(self._speed_index - 1, 0)
 
        elif event.key == pygame.K_h:
            self.hud_visible = not self.hud_visible

