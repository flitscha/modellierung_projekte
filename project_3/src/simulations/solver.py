"""
Vortex Panel Numerical Method Solver.
Based on "Fundamentals of Aerodynamics", 5th Edition (pp. 361-366).
"""
import numpy as np
from core.airfoil import Airfoil


def solve_panel_method(airfoil: Airfoil, alpha_deg: float, v_inf: float = 1.0) -> dict:
    """
    Solves the flow over an arbitrary airfoil using a first-order vortex panel method.

    References to PDF: "Fundamentals of Aerodynamics 5th edition-386-396.pdf"
    - Geometry & Control Points: Page 2 (p. 362)
    - Boundary Conditions & J_ij Integral: Page 3 (p. 363)
    - Kutta Condition: Page 4 (p. 364)
    - Velocity, Lift & Circulation: Page 5 (p. 365)
    """
    alpha = np.radians(alpha_deg)

    # 1. GEOMETRY SETUP (Page 2, p. 362)
    # Boundary points defining the panels
    x_b = airfoil.x
    y_b = airfoil.y
    n = len(x_b) - 1  # Number of panels

    # Initialize panel properties
    # Control points (x_i, y_i) are located at the midpoint of each panel (Page 2, p. 362, source 335)
    x_c = np.zeros(n)
    y_c = np.zeros(n)
    s_j = np.zeros(n)      # Length of each panel s_j (Page 5, p. 365, source 424)
    theta_j = np.zeros(n)  # Orientation angle of the panel relative to x-axis

    for i in range(n):
        dx = x_b[i+1] - x_b[i]
        dy = y_b[i+1] - y_b[i]
        s_j[i] = np.sqrt(dx**2 + dy**2)
        x_c[i] = x_b[i] + 0.5 * dx
        y_c[i] = y_b[i] + 0.5 * dy
        theta_j[i] = np.arctan2(dy, dx)

    # Outward normal and tangent angles for each panel i
    delta_i = theta_j + np.pi / 2.0
    beta_i = delta_i + alpha  # Angle between V_inf and panel normal (Page 3, p. 363, source 358)

    # 2. INFLUENCE COEFFICIENT MATRIX A (Page 3, p. 363)
    # Setting up the system of linear algebraic equations: A * gamma = b
    # Equation (4.80): V_inf * cos(beta_i) - Sum( (gamma_j / 2*pi) * J_ij ) = 0 (source 377)
    A = np.zeros((n + 1, n))
    b = np.zeros(n + 1)

    for i in range(n):
        # Freestream normal component vector b (Page 3, p. 363, Equation 3.148)
        b[i] = -v_inf * np.cos(beta_i[i])

        for j in range(n):
            if i == j:
                # Self-influence of a panel on its own control point
                A[i, j] = 0.5
            else:
                # Numerical evaluation of J_ij integral (Page 3, p. 363, Equation 4.77 & 4.79)
                # Compute distance and angle from panel j to control point i
                dx_ij = x_c[i] - x_c[j]
                dy_ij = y_c[i] - y_c[j]

                # Transform coordinates to local panel j system
                x_local = dx_ij * np.cos(theta_j[j]) + dy_ij * np.sin(theta_j[j])
                y_local = -dx_ij * np.sin(theta_j[j]) + dy_ij * np.cos(theta_j[j])

                # Compute angles to panel edges
                theta_edge1 = np.arctan2(y_local, x_local + s_j[j]/2.0)
                theta_edge2 = np.arctan2(y_local, x_local - s_j[j]/2.0)

                # J_ij represents the normal velocity induced at control point i by panel j
                # Page 3, p. 363, Equation (4.79) (source 371)
                J_ij = -(1.0 / (2.0 * np.pi)) * (theta_edge2 - theta_edge1)
                A[i, j] = J_ij

    # 3. KUTTA CONDITION (Page 4, p. 364)
    # According to Equation (4.81): gamma_i = -gamma_i-1 at the trailing edge (source 403)
    # This creates an overdetermined system (n+1 equations for n unknowns) (source 407)
    # We replace the last row of A with the numerical Kutta condition approximation (source 408, 410)
    A[n, 0] = 1.0
    A[n, n-1] = 1.0
    b[n] = 0.0

    # Solve for the n-1 independent control points combined with Kutta condition
    # To handle the overdetermined system cleanly, we drop the last control point row
    A_determined = np.vstack([A[:-2, :], A[n, :]]) 
    b_determined = np.append(b[:-2], b[n])

    # Solve the system of linear equations
    gamma = np.linalg.solve(A_determined, b_determined)

    # 4. POST-PROCESSING: LIFT & CIRCULATION (Page 5, p. 365)
    # Total circulation Gamma = Sum( gamma_j * s_j ) -> Equation (4.82) (source 430)
    total_gamma = -np.sum(gamma * s_j) # negative value, since we have counter-clockwise order

    # Lift per unit span L_prime = rho * V_inf * Gamma -> Equation (4.83) (source 431)
    # Assuming normalized density rho = 1.0
    rho = 1.0
    lift_prime = rho * v_inf * total_gamma

    # Section lift coefficient c_l = L_prime / (0.5 * rho * V_inf^2 * chord)
    # Our generated airfoil chord length is exactly 1.0
    chord = 1.0
    cl = lift_prime / (0.5 * rho * (v_inf**2) * chord)

    # Local velocity tangential to the surface V_local = gamma_j (Page 5, p. 365, source 422)
    v_local = -gamma # negative, since we have counter-clockwise order

    # Local pressure coefficient distribution from Bernoulli's equation (Page 5, p. 365, source 423)
    cp = 1.0 - (v_local / v_inf)**2

    return {
        "cl": cl,
        "cp": cp,
        "gamma": gamma,
        "x_c": x_c
    }

