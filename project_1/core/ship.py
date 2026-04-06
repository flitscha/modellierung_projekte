import numpy as np
from core.body import Body


class Ship(Body):
    """
    A controllable spaceship. Extends Body with thrust capabilities.
    """

    def __init__(self, mass: float, position, velocity):
        super().__init__(mass, position, velocity)
        self.total_delta_v: float = 0.0

    def reset_delta_v(self):
        self.total_delta_v = 0.0

    def apply_impulse(self, delta_v: np.ndarray):
        """Instantly change the ship's velocity by delta_v"""
        self.vel = self.vel + delta_v
        self.total_delta_v += np.linalg.norm(delta_v)

    def apply_impulse_tangential(self, magnitude: float):
        """Apply an impulse in the current prograde (tangential) direction"""
        tangent = self._tangential_direction()
        self.apply_impulse(tangent * magnitude)


    def _tangential_direction(self) -> np.ndarray:
        """Unit vector in the prograde direction (perpendicular to position)."""
        vel_norm = np.linalg.norm(self.vel)
        if vel_norm < 1e-10:
            return np.array([0.0, 1.0])
        return self.vel / vel_norm

