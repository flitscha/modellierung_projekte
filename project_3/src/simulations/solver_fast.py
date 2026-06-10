import numpy as np
from core.airfoil import Airfoil
from numba import njit


def _calculate_panel_geometry(nodes: np.ndarray, alpha_rad: float):
    """
    Calculate geometric properties of each panel from the nodes.

    Parameters
    ----------
    nodes : np.ndarray
        Airfoil boundary points in positive orientation.
    alpha_rad : float
        Angle of attack in radians.

    Returns
    -------
    tuple
        (Control points x, Control points y, panel angles phi, normal angles beta, lengths s)
    """
    n = len(nodes) - 1

    # Control points are the midpoints of the panels
    x = [(nodes[i][0] + nodes[i+1][0]) / 2 for i in range(n)]
    y = [(nodes[i][1] + nodes[i+1][1]) / 2 for i in range(n)]

    # Panel angle phi relative to the x-axis
    phi = []
    for i in range(n):
        dx = nodes[i+1][0] - nodes[i][0]
        dy = nodes[i+1][1] - nodes[i][1]
        p = np.arctan2(dy, dx)
        phi.append(p + 2 * np.pi if p < 0 else p)

    # Angle beta between freestream and outward normal
    beta = []
    for i in range(n):
        b = phi[i] + (np.pi / 2) - alpha_rad
        beta.append(b - (2 * np.pi) if b > 2 * np.pi else b)

    # Panel lengths s_j
    s = [((nodes[i+1][0] - nodes[i][0])**2 + (nodes[i+1][1] - nodes[i][1])**2)**0.5 for i in range(n)]

    return np.array(x), np.array(y), np.array(phi), np.array(beta), np.array(s)


@njit(fastmath=True)
def _compute_influence_integrals_numba(
    i: int,
    j: int,
    x: np.ndarray,
    y: np.ndarray,
    nodes: np.ndarray,
    phi: np.ndarray,
    s: np.ndarray
):
    """
    Numba-optimized version of influence integrals.
    """
    if i == j:
        return 0.0, 0.0

    dx = x[i] - nodes[j, 0]
    dy = y[i] - nodes[j, 1]

    cos_pj = np.cos(phi[j])
    sin_pj = np.sin(phi[j])

    A = -dx * cos_pj - dy * sin_pj
    B = dx * dx + dy * dy

    C_I = np.sin(phi[i] - phi[j])
    C_K = -np.cos(phi[i] - phi[j])

    sin_pi = np.sin(phi[i])
    cos_pi = np.cos(phi[i])

    D_I = -dx * sin_pi + dy * cos_pi
    D_K = dx * cos_pi + dy * sin_pi

    if (B - A * A) <= 0.0:
        return 0.0, 0.0

    E = np.sqrt(B - A * A)

    log_term = np.log(((s[j] * s[j]) + 2.0 * A * s[j] + B) / B)

    arctan_term = np.arctan2((s[j] + A), E) - np.arctan2(A, E)

    I_val = (C_I * 0.5) * log_term + ((D_I - A * C_I) / E) * arctan_term
    K_val = (C_K * 0.5) * log_term + ((D_K - A * C_K) / E) * arctan_term

    return I_val, K_val


def _build_linear_system(
    n: int,
    x: np.ndarray,
    y: np.ndarray,
    nodes: np.ndarray,
    phi: np.ndarray,
    beta: np.ndarray,
    s: np.ndarray,
    v_inf: float
):
    # Allocate matrices
    I_mat = np.zeros((n, n))
    K_mat = np.zeros((n, n))

    # Influence integral
    for i in range(n):
        for j in range(n):
            I_val, K_val = _compute_influence_integrals_numba(
                i, j, x, y, nodes, phi, s
            )
            I_mat[i, j] = I_val
            K_mat[i, j] = K_val

    L_mat = -I_mat
    J_mat = K_mat

    # System matrix A
    A_sys = np.zeros((n + 1, n + 1))

    # Fill upper-left block
    A_sys[:n, :n] = I_mat
    np.fill_diagonal(A_sys[:n, :n], np.pi)

    # Rightmost column (Kutta coupling sum)
    K_sum = np.sum(K_mat, axis=1) - np.diag(K_mat)
    A_sys[:n, n] = -K_sum

    # Kutta row (last row)
    A_sys[n, :n] = J_mat[0] + J_mat[n - 1]
    A_sys[n, 0] = J_mat[n - 1, 0]
    A_sys[n, n - 1] = J_mat[0, n - 1]

    # Last element
    L_sum = np.sum(L_mat[0, 1:n-1] + L_mat[n - 1, 1:n-1])
    A_sys[n, n] = -L_sum + 2 * np.pi

    # RHS vector
    b_sys = np.zeros(n + 1)

    b_sys[:n] = -v_inf * 2 * np.pi * np.cos(beta)
    b_sys[n] = -v_inf * 2 * np.pi * (np.sin(beta[0]) + np.sin(beta[-1]))

    return A_sys, b_sys, J_mat, L_mat


def solve_panel_method(airfoil: Airfoil, alpha_deg: float, v_inf: float = 1.0):

    nodes = airfoil.coords[::-1]
    n = len(nodes) - 1
    alpha_rad = alpha_deg * np.pi / 180.0

    x, y, phi, beta, s = _calculate_panel_geometry(nodes, alpha_rad)

    A_sys, b_sys, J_mat, L_mat = _build_linear_system(n, x, y, nodes, phi, beta, s, v_inf)

    sol = np.linalg.solve(A_sys, b_sys)
    gamma_global = sol[n]
    v_t_distribution = []
    Cp = []

    for i in range(n):
        term1 = v_inf * np.sin(beta[i])
        term2 = sum(sol[j] * J_mat[i, j] / (2 * np.pi) for j in range(n))
        term3 = gamma_global / 2
        term4 = sum(-(gamma_global * L_mat[i, j] / (2 * np.pi)) for j in range(n))

        v_t_local = term1 + term2 + term3 + term4
        v_t_distribution.append(v_t_local)
        Cp.append(1.0 - (v_t_local**2 / v_inf**2))

    Gamma = 0.0
    for j in range(n):
        Gamma += v_t_distribution[j] * s[j]

    cl = (2.0 * Gamma) / v_inf

    return {
        "cl": cl,
        "cp": np.array(Cp[::-1]),
        "gamma": gamma_global,
        "x_c": np.array(x[::-1]),
        "y_c": np.array(y[::-1])
    }

