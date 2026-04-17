import numpy as np
from core.body import Body
from core.orbit import Orbit
from core.constants import G


class Ship(Body):
    """
    A controllable spaceship. Extends Body with thrust capabilities.
    """

    def __init__(self, mass: float, position, velocity):
        super().__init__(mass, position, velocity)
        self.total_delta_v: float = 0.0

        # Set by apply_impulse, used to spawn particles
        self.last_thrust_dir: np.ndarray = np.array([0.0, 1.0])
        self.last_delta_v_mag: float = 0.0

    def reset_delta_v(self):
        self.total_delta_v = 0.0
        self.last_delta_v_mag = 0.0

    def apply_impulse(self, delta_v: np.ndarray):
        """Instantly change the ship's velocity by delta_v"""
        mag = float(np.linalg.norm(delta_v))
        if mag > 1e-10:
            self.last_thrust_dir  = delta_v / mag
            self.last_delta_v_mag = mag
        self.vel = self.vel + delta_v
        self.total_delta_v += mag

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


    def get_current_orbit(self, planet: Body) -> Orbit:
        r_vec_2d = self.pos - planet.pos
        v_vec_2d = self.vel - planet.vel

        # embed in 3d (this way it is easier to implement the formulas that use cross-products)
        r_vec = np.array([r_vec_2d[0], r_vec_2d[1], 0.0])
        v_vec = np.array([v_vec_2d[0], v_vec_2d[1], 0.0])

        r = np.linalg.norm(r_vec)
        v = np.linalg.norm(v_vec)

        mu = G * planet.mass

        if r < 1e-10:
            return Orbit(0.0, 0.0, 0.0)

        # calculate the semi-major axis by transforming the vis-viva equation
        _denominator = 2 * mu - v*v * r
        if abs(_denominator) < 1e-10:
            semi_major_axis = np.inf # parabolic orbit
        else:
            semi_major_axis = (mu * r) / _denominator

        # calculate the eccentricity (https://en.wikipedia.org/wiki/Eccentricity_vector)

        # specific relative angular momentum vector (https://en.wikipedia.org/wiki/Specific_angular_momentum)
        h_vec = np.cross(r_vec, v_vec)

        eccentricity_vector = np.cross(v_vec, h_vec) / mu - r_vec / r
        eccentricity = np.linalg.norm(eccentricity_vector)


        # argument of periapsis (https://en.wikipedia.org/wiki/Argument_of_periapsis)
        if eccentricity > 1e-10:
            argument_of_periapsis = np.atan2(eccentricity_vector[1], eccentricity_vector[0])
        else:
            argument_of_periapsis = 0.0

        return Orbit(semi_major_axis, eccentricity, argument_of_periapsis)

