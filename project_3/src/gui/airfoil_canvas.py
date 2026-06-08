import numpy as np
from core.airfoil import Airfoil

def render_geometry(airfoil: Airfoil, width: int, height: int, alpha_deg: float = 0.0) -> list:
    # array initialisation (with background color)
    pixels = np.full((height, width, 4), [0.086, 0.086, 0.118, 1.0], dtype=np.float32)

    # rotation
    alpha_rad = np.radians(alpha_deg)
    cos_a = np.cos(-alpha_rad)
    sin_a = np.sin(-alpha_rad)

    x_rot = airfoil.x * cos_a - airfoil.y * sin_a
    y_rot = airfoil.x * sin_a + airfoil.y * cos_a

    # bound checking and scaling
    padding = 60
    min_y, max_y = np.min(airfoil.y), np.max(airfoil.y)
    airfoil_height_range = max_y - min_y if (max_y - min_y) > 0 else 0.1

    max_allowable_w = width - 2 * padding
    max_allowable_h = height - 2 * padding

    scale_x = max_allowable_w
    scale_y = max_allowable_h / airfoil_height_range
    scale = min(scale_x, scale_y) * 0.8 # Multiplied by 0.8 to give some extra room for rotation

    # Center the rotation pivot point (the leading edge at 0,0)
    off_x = (width - scale) / 2
    off_y = (height / 2) + (sin_a * scale * 0.3)

    # coordinate transformation
    x_pix = (off_x + x_rot * scale).astype(int)
    y_pix = (off_y - y_rot * scale).astype(int)

    # draw rotated chord line
    chord_samples = np.linspace(0.0, 1.0, int(scale))
    chord_x_rot = chord_samples * cos_a
    chord_y_rot = chord_samples * sin_a

    chord_x_pix = (off_x + chord_x_rot * scale).astype(int)
    chord_y_pix = (off_y - chord_y_rot * scale).astype(int)

    valid_chord = (chord_x_pix >= 0) & (chord_x_pix < width) & (chord_y_pix >= 0) & (chord_y_pix < height)
    pixels[chord_y_pix[valid_chord], chord_x_pix[valid_chord]] = [0.25, 0.25, 0.35, 1.0] # Muted grey-blue

    # draw angle indicator (straight line at the left)
    baseline_len = int(scale * 0.15)
    if 0 <= int(off_y) < height:
        start_x = max(0, int(off_x) - baseline_len)
        end_x = min(width, int(off_x))
        pixels[int(off_y), start_x:end_x] = [0.4, 0.4, 0.4, 0.5]

    # draw airfoil points
    valid = (x_pix >= 1) & (x_pix < width - 1) & (y_pix >= 1) & (y_pix < height - 1)
    x_v = x_pix[valid]
    y_v = y_pix[valid]

    # Thick drawing point brush
    airfoil_color = [1.0, 1.0, 1.0, 1.0]
    pixels[y_v, x_v] = airfoil_color
    pixels[y_v+1, x_v] = airfoil_color
    pixels[y_v-1, x_v] = airfoil_color
    pixels[y_v, x_v+1] = airfoil_color
    pixels[y_v, x_v-1] = airfoil_color

    return pixels.ravel()
