"""
Airfoil Design, Analysis & Optimization
========================================
Parametrisierung: NACA 4-stellig + CST (Class-Shape Transformation)
Analyse:          Thin Airfoil Theory + XFOIL-Interface (optional)
Optimierung:      scipy.optimize (differential_evolution)

Anforderungen:
    pip install numpy matplotlib scipy

Optional (für XFOIL-Analyse):
    XFOIL muss installiert sein: https://web.mit.edu/drela/Public/web/xfoil/
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution, minimize
from scipy.interpolate import interp1d
import subprocess
import os
import tempfile





# ─────────────────────────────────────────────────────────────
# 1. AIRFOIL GEOMETRIE
# ─────────────────────────────────────────────────────────────

def naca4(m_pct, p_pct, t_pct, n=200):
    """
    NACA 4-stelliges Profil.

    Parameter:
        m_pct : maximale Wölbung in % der Profiltiefe (z.B. 4 → NACA 4xxx)
        p_pct : Position der max. Wölbung in 10% (z.B. 4 → NACA x4xx)
        t_pct : maximale Dicke in % (z.B. 12 → NACA xx12)
        n     : Anzahl Punkte pro Seite
    """
    m = m_pct / 100.0
    p = p_pct / 10.0
    t = t_pct / 100.0

    # Kosinus-Verteilung für bessere Auflösung an Vorder- und Hinterkante
    beta = np.linspace(0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))

    # Dickenfunktion (NACA-Standard)
    yt = 5 * t * (0.2969 * np.sqrt(x)
                  - 0.1260 * x
                  - 0.3516 * x**2
                  + 0.2843 * x**3
                  - 0.1015 * x**4)

    # Wölbungslinie
    yc = np.where(
        x <= p,
        (m / p**2) * (2 * p * x - x**2),
        (m / (1 - p)**2) * ((1 - 2 * p) + 2 * p * x - x**2)
    )

    # Neigungswinkel der Wölbungslinie
    if p == 0:
        dyc_dx = np.zeros_like(x)
    else:
        dyc_dx = np.where(
            x <= p,
            (2 * m / p**2) * (p - x),
            (2 * m / (1 - p)**2) * (p - x)
        )
    theta = np.arctan(dyc_dx)

    # Obere / untere Kontur
    xu = x  - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x  + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    return xu, yu, xl, yl


def cst_airfoil(Au, Al, n=200, t_te=0.002):
    """
    CST-Parametrisierung (Class-Shape Transformation, Kulfan 2008).

    Au : Liste von Koeffizienten für die Oberseite
    Al : Liste von Koeffizienten für die Unterseite
    t_te: Hinterkanten-Dicke (halbe Dicke, für 3D-Druck wichtig)
    """
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))

    def shape(x, A):
        N = len(A) - 1
        S = np.zeros_like(x)
        for i, a in enumerate(A):
            binom = np.math.comb(N, i)
            S += a * binom * (x**i) * ((1 - x)**(N - i))
        return S

    C = x**0.5 * (1 - x)  # Klassenfunction C(1/2, 1)

    yu =  C * shape(x, Au) + x * t_te
    yl = -C * shape(x, Al) - x * t_te  # Vorzeichen: Unterseite negativ

    return x, yu, x, yl


def to_selig(xu, yu, xl, yl, filename="airfoil.dat", name="AIRFOIL"):
    """
    Exportiert das Profil im Selig-Format.
    Reihenfolge: Obere Hinterkante → Vorderkante → Untere Hinterkante (CCW)
    """
    # Obere Seite: von TE (x=1) zur LE (x=0)
    upper = np.column_stack([xu[::-1], yu[::-1]])
    # Untere Seite: von LE (x=0) zu TE (x=1), ersten Punkt überspringen
    lower = np.column_stack([xl[1:], yl[1:]])
    coords = np.vstack([upper, lower])

    with open(filename, "w") as f:
        f.write(f"{name}\n")
        for x, y in coords:
            f.write(f"  {x:.6f}  {y:.6f}\n")
    print(f"Gespeichert: {filename}")
    return coords


# ─────────────────────────────────────────────────────────────
# 2. THIN AIRFOIL THEORY
# ─────────────────────────────────────────────────────────────

def thin_airfoil_cl(alpha_deg, m_pct, p_pct):
    """
    Auftriebsbeiwert nach Dünner-Profiletheorie.
    Cl = 2π(α + αL0)  mit αL0 = -2 * (m/p - m/(1-p)) * ... (vereinfacht)

    Für NACA 4-stellig:
        αL0 ≈ -2 * m * (1 - 2p) / ... (numerische Integration)
    """
    alpha = np.deg2rad(alpha_deg)
    m = m_pct / 100.0
    p = p_pct / 10.0

    # Numerische Integration für αL0
    theta = np.linspace(0.0001, np.pi - 0.0001, 1000)
    x = 0.5 * (1 - np.cos(theta))

    if p > 0:
        dyc_dx = np.where(
            x <= p,
            (2 * m / p**2) * (p - x),
            (2 * m / (1 - p)**2) * (p - x)
        )
    else:
        dyc_dx = np.zeros_like(x)

    alpha_L0 = -(1 / np.pi) * np.trapz(dyc_dx * (1 - np.cos(theta)) / np.sin(theta), theta)

    Cl = 2 * np.pi * (alpha - alpha_L0)
    return Cl, np.rad2deg(alpha_L0)


def cl_alpha_curve(m_pct, p_pct, alphas=None):
    """Cl über Anstellwinkel 0–15°"""
    if alphas is None:
        alphas = np.linspace(-5, 15, 50)
    cls = [thin_airfoil_cl(a, m_pct, p_pct)[0] for a in alphas]
    return alphas, np.array(cls)


# ─────────────────────────────────────────────────────────────
# 3. XFOIL INTERFACE (optional)
# ─────────────────────────────────────────────────────────────

def run_xfoil(xu, yu, xl, yl, alphas, Re=500000, n_crit=9, max_iter=100):
    """
    Startet XFOIL und gibt Cl, Cd, Cm zurück.
    Benötigt XFOIL im PATH. Gibt None zurück wenn nicht verfügbar.
    """
    try:
        subprocess.run(["xfoil"], input="", capture_output=True, timeout=2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("XFOIL nicht gefunden – überspringe XFOIL-Analyse.")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        coord_file = os.path.join(tmpdir, "airfoil.dat")
        polar_file = os.path.join(tmpdir, "polar.dat")

        to_selig(xu, yu, xl, yl, coord_file, "AIRFOIL")

        cmds = [
            f"LOAD {coord_file}",
            "PANE",
            "OPER",
            f"VISC {Re}",
            f"VPAR\nN {n_crit}\n\n",
            f"ITER {max_iter}",
            "PACC",
            polar_file,
            "",
            f"ASEQ {alphas[0]} {alphas[-1]} {alphas[1]-alphas[0]}",
            "PACC",
            "",
            "QUIT"
        ]
        input_str = "\n".join(cmds) + "\n"

        subprocess.run(["xfoil"], input=input_str, capture_output=True,
                       text=True, timeout=60)

        if not os.path.exists(polar_file):
            return None

        data = np.loadtxt(polar_file, skiprows=12)
        if data.ndim == 1:
            data = data[np.newaxis, :]

        return {
            "alpha": data[:, 0],
            "Cl":    data[:, 1],
            "Cd":    data[:, 2],
            "Cm":    data[:, 4],
        }


# ─────────────────────────────────────────────────────────────
# 4. OPTIMIERUNG
# ─────────────────────────────────────────────────────────────

def objective_naca4(params):
    """
    Zielfunktion für NACA 4-stellig.
    Maximiere: mittleren Cl über 0–10°
    Minimiere: Varianz des Cl über 0–10° (gleichmäßiger Auftrieb)
    Strafe:    zu dünne Profile (< 8%), zu dicke (> 18%)
    """
    m_pct, p_pct, t_pct = params
    alphas = np.linspace(0, 10, 11)
    cls = np.array([thin_airfoil_cl(a, m_pct, p_pct)[0] for a in alphas])

    mean_cl = np.mean(cls)
    var_cl  = np.var(cls)

    # Strafe für ungültige Geometrie
    penalty = 0
    if t_pct < 8:
        penalty += 10 * (8 - t_pct)**2    # zu dünn → Druckprobleme
    if t_pct > 20:
        penalty += 10 * (t_pct - 20)**2   # zu dick → zu viel Widerstand
    if p_pct < 2:
        penalty += 5 * (2 - p_pct)**2     # Max-Wölbung zu weit vorne

    # Wir minimieren → negatives mean_cl + Varianzterm
    return -mean_cl + 0.5 * var_cl + penalty


def optimize_naca4():
    """Globale Optimierung mit Differential Evolution"""
    print("\n=== Optimierung läuft (NACA 4-digit) ===")
    bounds = [
        (1, 9),    # m: 1–9% Wölbung
        (2, 7),    # p: Position 20–70%
        (8, 18),   # t: Dicke 8–18%
    ]
    result = differential_evolution(
        objective_naca4,
        bounds,
        seed=42,
        maxiter=500,
        tol=1e-6,
        popsize=20,
        mutation=(0.5, 1.5),
        recombination=0.9,
        disp=True
    )
    m, p, t = result.x
    print(f"\nOptimales Profil: NACA {int(round(m))}{int(round(p))}{int(round(t)):02d}")
    print(f"  Wölbung m = {m:.2f}%")
    print(f"  Position p = {p:.2f} (×10%)")
    print(f"  Dicke    t = {t:.2f}%")
    return result.x


# ─────────────────────────────────────────────────────────────
# 5. VISUALISIERUNG
# ─────────────────────────────────────────────────────────────

def plot_airfoil(xu, yu, xl, yl, title="Airfoil"):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xu, yu, "b-", lw=2, label="Oberseite")
    ax.plot(xl, yl, "r-", lw=2, label="Unterseite")
    ax.fill(
        np.concatenate([xu[::-1], xl]),
        np.concatenate([yu[::-1], yl]),
        alpha=0.15, color="steelblue"
    )
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_xlabel("x/c")
    ax.set_ylabel("y/c")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(title.replace(" ", "_") + ".png", dpi=150)
    plt.show()


def plot_cl_comparison(profiles: dict, alphas=None):
    """
    Vergleicht Cl(α)-Kurven mehrerer Profile.
    profiles = {"NACA 4412": (m, p), "NACA 2412": (2, 4), ...}
    """
    if alphas is None:
        alphas = np.linspace(0, 12, 50)

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, (m, p) in profiles.items():
        _, cls = cl_alpha_curve(m, p, alphas)
        ax.plot(alphas, cls, lw=2, label=label)

    ax.axvspan(0, 10, alpha=0.08, color="green", label="Zielbereich 0–10°")
    ax.set_xlabel("Anstellwinkel α [°]")
    ax.set_ylabel("Auftriebsbeiwert Cl")
    ax.set_title("Cl(α) – Profilvergleich (Thin Airfoil Theory)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("cl_comparison.png", dpi=150)
    plt.show()


def plot_cl_uniformity(m_pct, p_pct, t_pct):
    """Zeigt Cl im Zielbereich 0–10° mit Gleichmäßigkeitsmetrik"""
    alphas = np.linspace(0, 10, 50)
    cls = [thin_airfoil_cl(a, m_pct, p_pct)[0] for a in alphas]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(alphas, cls, "b-", lw=2)
    ax.fill_between(alphas, cls, alpha=0.15)
    ax.set_xlabel("Anstellwinkel α [°]")
    ax.set_ylabel("Cl")
    ax.set_title(f"Cl(α) für NACA {int(m_pct)}{int(p_pct)}{int(t_pct):02d}  "
                 f"| ΔCl = {max(cls)-min(cls):.3f}")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("cl_uniformity.png", dpi=150)
    plt.show()


# ─────────────────────────────────────────────────────────────
# 6. HAUPTPROGRAMM
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── Schritt 1: Referenzprofile vergleichen ──────────────────
    print("=" * 55)
    print("  AIRFOIL ANALYSIS & OPTIMIZATION")
    print("=" * 55)

    profiles_to_compare = {
        "NACA 4412": (4, 4),
        "NACA 6412": (6, 4),
        "NACA 4415": (4, 4),
        "NACA 2412": (2, 4),
    }
    plot_cl_comparison(profiles_to_compare)

    for name, (m, p) in profiles_to_compare.items():
        alphas_target = np.linspace(0, 10, 11)
        cls = [thin_airfoil_cl(a, m, p)[0] for a in alphas_target]
        _, alpha_L0 = thin_airfoil_cl(0, m, p)
        print(f"\n{name}:")
        print(f"  αL0       = {alpha_L0:.2f}°")
        print(f"  Cl bei 5° = {thin_airfoil_cl(5, m, p)[0]:.3f}")
        print(f"  Cl-Mittel (0–10°) = {np.mean(cls):.3f}")
        print(f"  Cl-Varianz (0–10°)= {np.var(cls):.4f}")

    # ── Schritt 2: Optimierung ──────────────────────────────────
    opt_params = optimize_naca4()
    m_opt, p_opt, t_opt = opt_params

    # ── Schritt 3: Optimiertes Profil generieren ────────────────
    xu, yu, xl, yl = naca4(m_opt, p_opt, t_opt, n=200)

    name_opt = f"NACA_{int(round(m_opt))}{int(round(p_opt))}{int(round(t_opt)):02d}_opt"
    plot_airfoil(xu, yu, xl, yl, title=name_opt)
    plot_cl_uniformity(m_opt, p_opt, t_opt)

    # ── Schritt 4: Selig-Export ─────────────────────────────────
    to_selig(xu, yu, xl, yl,
             filename=f"{name_opt}.dat",
             name=name_opt)

    # ── Schritt 5: Optional XFOIL ──────────────────────────────
    alphas_xfoil = np.arange(0, 11, 1.0)
    polar = run_xfoil(xu, yu, xl, yl, alphas=alphas_xfoil, Re=500_000)

    if polar is not None:
        print("\n=== XFOIL Polar ===")
        print(f"{'α':>6}  {'Cl':>6}  {'Cd':>7}  {'Cl/Cd':>8}")
        for i in range(len(polar["alpha"])):
            ld = polar["Cl"][i] / polar["Cd"][i] if polar["Cd"][i] > 0 else 0
            print(f"{polar['alpha'][i]:6.1f}  {polar['Cl'][i]:6.3f}  "
                  f"{polar['Cd'][i]:7.5f}  {ld:8.1f}")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        ax1.plot(polar["alpha"], polar["Cl"], "b-o")
        ax1.set_xlabel("α [°]"); ax1.set_ylabel("Cl")
        ax1.set_title("Cl(α) – XFOIL"); ax1.grid(True, alpha=0.3)

        ax2.plot(polar["Cd"], polar["Cl"], "r-o")
        ax2.set_xlabel("Cd"); ax2.set_ylabel("Cl")
        ax2.set_title("Polarer – XFOIL"); ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig("xfoil_polar.png", dpi=150)
        plt.show()
    else:
        print("\nTipp: Installiere XFOIL für Drag & viskose Effekte.")
        print("  https://web.mit.edu/drela/Public/web/xfoil/")

    print("\nFertig! Selig-Datei und Plots gespeichert.")
