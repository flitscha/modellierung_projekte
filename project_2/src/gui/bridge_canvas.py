import numpy as np
from shapely.vectorized import contains as shapely_contains
from core.geometry import Geometry
from core.truss import Truss

# Colors (RGBA)
COLOR_BRIDGE = (80, 160, 220, 255)
COLOR_BG = (30, 30, 40, 255)

def render_geometry(
    geometry: Geometry,
    canvas_w: int,
    canvas_h: int,
    padding_frac: float = 0.08,
) -> list[float]:
    # 1. Bounding Box von Shapely holen
    min_x, min_y, max_x, max_y = geometry.clean_shape.bounds
    geo_w = max_x - min_x or 1.0
    geo_h = max_y - min_y or 1.0

    pad_x = canvas_w * padding_frac
    pad_y = canvas_h * padding_frac
    draw_w = canvas_w - 2 * pad_x
    draw_h = canvas_h - 2 * pad_y

    scale = min(draw_w / geo_w, draw_h / geo_h)

    offset_x = pad_x + (draw_w - geo_w * scale) / 2
    offset_y = pad_y + (draw_h - geo_h * scale) / 2

    # 2. Pixel-Gitter in Welt-Koordinaten umrechnen
    # Wir machen das direkt mit NumPy für Speed
    x_coords = (np.arange(canvas_w) - offset_x) / scale + min_x
    y_coords = (canvas_h - 1 - np.arange(canvas_h) - offset_y) / scale + min_y
    
    gx, gy = np.meshgrid(x_coords, y_coords)

    # 3. Die Magie: Vektorisierter Point-in-Polygon Test
    # shapely.vectorized.contains prüft das gesamte Grid auf einmal gegen das verschmolzene Shape
    mask = shapely_contains(geometry.clean_shape, gx, gy)

    # 4. Farben zuweisen
    rgba = np.where(mask[..., None], COLOR_BRIDGE, COLOR_BG).astype(np.float32) / 255.0
    
    return rgba.flatten().tolist()


def render_truss(
    truss: Truss,
    canvas_w: int,
    canvas_h: int,
    padding_frac: float = 0.08,
) -> list[float]:

    import numpy as np

    # --- bounding box ---
    xs = [n.x for n in truss.nodes]
    ys = [n.y for n in truss.nodes]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    geo_w = max_x - min_x or 1.0
    geo_h = max_y - min_y or 1.0

    pad_x = canvas_w * padding_frac
    pad_y = canvas_h * padding_frac
    draw_w = canvas_w - 2 * pad_x
    draw_h = canvas_h - 2 * pad_y

    scale = min(draw_w / geo_w, draw_h / geo_h)

    offset_x = pad_x + (draw_w - geo_w * scale) / 2
    offset_y = pad_y + (draw_h - geo_h * scale) / 2

    # --- image ---
    img = np.zeros((canvas_h, canvas_w, 4), dtype=float)

    # background
    img[:] = np.array([30, 30, 40, 255]) / 255.0

    def world_to_px(x, y):
        px = int(offset_x + (x - min_x) * scale)
        py = int(canvas_h - 1 - (offset_y + (y - min_y) * scale))
        return px, py

    # --- draw edges (simple line rasterization) ---
    for e in truss.edges:
        n1 = truss.nodes[e.i]
        n2 = truss.nodes[e.j]

        x0, y0 = world_to_px(n1.x, n1.y)
        x1, y1 = world_to_px(n2.x, n2.y)

        # Bresenham-like
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        x, y = x0, y0
        while True:
            if 0 <= x < canvas_w and 0 <= y < canvas_h:
                img[y, x] = np.array([220, 220, 100, 255]) / 255.0

            if x == x1 and y == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    # --- draw nodes ---
    for n in truss.nodes:
        px, py = world_to_px(n.x, n.y)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                x = px + dx
                y = py + dy
                if 0 <= x < canvas_w and 0 <= y < canvas_h:
                    img[y, x] = np.array([255, 100, 100, 255]) / 255.0

    return img.flatten().tolist()

