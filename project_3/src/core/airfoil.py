"""
Airfoil geometry container.

Stores the (x, y) coordinates in Selig format:
  - x in [0, 1], y in [-1, 1]
  - ordered: counter-clockwise, starting from Top-Right
"""
from __future__ import annotations
import numpy as np


class Airfoil:
    """
    Parameters
    ----------
    coords : (N, 2) float array
        Coordinates in Selig ordering (Top-Rihgt -> Top-Left -> Bottom-Left -> Bottom-Right).
    name : str
    """
    def __init__(self, coords: np.ndarray, name: str = ""):
        self.coords = np.asarray(coords, dtype=float) # shape (N, 2)
        self.name = name

    @property
    def x(self) -> np.ndarray:
        return self.coords[:, 0]

    @property
    def y(self) -> np.ndarray:
        return self.coords[:, 1]

    def upper_surface(self) -> np.ndarray:
        """Points on the upper surface (y >= 0 side), Top-Rihgt -> Top-Left"""
        le = int(np.argmin(self.x))
        return self.coords[: le + 1]

    def lower_surface(self) -> np.ndarray:
        """Points on the lower surface (y <= 0 side), Bottom-Left -> Bottom-Right"""
        le = int(np.argmin(self.x))
        return self.coords[le:]

    # ------------ Export ------------------------
    def to_selig(self) -> str:
        """Return coordinate data as a Selig-format string."""
        lines = [f"{x:.6f} {y:.6f}" for x, y in self.coords]
        return "\n".join(lines)

    def save_selig(self, path: str):
        with open(path, "w") as f:
            f.write(self.to_selig())

