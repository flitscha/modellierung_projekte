import numpy as np
from dataclasses import dataclass
from core.constants import G, PLANET_MASS
from core.orbit import Orbit


@dataclass(frozen=True)
class HohmannTransfer:
    """
    Results of a Hohmann transfer calculation between two elliptic orbits.

    All velocities in m/s, time in seconds.
    """
    delta_v1: float  # impulse at burn 1 (m/s, positive = prograde)
    delta_v2: float  # impulse at burn 2 (m/s, positive = prograde)
    delta_v_total: float  # |dv1| + |dv2|
    transfer_time: float  # coast time between the two burns (s)
    r_burn1: float  # radius at burn 1 (m)
    r_burn2: float  # radius at burn 2 (m)
    ascending: bool  # True = going to higher orbit


def compute_hohmann(orbit1: Orbit, orbit2: Orbit) -> HohmannTransfer:
    """
    Compute the optimal 2-impulse transfer between two coplanar elliptic orbits.

    For an ascending transfer (orbit2 higher than orbit1):
      - Burn 1 at the apoapsis of orbit1
      - Burn 2 at the periapsis of orbit2

    For a descending transfer:
      - Burn 1 at the periapsis of orbit1
      - Burn 2 at the apoapsis of orbit2
    """
    mu = G * PLANET_MASS

    ascending = orbit2.semi_major_axis >= orbit1.semi_major_axis

    if ascending:
        r_burn1 = orbit1.apoapsis
        r_burn2 = orbit2.periapsis
    else:
        r_burn1 = orbit1.periapsis
        r_burn2 = orbit2.apoapsis

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
    dv2 = v2_orbit    - v2_transfer

    # Coast time = half period of transfer ellipse
    t_transfer = np.pi * np.sqrt(a_transfer**3 / mu)

    return HohmannTransfer(
        delta_v1=dv1,
        delta_v2=dv2,
        delta_v_total=abs(dv1) + abs(dv2),
        transfer_time=t_transfer,
        r_burn1=r_burn1,
        r_burn2=r_burn2,
        ascending=ascending,
    )

