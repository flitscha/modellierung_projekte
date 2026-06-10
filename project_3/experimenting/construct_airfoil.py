"""
Interaktiver Airfoil-Generator
==============================
Parametrisierung: NACA 4-stellig + CST (Class-Shape Transformation)

Anforderungen:
    pip install numpy matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
from matplotlib.patches import FancyArrowPatch


# ─────────────────────────────────────────────────────────────
# Geometrie-Funktionen
# ─────────────────────────────────────────────────────────────

def naca4(m_pct, p_pct, t_pct, n=200):
    """NACA 4-stelliges Profil."""
    m = m_pct / 100.0
    p = p_pct / 10.0
    t = t_pct / 100.0

    beta = np.linspace(0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))

    yt = 5 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1015 * x**4
    )

    if p == 0 or m == 0:
        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)
    else:
        yc = np.where(
            x <= p,
            (m / p**2) * (2 * p * x - x**2),
            (m / (1 - p)**2) * ((1 - 2 * p) + 2 * p * x - x**2),
        )
        dyc_dx = np.where(
            x <= p,
            (2 * m / p**2) * (p - x),
            (2 * m / (1 - p)**2) * (p - x),
        )

    theta = np.arctan(dyc_dx)
    xu = x  - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x  + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)
    return xu, yu, xl, yl, x, yc


def cst(Au, Al, n=200):
    """
    CST-Profil (Kulfan 2008).
    Au, Al: Listen mit Koeffizienten (z.B. je 4 Werte).
    """
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    C = np.sqrt(x) * (1 - x)  # Klassenfunktion N1=0.5, N2=1

    def shape(A):
        N = len(A) - 1
        S = np.zeros_like(x)
        for i, a in enumerate(A):
            from math import comb
            S += a * comb(N, i) * (x**i) * ((1 - x) ** (N - i))
        return S

    yu =  C * shape(Au)
    yl = -C * shape(Al)
    return x, yu, x, yl


def to_selig(xu, yu, xl, yl):
    """Gibt Koordinaten im Selig-Format zurück (numpy array)."""
    upper = np.column_stack([xu[::-1], yu[::-1]])
    lower = np.column_stack([xl[1:], yl[1:]])
    return np.vstack([upper, lower])


def save_selig(xu, yu, xl, yl, filename, name="AIRFOIL"):
    coords = to_selig(xu, yu, xl, yl)
    with open(filename, "w") as f:
        f.write(f"{name}\n")
        for x, y in coords:
            f.write(f"  {x:.6f}  {y:.6f}\n")
    print(f"Gespeichert: {filename}  ({len(coords)} Punkte)")


# ─────────────────────────────────────────────────────────────
# Interaktiver Plot
# ─────────────────────────────────────────────────────────────

def main():
    fig = plt.figure(figsize=(12, 7))
    fig.patch.set_facecolor("#f8f8f8")

    # Hauptplot
    ax = fig.add_axes([0.05, 0.42, 0.60, 0.50])
    ax.set_facecolor("white")
    ax.set_aspect("equal")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.35, 0.35)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_xlabel("x/c", fontsize=10)
    ax.set_ylabel("y/c", fontsize=10)
    ax.set_title("Tragflächenprofil", fontsize=11, pad=8)

    # Plot-Elemente
    (line_upper,) = ax.plot([], [], "b-", lw=2, label="Oberseite")
    (line_lower,) = ax.plot([], [], "r-", lw=2, label="Unterseite")
    (line_camber,) = ax.plot([], [], "g--", lw=1, alpha=0.7, label="Wölbungslinie")
    fill_obj = [ax.fill([], [], alpha=0.12, color="steelblue")[0]]
    ax.legend(loc="upper right", fontsize=8)

    # Info-Text
    info_text = ax.text(
        0.02, 0.97, "", transform=ax.transAxes,
        va="top", fontsize=9, family="monospace",
        color="#333333",
    )

    # ── NACA-4 Schieberegler ──────────────────────────────────
    slider_ax = {}
    naca_sliders = {}

    slider_defs = [
        ("m",  "Wölbung m [%]",     0.0, 9.5, 4.0, 0.1),
        ("p",  "Position p [×10%]", 1.0, 7.0, 4.0, 0.5),
        ("t",  "Dicke t [%]",       4.0, 30.0, 12.0, 0.5),
        ("n",  "Punkte n",          50,  500,  200,  10),
    ]

    for i, (key, label, vmin, vmax, vinit, vstep) in enumerate(slider_defs):
        left  = 0.07
        bot   = 0.30 - i * 0.065
        ax_s  = fig.add_axes([left, bot, 0.52, 0.025])
        sl    = Slider(ax_s, label, vmin, vmax, valinit=vinit, valstep=vstep)
        sl.label.set_fontsize(9)
        sl.valtext.set_fontsize(9)
        naca_sliders[key] = sl
        slider_ax[key] = ax_s

    # ── CST Schieberegler ─────────────────────────────────────
    cst_slider_defs = [
        ("A0u", "Au[0]", 0.0, 0.5, 0.17, 0.01),
        ("A1u", "Au[1]", 0.0, 0.5, 0.22, 0.01),
        ("A0l", "Al[0]", 0.0, 0.5, 0.15, 0.01),
        ("A1l", "Al[1]", 0.0, 0.5, 0.10, 0.01),
    ]
    cst_sliders = {}
    for i, (key, label, vmin, vmax, vinit, vstep) in enumerate(cst_slider_defs):
        left = 0.07
        bot  = 0.30 - i * 0.065
        ax_s = fig.add_axes([left, bot, 0.52, 0.025])
        sl   = Slider(ax_s, label, vmin, vmax, valinit=vinit, valstep=vstep)
        sl.label.set_fontsize(9)
        sl.valtext.set_fontsize(9)
        cst_sliders[key] = sl
        ax_s.set_visible(False)

    # ── Modus-Wahl ────────────────────────────────────────────
    ax_radio = fig.add_axes([0.70, 0.72, 0.13, 0.12])
    radio = RadioButtons(ax_radio, ("NACA 4-digit", "CST"), active=0)
    for label in radio.labels:
        label.set_fontsize(9)

    mode = {"current": "naca"}

    def switch_mode(label):
        if label == "NACA 4-digit":
            mode["current"] = "naca"
            for ax_s in slider_ax.values():
                ax_s.set_visible(True)
            for key, sl in cst_sliders.items():
                sl.ax.set_visible(False)
        else:
            mode["current"] = "cst"
            for ax_s in slider_ax.values():
                ax_s.set_visible(False)
            for key, sl in cst_sliders.items():
                sl.ax.set_visible(True)
        update(None)
        fig.canvas.draw_idle()

    radio.on_clicked(switch_mode)

    # ── Preset-Buttons ────────────────────────────────────────
    ax_pre_label = fig.add_axes([0.70, 0.64, 0.13, 0.02])
    ax_pre_label.axis("off")
    ax_pre_label.text(0.5, 0.5, "Presets", ha="center", fontsize=9, color="#555")

    presets = [
        ("NACA 0012", 0, 0, 12),
        ("NACA 2412", 2, 4, 12),
        ("NACA 4412", 4, 4, 12),
        ("NACA 6412", 6, 4, 12),
        ("NACA 4415", 4, 4, 15),
        ("NACA 6415", 6, 4, 15),
    ]
    preset_buttons = []
    for i, (name, m, p, t) in enumerate(presets):
        row, col = divmod(i, 2)
        bax = fig.add_axes([0.70 + col * 0.07, 0.55 - row * 0.055, 0.065, 0.038])
        btn = Button(bax, name, color="#eaeaea", hovercolor="#d0d0d0")
        btn.label.set_fontsize(7.5)

        def make_cb(m_, p_, t_):
            def cb(event):
                radio.set_active(0)
                switch_mode("NACA 4-digit")
                naca_sliders["m"].set_val(m_)
                naca_sliders["p"].set_val(p_)
                naca_sliders["t"].set_val(t_)
            return cb

        btn.on_clicked(make_cb(m, p, t))
        preset_buttons.append(btn)

    # ── Speichern-Button ──────────────────────────────────────
    ax_save = fig.add_axes([0.70, 0.26, 0.26, 0.05])
    btn_save = Button(ax_save, "Selig .dat speichern", color="#c8e6c9", hovercolor="#a5d6a7")
    btn_save.label.set_fontsize(9)

    save_counter = [0]

    def on_save(event):
        save_counter[0] += 1
        if mode["current"] == "naca":
            m = naca_sliders["m"].val
            p = naca_sliders["p"].val
            t = naca_sliders["t"].val
            n = int(naca_sliders["n"].val)
            xu, yu, xl, yl, _, _ = naca4(m, p, t, n)
            name = f"NACA_{int(m)}{int(p)}{int(t):02d}"
        else:
            Au = [cst_sliders["A0u"].val, cst_sliders["A1u"].val]
            Al = [cst_sliders["A0l"].val, cst_sliders["A1l"].val]
            xu, yu, xl, yl = cst(Au, Al)
            name = f"CST_{save_counter[0]:03d}"
        filename = f"{name}.dat"
        save_selig(xu, yu, xl, yl, filename, name)
        btn_save.label.set_text(f"Gespeichert: {filename}")
        fig.canvas.draw_idle()

    btn_save.on_clicked(on_save)

    # ── Reset-Button ──────────────────────────────────────────
    ax_reset = fig.add_axes([0.70, 0.20, 0.26, 0.05])
    btn_reset = Button(ax_reset, "Reset", color="#f0e6c8", hovercolor="#e0d0a0")
    btn_reset.label.set_fontsize(9)

    def on_reset(event):
        for sl in naca_sliders.values():
            sl.reset()
        for sl in cst_sliders.values():
            sl.reset()
        btn_save.label.set_text("Selig .dat speichern")

    btn_reset.on_clicked(on_reset)

    # ── Update-Funktion ───────────────────────────────────────
    def update(val):
        if mode["current"] == "naca":
            m = naca_sliders["m"].val
            p = naca_sliders["p"].val
            t = naca_sliders["t"].val
            n = int(naca_sliders["n"].val)
            xu, yu, xl, yl, xc, yc = naca4(m, p, t, n)
            name = f"NACA {int(m)}{int(p)}{int(t):02d}"
            t_max = t
            # Max-Dicke Näherung
            t_pos = 0.3  # ungefähre Position des Dickenmaximums
            info = (
                f"{name}\n"
                f"Wölbung:   {m:.1f}%  @ {int(p)*10}% Tiefe\n"
                f"Dicke:     {t:.1f}%\n"
                f"Punkte:    {n}"
            )
            line_camber.set_data(xc, yc)
            line_camber.set_visible(True)
        else:
            Au = [cst_sliders["A0u"].val, cst_sliders["A1u"].val]
            Al = [cst_sliders["A0l"].val, cst_sliders["A1l"].val]
            xu, yu, xl, yl = cst(Au, Al)
            xc = yc = []
            info = (
                f"CST-Profil\n"
                f"Au = [{Au[0]:.2f}, {Au[1]:.2f}]\n"
                f"Al = [{Al[0]:.2f}, {Al[1]:.2f}]"
            )
            line_camber.set_visible(False)

        line_upper.set_data(xu, yu)
        line_lower.set_data(xl, yl)

        # Füllung aktualisieren
        fill_obj[0].remove()
        fill_obj[0] = ax.fill(
            np.concatenate([xu[::-1], xl]),
            np.concatenate([yu[::-1], yl]),
            alpha=0.12, color="steelblue"
        )[0]

        info_text.set_text(info)
        fig.canvas.draw_idle()

    for sl in naca_sliders.values():
        sl.on_changed(update)
    for sl in cst_sliders.values():
        sl.on_changed(update)

    update(None)

    plt.suptitle("Airfoil Generator", fontsize=13, y=0.97, color="#222")
    plt.show()


if __name__ == "__main__":
    main()
