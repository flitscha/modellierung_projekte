"""
NACA 4-digit airfoil design.

The four-digit series is defined by three shape parameters:
    m - maximum camber as fraction of chord (first digit / 100)
    p - position of max camber as fraction (second digit / 10)
    t - maximum thickness as fraction (last two digits / 100)
"""
from __future__ import annotations
import numpy as np

import config
from core.design import Design
from core.airfoil import Airfoil
from core.parameter import FloatParameter


def _naca4_coords(m: float, p: float, t: float, n: int = 200) -> np.ndarray:
    """
    Generate NACA 4-digit airfoil coordinates in Selig format, using cosine spacing
    """
    beta = np.linspace(0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))

    # Standard NACA 4-digit thickness formula
    yt = (t / 0.2) * (
        0.2969 * np.sqrt(x) -
        0.1260 * x -
        0.3516 * x**2 +
        0.2843 * x**3 -
        0.1015 * x**4
    )

    # camber line
    yc = np.zeros_like(x)
    dycdx = np.zeros_like(x)

    if m > 0 and p > 0:
        # forward of max-camber position
        mask1 = x < p
        yc[mask1] = (m / p**2) * (2*p*x[mask1] - x[mask1]**2)
        dycdx[mask1] = (2*m / p**2) * (p - x[mask1])

        # aft of max-camber position
        mask2 = ~mask1
        yc[mask2]    = (m / (1-p)**2) * (1 - 2*p + 2*p*x[mask2] - x[mask2]**2)
        dycdx[mask2] = (2*m / (1-p)**2) * (p - x[mask2])

    theta = np.arctan(dycdx)

    # upper and lower surface
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    # Selig order: upper TE (trailing edge) -> LE (leading edge), then lower LE -> TE
    upper = np.column_stack([xu[::-1], yu[::-1]]) # TE → LE
    lower = np.column_stack([xl[1:], yl[1:]]) # LE+1 → TE
    return np.vstack([upper, lower])


class NACA4Design(Design):
    def __init__(self):
        self.name = "NACA 4-digit"

    def parameter_space(self):
        return [
            FloatParameter("camber", config.MIN_CAMBER, config.MAX_CAMBER),
            FloatParameter("camber_pos", 0.20, 0.60),
            FloatParameter("thickness", config.MIN_THICKNESS, config.MAX_THICKNESS),
        ]

    def default_parameters(self):
        # Default: NACA 2412
        return {"camber": 0.02, "camber_pos": 0.40, "thickness": 0.12}

    def validate(self, params) -> bool:
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
        name = f"NACA {m_str}{p_str}{t_str}"
        return Airfoil(coords, name=name)

