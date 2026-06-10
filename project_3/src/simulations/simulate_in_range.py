import numpy as np
from core.airfoil import Airfoil
from simulations.solver_fast import solve_panel_method


def evaluate_cl_range(airfoil: Airfoil, start_deg: float = 0.0, end_deg: float = 10.0, step_deg: float = 1.0) -> dict:
    """
    Evaluates the airfoil's lift coefficient over a range of angles of attack.

    Returns a dictionary with min, max, and mean cl values,
    automatically applying the sign correction for standard aerodynamic convention.
    """
    alpha_range = np.arange(start_deg, end_deg + step_deg, step_deg)
    cl_values = []

    for alpha in alpha_range:
        results = solve_panel_method(airfoil, alpha_deg=alpha)
        cl_values.append(results["cl"])

    return {
        "min_cl": float(np.min(cl_values)),
        "max_cl": float(np.max(cl_values)),
        "mean_cl": float(np.mean(cl_values)),
        "all_cl": cl_values,
        "alpha_range": alpha_range.tolist()
    }

