"""
optimization/objective.py
=========================
Loss function for bridge optimisation.

Loss = w_mass * (mass / mass_ref) + w_deflection * deflection_penalty(max_deflection)

The deflection penalty is a smooth ramp:
  - below the limit  → 0  (constraint satisfied, only mass counts)
  - above the limit  → grows quadratically

Returns None on any solver failure (singular matrix, etc.) so callers
can substitute a penalty value without crashing.
"""

import numpy as np

from simulations.solve_truss import solve_truss

W_MASS            = 1.0
W_DEFLECTION      = 5.0
MASS_REF_G        = 100.0
DEFLECTION_LIMIT  = 3.0   # mm
LOAD_KG           = 5.0


def _run_truss(design, params) -> tuple[float, float]:
    geometry = design.build_geometry(params)
    truss    = design.build_truss(params)

    xs = [n.x for n in truss.nodes]
    min_x, max_x = min(xs), max(xs)

    bottom_nodes = [i for i, n in enumerate(truss.nodes) if n.y == 0]
    mid_node   = min(bottom_nodes, key=lambda i: abs(truss.nodes[i].x - 0.5 * (min_x + max_x)))
    left_node  = min(bottom_nodes, key=lambda i: truss.nodes[i].x)
    right_node = max(bottom_nodes, key=lambda i: truss.nodes[i].x)

    F = LOAD_KG * 9.81
    forces     = {mid_node: (0.0, -F)}
    fixed_dofs = [(left_node, 0), (left_node, 1), (right_node, 1)]

    # np.linalg.LinAlgError is raised here if the matrix is singular
    displacements, _ = solve_truss(truss, forces, fixed_dofs, E=2500.0)

    max_deflection = float(max(abs(d[1]) for d in displacements))
    mass_g         = float(geometry.estimate_weight_grams())

    return max_deflection, mass_g


def _deflection_penalty(max_deflection_mm: float) -> float:
    excess = max(0.0, max_deflection_mm - DEFLECTION_LIMIT)
    return (excess / DEFLECTION_LIMIT) ** 2


def compute_loss(design, params) -> dict | None:
    """
    Returns a result dict, or None on any numerical failure.

    Callers should treat None as a high-penalty case.
    """
    try:
        deflection_mm, mass_g = _run_truss(design, params)
    except np.linalg.LinAlgError:
        # singular stiffness matrix → mechanism, not a valid structure
        return None
    except Exception:
        return None

    # sanity check: a real bridge won't deflect less than 0.001 mm under 5 kg
    # if we see something smaller it's a degenerate near-zero-length member
    if deflection_mm < 0.001:
        return None

    term_mass       = W_MASS * (mass_g / MASS_REF_G)
    term_deflection = W_DEFLECTION * _deflection_penalty(deflection_mm)
    loss            = term_mass + term_deflection

    return {
        "loss": loss,
        "mass_g": mass_g,
        "deflection_mm": deflection_mm,
        "term_mass": term_mass,
        "term_deflection": term_deflection,
        "feasible": deflection_mm <= DEFLECTION_LIMIT,
    }
