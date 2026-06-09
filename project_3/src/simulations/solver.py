import numpy as np
from core.airfoil import Airfoil

def solve_panel_method(airfoil: Airfoil, alpha_deg: float, v_inf: float = 1.0):
    # 1. Orientierung anpassen: Der Originalcode erwartet die Punkte IM Uhrzeigersinn.
    # Da Selig GEGEN den Uhrzeigersinn läuft, drehen wir die Reihenfolge einfach um.
    nodes = airfoil.coords[::-1]
    
    # Standardwerte, die im Originalcode als Argumente übergeben wurden
    velocity = v_inf
    density = 1.225  # Standard Luftdichte, falls für Dimensionierung benötigt (hier gekürzt)
    chord = 1.0      # Standard Sehnenlänge
    
    # Number of panels
    n = len(nodes) - 1

    # Body points coordinates
    xb = [nodes[i][0] for i in range(n)]
    yb = [nodes[i][1] for i in range(n)]

    # Control points coordinates (Mittelpunkte)
    # Wichtig: Weil wir die Nodes umgedreht haben, müssen wir das Rückgabe-X/Y 
    # am Ende wieder in die originale Selig-Reihenfolge bringen.
    x = [(nodes[i][0] + nodes[i+1][0])/2 for i in range(n)]
    y = [(nodes[i][1] + nodes[i+1][1])/2 for i in range(n)]

    # Free-stream velocity and Angle of Attack
    V_inf = velocity
    a = alpha_deg * np.pi / 180

    # Angles of panels
    def phi_f(i):
        dx = nodes[i+1][0] - nodes[i][0]
        dy = nodes[i+1][1] - nodes[i][1]
        phi = np.arctan2(dy, dx)
        return phi + 2 * np.pi if phi < 0 else phi

    phi = [phi_f(j) for j in range(n)]

    # Angles between free-stream velocity and outward normal
    def beta_f(i):
        b = phi[i] + (np.pi / 2) - a
        return b - (2 * np.pi) if b > 2 * np.pi else b

    beta = [beta_f(j) for j in range(n)]

    # Panel lengths
    def s_f(i):
        dx = nodes[i+1][0] - nodes[i][0]
        dy = nodes[i+1][1] - nodes[i][1]
        return (dx**2 + dy**2)**0.5

    s = [s_f(j) for j in range(n)]

    # I, K matrices
    def I_K(i, j):
        if i == j:
            return 0.0, 0.0
        else:
            A = -(x[i]-nodes[j][0]) * np.cos(phi[j]) - (y[i]-nodes[j][1]) * np.sin(phi[j])
            B = (x[i]-nodes[j][0])**2 + (y[i]-nodes[j][1])**2
            C_I = np.sin(phi[i]-phi[j])
            C_K = -np.cos(phi[i]-phi[j])
            D_I = -(x[i]-nodes[j][0]) * np.sin(phi[i]) + (y[i]-nodes[j][1]) * np.cos(phi[i])
            D_K = (x[i]-nodes[j][0]) * np.cos(phi[i]) + (y[i]-nodes[j][1]) * np.sin(phi[i])
            if (B - A**2) <= 0:
                return 0.0, 0.0
            else:
                E = (B - A**2)**0.5
                log_term = np.log(((s[j])**2 + 2*A*s[j] + B)/B)
                arctan_term = np.arctan2((s[j]+A), E) - np.arctan2(A, E)
                return (C_I/2) * log_term + ((D_I-A*C_I)/E) * arctan_term, (C_K/2) * log_term + ((D_K-A*C_K)/E) * arctan_term

    I = [[] for _ in range(n)]
    K = [[] for _ in range(n)]
    L = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            I_value, K_value = I_K(i, j)
            I[i].append(I_value)
            L[i].append(-I_value)
            K[i].append(K_value)

    J = K

    # Generating influence matrix
    A_mat = [[] for _ in range(n+1)]

    for i in range(n):
        for j in range(n):
            if i == j:
                A_mat[i].append(np.pi)
            else:
                A_mat[i].append(I[i][j])

    for i in range(n):
        K_sum = 0
        for j in range(n):
            if i != j:
                K_sum += K[i][j]
        A_mat[i].append(-K_sum)

    for j in range(n):
        if j == 0:
            A_mat[n].append(J[n-1][0])
        elif j == (n-1):
            A_mat[n].append(J[0][n-1])
        else:
            A_mat[n].append(J[0][j] + J[n-1][j])

    L_sum = 0
    for j in range(1, n-1):
        L_sum += L[0][j] + L[n-1][j]
    L_sum += L[n-1][0] + L[0][n-1]

    A_mat[n].append(-(L_sum) + 2*np.pi)

    # RHS terms matrix
    def b_i(i):
        return -V_inf * 2 * np.pi * np.cos(beta[i])

    b = [b_i(i) for i in range(n)]
    b.append(-V_inf * 2 * np.pi * (np.sin(beta[0]) + np.sin(beta[n-1])))

    # Solving Linear system
    invA = np.linalg.inv(A_mat)
    sol = np.dot(invA, b)
    
    # Die Zirkulation (Gamma) ist der letzte Eintrag im Lösungsvektor
    gamma = sol[n]

    # Tangential velocity on panel "i" function
    def V_t(i):
        term1 = V_inf * np.sin(beta[i])
        term2 = sum(sol[j] * J[i][j] / (2 * np.pi) for j in range(n))
        term3 = gamma / 2
        term4 = sum(-(gamma * L[i][j] / (2 * np.pi)) for j in range(n))
        return term1 + term2 + term3 + term4

    # Calculate tangential velocity and Cp on each panel
    Vt = []
    Cp = []
    for i in range(n):
        v = V_t(i)
        Vt.append(v)
        Cp.append(1 - (v**2 / V_inf**2))

    # Normal and Axial Force Coefficients
    CN = [-Cp[j] * s[j] * np.sin(beta[j]) for j in range(n)]
    CA = [-Cp[j] * s[j] * np.cos(beta[j]) for j in range(n)]

    # Lift Coefficient
    cl = 0.0
    for j in range(n):
        cl += CN[j] * np.cos(a) - CA[j] * np.sin(a)

    #--------------------------------------------------------------
    # Vorbereitung der Rückgabe (Rückdrehung in Selig-Reihenfolge)
    #--------------------------------------------------------------
    # Da wir die Panels intern umgedreht haben (Index 0 war das letzte Selig-Panel),
    # müssen wir die Listen für Cp, x und y umdrehen, damit sie wieder perfekt 
    # zu der Geometrie-Reihenfolge der übergebenen Airfoil-Klasse passen.
    cp_ordered = np.array(Cp[::-1])
    xm_ordered = np.array(x[::-1])
    ym_ordered = np.array(y[::-1])

    return {
        "cl": cl,
        "cp": cp_ordered,
        "gamma": gamma,
        "x_c": xm_ordered,
        "y_c": ym_ordered
    }
