# TODO: fix solver

import numpy as np
from core.airfoil import Airfoil

def solve_panel_method(airfoil: Airfoil, alpha_deg: float, v_inf: float = 1.0):
    """
    Parameters
    ----------
    airfoil: Closed airfoil geometry (Points start top-right, CCW -> Upper side first).
    alpha_deg: Angle of attack in degrees.
    v_inf: Freestream velocity magnitude.
    """

    alpha = np.deg2rad(alpha_deg)
    x_b = np.asarray(airfoil.x)
    y_b = np.asarray(airfoil.y)
    n = len(x_b) - 1

    # Geometry Arrays
    x_c = np.zeros(n)
    y_c = np.zeros(n)
    s = np.zeros(n)
    tx = np.zeros(n)
    ty = np.zeros(n)
    nx = np.zeros(n)
    ny = np.zeros(n)
    theta = np.zeros(n)

    for j in range(n):
        dx = x_b[j + 1] - x_b[j]
        dy = y_b[j + 1] - y_b[j]

        s[j] = np.hypot(dx, dy)
        theta[j] = np.arctan2(dy, dx)

        # Tangenten (Zeigen von rechts nach links auf der Oberseite)
        tx[j] = dx / s[j]
        ty[j] = dy / s[j]

        # DEIN RECHTER URSPRUNGS-CODE: Zeigt bei CCW sauber nach AUSSEN
        nx[j] = -ty[j]
        ny[j] = tx[j]

        # Kontrollpunkte
        x_c[j] = 0.5 * (x_b[j] + x_b[j + 1])
        y_c[j] = 0.5 * (y_b[j] + y_b[j + 1])

    # Einflussmatrix aufbauen
    A = np.zeros((n, n))
    b = np.zeros(n)

    Vx = v_inf * np.cos(alpha)
    Vy = v_inf * np.sin(alpha)

    for i in range(n):
        # Normalenkomponente der ungestörten Strömung
        b[i] = -(Vx * nx[i] + Vy * ny[i])

        for j in range(n):
            if i == j:
                A[i, j] = 0.5
                continue

            # Transformation in lokale Koordinaten von Panel j
            dx = x_c[i] - x_b[j]
            dy = y_c[i] - y_b[j]

            x_local = dx * np.cos(theta[j]) + dy * np.sin(theta[j])
            y_local = -dx * np.sin(theta[j]) + dy * np.cos(theta[j])

            r1 = np.hypot(x_local, y_local)
            r2 = np.hypot(x_local - s[j], y_local)

            if r1 < 1e-10 or r2 < 1e-10:
                A[i, j] = 0.0
                continue

            beta = np.arctan2(y_local, x_local - s[j]) - np.arctan2(y_local, x_local)

            # Lokale induzierte Geschwindigkeiten
            u_local = -beta / (2.0 * np.pi)
            v_local = 1.0 / (4.0 * np.pi) * np.log((r2 * r2) / (r1 * r1))

            # Rückrotation ins globale System
            u = u_local * np.cos(theta[j]) - v_local * np.sin(theta[j])
            v = u_local * np.sin(theta[j]) + v_local * np.cos(theta[j])

            # Normalen-Einfluss
            A[i, j] = u * nx[i] + v * ny[i]

    # Matrix für Kutta-Bedingung vorbereiten
    A_kutta = np.zeros((n, n))
    b_kutta = np.zeros(n)

    A_kutta[:-1, :] = A[:-1, :]
    b_kutta[:-1] = b[:-1]

    # FIX FÜR CCW-LAUFRICHTUNG AN DER HINTERKANTE:
    # Da das erste und letzte Panel in die gleiche Richtung um die Hinterkante fließen,
    # müssen sich die Wirbelstärken abziehen, um den glatten Strömungsabgang zu erzwingen.
    A_kutta[-1, 0] = 1.0
    A_kutta[-1, -1] = -1.0  # Von +1.0 auf -1.0 geändert!
    b_kutta[-1] = 0.0

    gamma = np.linalg.solve(A_kutta, b_kutta)

    # ECHTE OBERFLÄCHENGESCHWINDIGKEIT BERECHNEN:
    # V_inf gleitet tangential am Profil entlang + der induzierte Wirbel-Anteil
    v_t = np.zeros(n)
    for i in range(n):
        v_inf_tangential = Vx * tx[i] + Vy * ty[i]
        v_t[i] = v_inf_tangential + gamma[i]

    cp = 1.0 - (v_t / v_inf) ** 2

    # Da der Pfad im CCW-Sinn läuft, misst die Zirkulation mathematisch korrekt.
    # Kein Minuszeichen beim Integral nötig.
    circulation = np.sum(gamma * s)

    rho = 1.0
    lift_per_span = rho * v_inf * circulation
    chord = np.max(x_b) - np.min(x_b)
    cl = lift_per_span / (0.5 * rho * v_inf**2 * chord)

    return {
        "cl": cl,
        "cp": cp,
        "gamma": gamma,
        "x_c": x_c,
        "y_c": y_c,
    }
