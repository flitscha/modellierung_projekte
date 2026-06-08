# TODO: check correctness
"""
NACA 4-digit airfoil design.

The four-digit series is defined by three shape parameters:
    m  – maximum camber as fraction of chord  (first digit / 100)
    p  – position of max camber as fraction   (second digit / 10)
    t  – maximum thickness as fraction        (last two digits / 100)

Examples of well-known airfoils expressible in this space:
    NACA 0012  →  m=0.00, p=0.0, t=0.12   (symmetric, thin)
    NACA 2412  →  m=0.02, p=0.4, t=0.12   (classic GA airfoil)
    NACA 4412  →  m=0.04, p=0.4, t=0.12   (higher lift)
    NACA 4415  →  m=0.04, p=0.4, t=0.15
    NACA 6412  →  m=0.06, p=0.4, t=0.12   (high-lift, thinner)
"""
from __future__ import annotations
import numpy as np

import config
from core.design import Design
from core.airfoil import Airfoil
from core.parameter import FloatParameter


def _naca4_coords(m: float, p: float, t: float, n: int = 200) -> np.ndarray:
    """
    Generate NACA 4-digit airfoil coordinates in Selig format.

    Uses cosine spacing for better leading-edge resolution.
    Returns array of shape (2*n-1, 2).
    """
    # cosine spacing on [0, 1]
    beta = np.linspace(0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))          # n points, 0 → 1

    # ── thickness distribution ────────────────────────────────────────────────
    # Standard NACA 4-digit thickness formula (closed trailing edge variant)
    yt = (t / 0.2) * (
        0.2969 * np.sqrt(x) -
        0.1260 * x -
        0.3516 * x**2 +
        0.2843 * x**3 -
        0.1015 * x**4      # closed TE: -0.1015 (open: -0.1036)
    )

    # ── camber line ───────────────────────────────────────────────────────────
    yc    = np.zeros_like(x)
    dycdx = np.zeros_like(x)

    if m > 0 and p > 0:
        # forward of max-camber position
        mask1 = x < p
        yc[mask1]    = (m / p**2)    * (2*p*x[mask1] - x[mask1]**2)
        dycdx[mask1] = (2*m / p**2)  * (p - x[mask1])

        # aft of max-camber position
        mask2 = ~mask1
        yc[mask2]    = (m / (1-p)**2) * (1 - 2*p + 2*p*x[mask2] - x[mask2]**2)
        dycdx[mask2] = (2*m / (1-p)**2) * (p - x[mask2])

    theta = np.arctan(dycdx)

    # ── upper and lower surface ───────────────────────────────────────────────
    xu = x  - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x  + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    # ── Selig order: upper TE → LE, then lower LE → TE ───────────────────────
    upper = np.column_stack([xu[::-1], yu[::-1]])   # TE → LE
    lower = np.column_stack([xl[1:], yl[1:]])     # LE+1 → TE  (skip duplicate LE)
    return np.vstack([upper, lower])


class NACA4Design(Design):
    """
    Single design type: NACA 4-digit series.

    Parameters exposed to the UI / optimiser:
        camber     – m, maximum camber fraction       [0.00 … 0.09]
        camber_pos – p, position of max camber        [0.20 … 0.60]
        thickness  – t, maximum thickness fraction    [0.06 … 0.20]
    """

    def __init__(self):
        self.name = "NACA 4-digit"

    def parameter_space(self):
        return [
            FloatParameter("camber", config.MIN_CAMBER, config.MAX_CAMBER),
            FloatParameter("camber_pos", 0.20, 0.60),
            FloatParameter("thickness", config.MIN_THICKNESS, config.MAX_THICKNESS),
        ]

    def default_parameters(self):
        # Default: NACA 2412 – a well-understood, printable airfoil
        return {"camber": 0.02, "camber_pos": 0.40, "thickness": 0.12}

    def validate(self, params) -> bool:
        m = params["camber"]
        p = params["camber_pos"]
        t = params["thickness"]
        # symmetric airfoil: camber_pos doesn't matter, but keep p valid
        if m > 0 and not (0.1 < p < 0.9):
            return False
        if t < config.MIN_THICKNESS or t > config.MAX_THICKNESS:
            return False
        return True

    def build_airfoil(self, params) -> Airfoil:
        m = params["camber"]
        p = params["camber_pos"]
        t = params["thickness"]
        coords = _naca4_coords(m, p, t, n=config.N_PANELS + 1)
        # Build the NACA designation string
        m_str = f"{round(m*100):01d}"
        p_str = f"{round(p*10):01d}"
        t_str = f"{round(t*100):02d}"
        name  = f"NACA {m_str}{p_str}{t_str}"
        return Airfoil(coords, name=name)

