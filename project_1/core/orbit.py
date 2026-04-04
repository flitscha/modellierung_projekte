from core.constants import PLANET_RADIUS

class Orbit:
    """
    Describes a Keplerian orbit around the central body.
 
    Parameters
    ----------
    semi_major_axis : float
        Semi-major axis in metres (= radius for circular orbits).
    eccentricity : float
        0 = circular, 0 < e < 1 = elliptic.
    """
 
    def __init__(self, semi_major_axis: float, eccentricity: float = 0.0):
        self.semi_major_axis = semi_major_axis
        self.eccentricity = eccentricity
 
    @property
    def periapsis(self) -> float:
        return self.semi_major_axis * (1 - self.eccentricity)
 
    @property
    def apoapsis(self) -> float:
        return self.semi_major_axis * (1 + self.eccentricity)
 
    @classmethod
    def circular(cls, altitude: float) -> "Orbit":
        """Create a circular orbit from an altitude above the planet surface."""
        return cls(semi_major_axis=PLANET_RADIUS + altitude)
