import numpy as np
from core.airfoil import Airfoil

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


def _compute_influence_integrals(
    i: int,
    j: int,
    x: np.ndarray,
    y: np.ndarray,
    nodes: np.ndarray,
    phi: np.ndarray,
    s: np.ndarray
):
    """
    Compute the geometric influence integrals I and K between panel i and panel j.
    This relates to integral J_i,j for normal velocity (Equation 4.79, Page 363).
    """
    if i == j:
        return 0.0, 0.0

    A = -(x[i] - nodes[j][0]) * np.cos(phi[j]) - (y[i] - nodes[j][1]) * np.sin(phi[j])
    B = (x[i] - nodes[j][0])**2 + (y[i] - nodes[j][1])**2
    C_I = np.sin(phi[i] - phi[j])
    C_K = -np.cos(phi[i] - phi[j])
    D_I = -(x[i] - nodes[j][0]) * np.sin(phi[i]) + (y[i] - nodes[j][1]) * np.cos(phi[i])
    D_K = (x[i] - nodes[j][0]) * np.cos(phi[i]) + (y[i] - nodes[j][1]) * np.sin(phi[i])

    if (B - A**2) <= 0:
        return 0.0, 0.0

    E = (B - A**2)**0.5
    log_term = np.log(((s[j])**2 + 2 * A * s[j] + B) / B)
    arctan_term = np.arctan2((s[j] + A), E) - np.arctan2(A, E)

    I_val = (C_I / 2) * log_term + ((D_I - A * C_I) / E) * arctan_term
    K_val = (C_K / 2) * log_term + ((D_K - A * C_K) / E) * arctan_term
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
    """
    Build the linear system A * gamma = b.
    Includes the Kutta condition and drops the last control point equation (Page 364).

    Returns
    -------
    tuple
        (Matrix A, Vector b, Matrix J, Matrix L)
    """
    I_mat = np.zeros((n, n))
    K_mat = np.zeros((n, n))
    L_mat = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            I_val, K_val = _compute_influence_integrals(i, j, x, y, nodes, phi, s)
            I_mat[i, j] = I_val
            K_mat[i, j] = K_val
            L_mat[i, j] = -I_val

    J_mat = K_mat # Induced coupling matrix for tangential velocity

    # Initialize the (n+1) x (n+1) system matrix A
    A_sys = np.zeros((n + 1, n + 1))

    # Normal velocity induction for panels 0 to n-1
    for i in range(n):
        for j in range(n):
            if i == j:
                A_sys[i, j] = np.pi
            else:
                A_sys[i, j] = I_mat[i, j]

    # Column for the constant circulation coupling (Kutta condition coupling)
    for i in range(n):
        K_sum = sum(K_mat[i, j] for j in range(n) if i != j)
        A_sys[i, n] = -K_sum

    # Last row of A: Numerical Kutta condition gamma_i = -gamma_{i-1} (Equation 4.81)
    for j in range(n):
        if j == 0:
            A_sys[n, j] = J_mat[n - 1, 0]
        elif j == (n - 1):
            A_sys[n, j] = J_mat[0, n - 1]
        else:
            A_sys[n, j] = J_mat[0, j] + J_mat[n - 1, j]

    L_sum = sum(L_mat[0, j] + L_mat[n - 1, j] for j in range(1, n - 1))
    L_sum += L_mat[n - 1, 0] + L_mat[0, n - 1]
    A_sys[n, n] = -L_sum + 2 * np.pi

    # Build right-hand side vector b (Equation 4.80)
    b_sys = np.zeros(n + 1)
    for i in range(n):
        b_sys[i] = -v_inf * 2 * np.pi * np.cos(beta[i])
    b_sys[n] = -v_inf * 2 * np.pi * (np.sin(beta[0]) + np.sin(beta[n - 1]))

    return A_sys, b_sys, J_mat, L_mat


def solve_panel_method(airfoil: Airfoil, alpha_deg: float, v_inf: float = 1.0):
    """
    Solve the 2D vortex panel method for an arbitrary airfoil.

    Parameters
    ----------
    airfoil : Airfoil
        The airfoil geometry object (Selig format: counter-clockwise)
    alpha_deg : float
        Angle of attack in degrees
    v_inf : float
        Freestream velocity

    Returns
    -------
    dict
        {"cl": cl, "cp": cp, "gamma": gamma, "x_c": x_c, "y_c": y_c}
    """

    # The textbook assumes clockwise orientation.
    # We invert the Selig points for the calculation.
    nodes = airfoil.coords[::-1]
    n = len(nodes) - 1
    alpha_rad = alpha_deg * np.pi / 180.0

    # Compute panel geometry properties
    x, y, phi, beta, s = _calculate_panel_geometry(nodes, alpha_rad)

    # Assemble and solve the linear system
    A_sys, b_sys, J_mat, L_mat = _build_linear_system(n, x, y, nodes, phi, beta, s, v_inf)
    sol = np.linalg.solve(A_sys, b_sys)

    # Global circulation strength is the last element of the solution vector
    gamma_global = sol[n]

    # Compute tangential velocities V_t and pressure coefficients C_p (Page 364-365)
    v_t_distribution = []
    Cp = []
    for i in range(n):
        # Calculate local tangential velocity from the linear system components
        term1 = v_inf * np.sin(beta[i])
        term2 = sum(sol[j] * J_mat[i, j] / (2 * np.pi) for j in range(n))
        term3 = gamma_global / 2
        term4 = sum(-(gamma_global * L_mat[i, j] / (2 * np.pi)) for j in range(n))

        v_t_local = term1 + term2 + term3 + term4
        v_t_distribution.append(v_t_local)

        # Calculate C_p using Bernoulli's equation
        Cp.append(1.0 - (v_t_local**2 / v_inf**2))

    # Compute total circulation and section lift coefficient c_l
    # We compute Gamma using Equation 4.82
    Gamma = 0.0
    for j in range(n):
        Gamma += v_t_distribution[j] * s[j]

    # Calculate lift per unit span L_prime (Equation 4.83)
    # L_prime = rho_inf * V_inf * Gamma
    # Converting to dimensionless lift coefficient c_l (c_l = L_prime / (0.5 * rho * V_inf^2 * chord))
    # For a normalized chord (c=1.0), this simplifies to:
    cl = (2.0 * Gamma) / v_inf

    return {
        "cl": cl,
        "cp": np.array(Cp[::-1]),
        "gamma": gamma_global,
        "x_c": np.array(x[::-1]),
        "y_c": np.array(y[::-1])
    }

