"""
Converts a Geometry object into a flat RGBA byte array that can be
uploaded as a DearPyGui dynamic texture.
"""
import numpy as np
from core.geometry import Geometry

# Colors (RGBA)
COLOR_BRIDGE = (80, 160, 220, 255)
COLOR_BG = (30, 30, 40, 255)
COLOR_GRID = (50, 50, 60, 255)


def render_geometry(
    geometry: Geometry,
    canvas_w: int,
    canvas_h: int,
    padding_frac: float = 0.08,
) -> list[float]:
    """
    Returns a flat list of floats in [0, 1] (RGBA per pixel) for DPG.

    The geometry bounding box is scaled to fill the canvas with a small
    padding so the bridge never touches the edges.
    """
    min_x, min_y, max_x, max_y = geometry.bounding_box()
    geo_w = max_x - min_x or 1.0
    geo_h = max_y - min_y or 1.0

    pad_x = canvas_w * padding_frac
    pad_y = canvas_h * padding_frac
    draw_w = canvas_w - 2 * pad_x
    draw_h = canvas_h - 2 * pad_y

    scale = min(draw_w / geo_w, draw_h / geo_h)

    # Centre the geometry in the canvas
    offset_x = pad_x + (draw_w - geo_w * scale) / 2
    offset_y = pad_y + (draw_h - geo_h * scale) / 2

    xs = np.linspace(0, canvas_w - 1, canvas_w)
    ys = np.linspace(0, canvas_h - 1, canvas_h)
    px_grid, py_grid = np.meshgrid(xs, ys)

    gx = (px_grid - offset_x) / scale + min_x
    gy = (canvas_h - 1 - py_grid - offset_y) / scale + min_y

    mask = np.zeros((canvas_h, canvas_w), dtype=bool)
    for shape in geometry.shapes:
        mask |= (
            (gx >= shape.x) & (gx <= shape.x + shape.width) &
            (gy >= shape.y) & (gy <= shape.y + shape.height)
        )

    rgba = np.where(mask[..., None], COLOR_BRIDGE, COLOR_BG) / 255.0
    return rgba.flatten().tolist()

