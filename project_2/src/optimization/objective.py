"""
This file determines how the optimizer behaves.

Two values need to be optimized:
- Bridge weight,
- bridge deflection.
"""

import numpy as np

from simulations.solve_truss import solve_truss
import config

W_MASS = 1.0
W_DEFLECTION = 5.0
MASS_REF_G = 100.0


def _run_truss(design, params) -> tuple[float, float]:
    geometry = design.build_geometry(params)
    truss = design.build_truss(params)
    displacements, _ = solve_truss(truss)

    max_deflection = float(max(abs(d[1]) for d in displacements))
    mass_g = float(geometry.estimate_weight_grams())

    return max_deflection, mass_g


def _deflection_penalty(max_deflection_mm: float) -> float:
    excess = max(0.0, max_deflection_mm - config.MAX_DEFLECTION)
    return (excess / config.MAX_DEFLECTION) ** 2


def compute_loss(design, params) -> dict | None:
    """
    Returns a result dict, or None (on numerical failure)
    """
    try:
        deflection_mm, mass_g = _run_truss(design, params)
    except np.linalg.LinAlgError:
        # singular stiffness matrix
        return None
    except Exception:
        return None

    if deflection_mm < 0.001: # avoid wrong results. The deflection cannot be smaller than 0.001
        return None

    term_mass = W_MASS * (mass_g / MASS_REF_G)
    term_deflection = W_DEFLECTION * _deflection_penalty(deflection_mm)
    loss = term_mass + term_deflection

    return {
        "loss": loss,
        "mass_g": mass_g,
        "deflection_mm": deflection_mm,
        "term_mass": term_mass,
        "term_deflection": term_deflection,
        "feasible": deflection_mm <= config.MAX_DEFLECTION,
    }

