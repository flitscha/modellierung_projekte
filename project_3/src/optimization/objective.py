"""
Objective function for Airfoil Optimization.
Calculates the mean or min Cl over a range of angles of attack.
"""
import numpy as np
import dearpygui.dearpygui as dpg

from simulations.solver_fast import solve_panel_method

def compute_loss(design, params) -> dict | None:
    """
    Computes performance metrics for a given airfoil parameter set.
    Since we want to maximize Cl, our 'loss' is the negative mean Cl
    """
    # Validate parameters geometrically
    if not design.validate(params):
        return None

    # Extract settings from UI safely (fallback to 3 samples if item doesn't exist yet)
    num_samples = 3
    if dpg.does_item_exist("opt_alpha_samples"):
        num_samples = int(dpg.get_value("opt_alpha_samples"))

    objective_target = "Maximize Mean Cl"
    if dpg.does_item_exist("opt_objective_target"):
        objective_target = dpg.get_value("opt_objective_target")

    # Generate alphas (e.g. 3 samples -> [0.0, 5.0, 10.0])
    alphas = np.linspace(0.0, 10.0, num_samples)

    try:
        airfoil = design.build_airfoil(params)
    except Exception:
        return None

    cls = []

    # Run panel method over the sampled alpha values
    for alpha in alphas:
        try:
            results = solve_panel_method(airfoil, alpha_deg=float(alpha))
            cls.append(results["cl"])
        except Exception:
            return None

    if not cls:
        return None

    mean_cl = float(np.mean(cls))
    min_cl = float(np.min(cls))
    max_cl = float(np.max(cls))

    # Determine optimization loss based on chosen objective target
    if objective_target == "Maximize Mean Cl":
        loss = -mean_cl
    else:
        loss = -min_cl

    return {
        "loss": loss,
        "mean_cl": mean_cl,
        "min_cl": min_cl,
        "max_cl": max_cl,
        "feasible": True,
    }

