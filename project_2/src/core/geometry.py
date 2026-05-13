"""
geometry.py
===========
Geometrie-Primitive für die Brückensimulation.

Design-Prinzip: contains(px, py) akzeptiert sowohl skalare float-Werte
als auch numpy-Arrays beliebiger Form. Das ermöglicht:
  - Vektorisierte FEM-Rasterisierung (meshgrid übergeben)
  - Vektorisierte Gewichtsschätzung (kein Python-Loop mehr)
  - Rückwärtskompatibilität mit altem skalarem Code

Intern wird überall & / | statt and / or verwendet – das funktioniert
für bool-Arrays und bool-Skalare gleichermaßen.
"""

from __future__ import annotations

import math
from typing import Tuple, Union

import numpy as np

import config


# Typ-Alias für skalare oder Array-Eingaben
Scalar_or_Array = Union[float, np.ndarray]


# ---------------------------------------------------------------------------
# Basisklasse
# ---------------------------------------------------------------------------

class Shape:
    """
    Abstrakte Basisklasse für alle Geometrie-Primitive.

    Unterklassen müssen implementieren:
      - contains(px, py)  → bool oder bool-Array
      - bounding_box()    → (min_x, min_y, max_x, max_y)
    """

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        raise NotImplementedError

    def bounding_box(self) -> Tuple[float, float, float, float]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Rechteck
# ---------------------------------------------------------------------------

class Rectangle(Shape):
    """
    Achsenparalleles Rechteck.

    Parameter
    ---------
    x, y    : untere linke Ecke (mm)
    width   : Breite (mm)
    height  : Höhe (mm)
    """

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x      = x
        self.y      = y
        self.width  = width
        self.height = height

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        return (
            (px >= self.x) & (px <= self.x + self.width) &
            (py >= self.y) & (py <= self.y + self.height)
        )

    def bounding_box(self) -> Tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.width, self.y + self.height


# ---------------------------------------------------------------------------
# Parallelogramm
# ---------------------------------------------------------------------------

class Parallelogram(Shape):
    """
    Parallelogramm mit senkrechter Wandstärke und horizontalem Versatz.

    Der Parameter `thickness` ist die *senkrechte* Distanz zwischen den
    beiden schrägen Seiten – also die echte Wandstärke wie sie ein
    3D-Drucker produziert. Die interne horizontale Breite `width` wird
    automatisch abgeleitet:

        side_length = √(skew_x² + height²)
        width       = thickness × side_length / height

    Ecken (counter-clockwise ab unten-links):
        BL = (x,                   y)
        BR = (x + width,           y)
        TR = (x + width + skew_x,  y + height)
        TL = (x + skew_x,          y + height)

    Positives skew_x → lehnt nach rechts.
    Negatives skew_x → lehnt nach links.

    contains() verwendet lokale (u, v)-Koordinaten via Cramer-Regel –
    exakt und vektorisiert.
    """

    def __init__(self, x: float, y: float, thickness: float,
                 height: float, skew_x: float = 0.0):
        self.x         = x
        self.y         = y
        self.thickness = thickness
        self.height    = height
        self.skew_x    = skew_x

        side_length = math.sqrt(skew_x ** 2 + height ** 2)
        self.width  = thickness * side_length / height

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        # Lokale Koordinaten relativ zur unteren linken Ecke
        lx = px - self.x
        ly = py - self.y

        # Löse [width, skew_x; 0, height] * [u; v] = [lx; ly] per Cramer
        # det = width * height  (immer > 0 für valide Geometrie)
        det = self.width * self.height
        if det == 0:
            return np.zeros_like(px, dtype=bool) if isinstance(px, np.ndarray) else False

        u = (lx * self.height - ly * self.skew_x) / det
        v = ly / self.height

        return (u >= 0.0) & (u <= 1.0) & (v >= 0.0) & (v <= 1.0)

    def bounding_box(self) -> Tuple[float, float, float, float]:
        corners_x = [self.x, self.x + self.width,
                     self.x + self.skew_x, self.x + self.width + self.skew_x]
        corners_y = [self.y, self.y, self.y + self.height, self.y + self.height]
        return min(corners_x), min(corners_y), max(corners_x), max(corners_y)


