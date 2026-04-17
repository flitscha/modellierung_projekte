import numpy as np
from dataclasses import dataclass
from core.constants import G, PLANET_MASS
from core.orbit import Orbit


@dataclass(frozen=True)
class HohmannTransfer:
    """
    Results of a Hohmann transfer calculation between two circular orbits.

    All velocities in m/s, time in seconds.
    """
    delta_v1: float  # impulse at burn 1 (m/s tangential)
    delta_v2: float  # impulse at burn 2 (m/s tangential)
    delta_v_total: float  # |dv1| + |dv2|
    transfer_time: float  # time between the two burns (s)


def compute_hohmann(orbit1: Orbit, orbit2: Orbit) -> HohmannTransfer:
    """
    Compute the optimal 2-impulse transfer between two coplanar circular orbits.
    """
    mu = G * PLANET_MASS

    r_burn1 = orbit1.periapsis  # this is the radius, because the orbits are circular
    r_burn2 = orbit2.periapsis

    # Semi-major axis of the transfer ellipse
    a_transfer = (r_burn1 + r_burn2) / 2.0

    # Velocities on the source/target orbits at the burn points (vis-viva)
    v1_orbit = np.sqrt(mu * (2 / r_burn1 - 1 / orbit1.semi_major_axis))
    v2_orbit = np.sqrt(mu * (2 / r_burn2 - 1 / orbit2.semi_major_axis))

    # Velocities on the transfer ellipse at the burn points (vis-viva)
    v1_transfer = np.sqrt(mu * (2 / r_burn1 - 1 / a_transfer))
    v2_transfer = np.sqrt(mu * (2 / r_burn2 - 1 / a_transfer))

    # Delta-v (positive = prograde)
    dv1 = v1_transfer - v1_orbit
    dv2 = v2_orbit - v2_transfer

    # Coast time = half period of transfer ellipse
    t_transfer = np.pi * np.sqrt(a_transfer**3 / mu)

    return HohmannTransfer(
        delta_v1=dv1,
        delta_v2=dv2,
        delta_v_total=abs(dv1) + abs(dv2),
        transfer_time=t_transfer
    )

