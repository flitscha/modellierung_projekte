import numpy as np

from config import DEFAULT_ZOOM, MAX_ZOOM, MIN_ZOOM, ZOOM_FACTOR


class Camera:
    """
    Attributes
    ----------
    zoom : float
        Pixels per meter. Higher = more zoomed in.
    center : np.ndarray
        World-space position [x, y] that maps to the screen center.
    """

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.zoom = DEFAULT_ZOOM
        self.center = np.array([0.0, 0.0])


    def world_to_screen(self, world_pos) -> tuple[int, int]:
        """Convert a world-space position to screen pixels."""
        dx = world_pos[0] - self.center[0]
        dy = world_pos[1] - self.center[1]
        x = self.screen_width  // 2 + int(dx * self.zoom)
        y = self.screen_height // 2 + int(dy * self.zoom)
        return (x, y)

    def screen_to_world(self, screen_pos) -> np.ndarray:
        """Convert screen pixels back to world-space."""
        dx = screen_pos[0] - self.screen_width  // 2
        dy = screen_pos[1] - self.screen_height // 2
        x = self.center[0] + dx / self.zoom
        y = self.center[1] + dy / self.zoom
        return np.array([x, y])

    def world_len_to_screen(self, length: float) -> int:
        """Convert a world-space length (meters) to pixels."""
        return max(1, int(length * self.zoom))

    def zoom_at(self, screen_pos, direction: int):
        """
        Zoom in (direction=+1) or out (direction=-1) centred on screen_pos.
        Keeps the world point under the mouse cursor fixed.
        """
        world_before = self.screen_to_world(screen_pos)

        factor = ZOOM_FACTOR if direction > 0 else 1.0 / ZOOM_FACTOR
        self.zoom = float(np.clip(self.zoom * factor, MIN_ZOOM, MAX_ZOOM))

        # Shift center so the point under the cursor stays fixed
        world_after = self.screen_to_world(screen_pos)
        self.center -= world_after - world_before

    def pan(self, delta_screen):
        """
        Pan the camera by delta_screen pixels.
        delta_screen = (dx, dy) in screen space.
        """
        self.center[0] -= delta_screen[0] / self.zoom
        self.center[1] -= delta_screen[1] / self.zoom

    def reset(self):
        """Snap back to origin with default zoom."""
        self.zoom   = DEFAULT_ZOOM
        self.center = np.array([0.0, 0.0])

