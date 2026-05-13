from __future__ import annotations

import math
from typing import Tuple, Union

import numpy as np

import config


Scalar_or_Array = Union[float, np.ndarray]


class Shape:
    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        raise NotImplementedError

    def bounding_box(self) -> Tuple[float, float, float, float]:
        raise NotImplementedError


class Rectangle(Shape):
    def __init__(self, x: float, y: float, width: float, height: float):
        # (x, y) is the bottom-left corner of the rectangle
        self.x = x
        self.y = y
        self.width  = width
        self.height = height

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        return (
            (px >= self.x) & (px <= self.x + self.width) &
            (py >= self.y) & (py <= self.y + self.height)
        )

    def bounding_box(self) -> Tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.width, self.y + self.height


class Parallelogram(Shape):
    """
    Parallelogram defined by vertical thickness, height, and horizontal skew.

    The actual horizontal width is computed automatically so that
    'thickness' represents the perpendicular wall thickness.

    Positive skew_x leans right, negative skew_x leans left.
    """

    def __init__(self, x: float, y: float, thickness: float, height: float, skew_x: float = 0.0):
        self.x = x
        self.y = y
        self.thickness = thickness
        self.height = height
        self.skew_x = skew_x

        side_length = math.sqrt(skew_x ** 2 + height ** 2)
        self.width = thickness * side_length / height

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        lx = px - self.x
        ly = py - self.y

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


class Geometry:
    # A Geometry-object is a collection of Shapes.
    def __init__(self, shapes: list[Shape]):
        self.shapes = shapes

    def contains(self, px: Scalar_or_Array, py: Scalar_or_Array) -> Scalar_or_Array:
        # returns true, where (px, py) lies in at least one Shape.
        result = None
        for shape in self.shapes:
            mask = shape.contains(px, py)
            result = mask if result is None else (result | mask)

        if result is None:
            return np.zeros_like(px, dtype=bool) if isinstance(px, np.ndarray) else False
        return result


    def bounding_box(self) -> Tuple[float, float, float, float]:
        boxes = [s.bounding_box() for s in self.shapes]
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)
        return min_x, min_y, max_x, max_y


    def approximate_area(self, nx: int, ny: int) -> float:
        min_x, min_y, max_x, max_y = self.bounding_box()
        dx = (max_x - min_x) / nx
        dy = (max_y - min_y) / ny

        # center point for each cell
        xs = np.linspace(min_x + dx/2, max_x - dx/2, nx)
        ys = np.linspace(min_y + dy/2, max_y - dy/2, ny)
        xs_grid, ys_grid = np.meshgrid(xs, ys, indexing='ij')

        mask = self.contains(xs_grid, ys_grid)
        return float(np.sum(mask)) * dx * dy


    def estimate_weight_grams(
        self,
        initial_nx: int = 50,
        max_nx: int = 4000,
        tol: float = 1e-3,
    ) -> float:
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
            nx = int(nx * 2)

        volume_mm3 = area * config.BRIDGE_DEPTH
        return volume_mm3 * config.PLA_DENSITY

