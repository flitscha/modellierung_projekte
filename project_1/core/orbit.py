import numpy as np
from core.constants import PLANET_RADIUS, G, PLANET_MASS

class Orbit:
    """
    Describes an elliptic orbit around the central body.
    Note: for the hohmann-transfer, we will only use circular orbits
 
    Parameters
    ----------
    semi_major_axis : float
        Semi-major axis in metres (= radius for circular orbits).
    eccentricity : float
        0 = circular, 0 < e < 1 = elliptic.
    argument_of_periapsis : float
        Angle in radians from the x axis to the periapsis direction.
        0 = periapsis points right, pi/2 = periapsis points up, etc.
    """
 
    def __init__(self, semi_major_axis: float, eccentricity: float = 0.0, argument_of_periapsis: float = 0.0):
        self.semi_major_axis = semi_major_axis
        self.eccentricity = eccentricity
        self.argument_of_periapsis = argument_of_periapsis
 
    @property
    def periapsis(self) -> float:
        return self.semi_major_axis * (1 - self.eccentricity)
 
    @property
    def apoapsis(self) -> float:
        return self.semi_major_axis * (1 + self.eccentricity)

    @property
    def periapsis_direction(self) -> np.ndarray:
        """Unit vector pointing from the focus toward the periapsis."""
        w = self.argument_of_periapsis
        return np.array([np.cos(w), np.sin(w)])
 
    @property
    def apoapsis_direction(self) -> np.ndarray:
        """Unit vector pointing from the focus toward the apoapsis."""
        return -self.periapsis_direction
 
    @property
    def periapsis_pos(self) -> np.ndarray:
        """World-space position of the periapsis (assuming planet at origin)."""
        return self.periapsis_direction * self.periapsis
 
    @property
    def apoapsis_pos(self) -> np.ndarray:
        """World-space position of the apoapsis (assuming planet at origin)."""
        return self.apoapsis_direction * self.apoapsis

    @property
    def is_circle(self) -> bool:
        return abs(self.eccentricity) <= 1e-8

    def state_at_periapsis(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Return (position, velocity) at the periapsis point.
 
        The velocity is tangential (perpendicular to the periapsis direction),
        computed from the vis-viva equation.
        """
        mu  = G * PLANET_MASS
        r   = self.periapsis
        v   = np.sqrt(mu * (2 / r - 1 / self.semi_major_axis))
 
        pos = self.periapsis_pos
 
        # Tangent = periapsis_direction rotated 90° counter-clockwise
        pd = self.periapsis_direction
        tangent = np.array([-pd[1], pd[0]])
        vel = tangent * v
 
        return pos, vel
 
    @classmethod
    def circular(cls, altitude: float) -> "Orbit":
        """Create a circular orbit from an altitude above the planet surface."""
        return cls(semi_major_axis=PLANET_RADIUS + altitude)