# ---------------------------------------------------------------------------
# Geometry (Zusammensetzung mehrerer Shapes)
# ---------------------------------------------------------------------------

class Geometry:
    """
    Union mehrerer Shapes: ein Punkt liegt in der Geometrie wenn er in
    mindestens einem Shape liegt.

    contains() ist vollständig vektorisiert – px und py können numpy-Arrays
    beliebiger Form sein (z.B. ein meshgrid für FEM oder Gewichtsschätzung).
    """

    def __init__(self, shapes: list[Shape]):
        self.shapes = shapes

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        """
        Gibt True zurück wo (px, py) in mindestens einem Shape liegt.
        Funktioniert für Skalare und numpy-Arrays gleichermaßen.
        """
        result = None
        for shape in self.shapes:
            mask = shape.contains(px, py)
            result = mask if result is None else (result | mask)

        # Fallback für leere Geometrie
        if result is None:
            return np.zeros_like(px, dtype=bool) if isinstance(px, np.ndarray) else False
        return result

    def bounding_box(self) -> Tuple[float, float, float, float]:
        """Umschließendes Rechteck über alle Shapes."""
        boxes = [s.bounding_box() for s in self.shapes]
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)
        return min_x, min_y, max_x, max_y

    # ------------------------------------------------------------------
    # Flächenberechnung (vektorisiert)
    # ------------------------------------------------------------------

    def approximate_area(self, nx: int, ny: int) -> float:
        """
        Berechnet die Querschnittsfläche durch Rasterisierung auf einem
        nx × ny Gitter. Vektorisiert – kein Python-Loop.

        Parameters
        ----------
        nx, ny : Gittergröße (höher = genauer)

        Returns
        -------
        Fläche in mm²
        """
        min_x, min_y, max_x, max_y = self.bounding_box()
        dx = (max_x - min_x) / nx
        dy = (max_y - min_y) / ny

        # Mittelpunkte aller Zellen
        xs = np.linspace(min_x + dx/2, max_x - dx/2, nx)
        ys = np.linspace(min_y + dy/2, max_y - dy/2, ny)
        xs_grid, ys_grid = np.meshgrid(xs, ys, indexing='ij')  # (nx, ny)

        mask = self.contains(xs_grid, ys_grid)
        return float(np.sum(mask)) * dx * dy

    # ------------------------------------------------------------------
    # Adaptive Gewichtsschätzung
    # ------------------------------------------------------------------

    def estimate_weight_grams(
        self,
        initial_nx: int = 50,
        max_nx: int     = 2000,
        tol: float      = 1e-3,
    ) -> float:
        """
        Schätzt das Gewicht adaptiv: verdoppelt die Auflösung bis die
        berechnete Fläche konvergiert (relative Änderung < tol).

        Hintergrund: Bei feinen Geometrien (dünne Stäbe, scharfe Ecken)
        liefert ein grobes Raster systematisch falsche Flächen. Die
        adaptive Variante ist zuverlässiger und trotzdem schnell, weil
        approximate_area() vektorisiert ist.

        Parameters
        ----------
        initial_nx : Startraster (quadratisch)
        max_nx     : maximale Auflösung (Sicherheitsstop)
        tol        : relative Konvergenztoleranz

        Returns
        -------
        Gewicht in Gramm
        """
        min_x, min_y, max_x, max_y = self.bounding_box()
        aspect = (max_y - min_y) / max((max_x - min_x), 1e-9)

        prev_area = None
        nx = initial_nx

        while nx <= max_nx:
            ny = max(4, round(nx * aspect))
            area = self.approximate_area(nx, ny)

            if prev_area is not None:
                rel = abs(area - prev_area) / (abs(prev_area) + 1e-12)
                if rel < tol:
                    break

            prev_area = area
            nx = int(nx * 2)   # verdoppeln statt ×1.5: Gitterpunkte überlappen nicht

        volume_mm3 = area * config.BRIDGE_DEPTH
        return volume_mm3 * config.PLA_DENSITY

