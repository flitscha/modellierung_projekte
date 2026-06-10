"""
matplotlib plot windows for airfoil analysis.
"""
from __future__ import annotations
import threading
import numpy as np
import matplotlib.pyplot as plt


def show_cl_plot(airfoil_name: str, alpha_range: list, cl_values: list):
    """Open a Cl vs Alpha plot in a new window"""
    def _plot():
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(alpha_range, cl_values, marker="o", linewidth=1.8, color="#4ab4e0")
        ax.axhline(0, color="grey", linewidth=0.6, linestyle="--")
        ax.set_xlabel("Angle of Attack (°)")
        ax.set_ylabel("Cl")
        ax.set_title(f"Cl vs Alpha — {airfoil_name}")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        plt.show()

    threading.Thread(target=_plot, daemon=True).start() # avoid blocking the dearPyGui application


def show_cp_plot(airfoil_name: str, alpha_deg: float, x_c: np.ndarray, cp: np.ndarray, y_c: np.ndarray):
    """Open a Cp distribution plot in a new window"""
    def _plot():
        # Split into upper and lower points
        # NOTE: Here, it is assumed that there are exactly as many points at the top as at the bottom,
        # and that the first half of the points are at the top.
        # This is the case in this project.
        n = len(x_c)
        x_upper = x_c[:n//2]
        cp_upper = cp[:n//2]
        x_lower = x_c[n//2:]
        cp_lower = cp[n//2:]

        # Sort by x so lines draw cleanly
        idx_u = np.argsort(x_upper)
        idx_l = np.argsort(x_lower)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(x_upper[idx_u], cp_upper[idx_u], color="#4ab4e0", linewidth=1.8, label="Upper surface")
        ax.plot(x_lower[idx_l], cp_lower[idx_l], color="#f08040", linewidth=1.8, label="Lower surface")

        ax.invert_yaxis() # convention: suction (negative Cp) at top
        ax.axhline(0, color="grey", linewidth=0.6, linestyle="--")
        ax.set_xlabel("x/c")
        ax.set_ylabel("Cp  (inverted)")
        ax.set_title(f"Pressure Distribution — {airfoil_name}  α={alpha_deg:.1f}°")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        plt.show()

    threading.Thread(target=_plot, daemon=True).start()

