import numpy as np
from core.airfoil import Airfoil

def render_geometry(airfoil: Airfoil, width: int, height: int) -> list:
    # Array Initialization (with background color)
    pixels = np.full((height, width, 4), [0.086, 0.086, 0.118, 1.0], dtype=np.float32)

    # bound checking and scaling
    padding = 40
    min_y = np.min(airfoil.y)
    max_y = np.max(airfoil.y)
    airfoil_height_range = max_y - min_y if (max_y - min_y) > 0 else 0.1

    max_allowable_w = width - 2 * padding
    max_allowable_h = height - 2 * padding

    scale_x = max_allowable_w
    scale_y = max_allowable_h / airfoil_height_range
    scale = min(scale_x, scale_y)

    # find the center of the airfoil
    off_x = (width - scale) / 2
    airfoil_mid_y = (max_y + min_y) / 2
    off_y = (height / 2) + (airfoil_mid_y * scale)

    # Coordinate Transformation
    x_pix = (off_x + airfoil.x * scale).astype(int)
    y_pix = (off_y - airfoil.y * scale).astype(int)

    # Boundary Check (avoid crashes, caused by out-of-bound array access)
    valid = (x_pix >= 1) & (x_pix < width - 1) & (y_pix >= 1) & (y_pix < height - 1)
    x_v = x_pix[valid]
    y_v = y_pix[valid]

    # Draw line at y=0
    chord_y = int(off_y)
    chord_x_start = int(off_x)
    chord_x_end = int(off_x + scale)
    if 0 <= chord_y < height:
        pixels[chord_y, max(0, chord_x_start):min(width, chord_x_end)] = [0.3, 0.3, 0.4, 1.0]

    # drawing Points (also draw neighboring pixels, to make the points look bigger)
    airfoil_color = [1.0, 1.0, 1.0, 1.0]
    pixels[y_v, x_v] = airfoil_color
    pixels[y_v+1, x_v] = airfoil_color
    pixels[y_v-1, x_v] = airfoil_color
    pixels[y_v, x_v+1] = airfoil_color
    pixels[y_v, x_v-1] = airfoil_color

    return pixels.ravel()

