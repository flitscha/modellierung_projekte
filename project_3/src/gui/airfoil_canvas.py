import numpy as np
from core.airfoil import Airfoil


def render_geometry(airfoil: Airfoil, width: int, height: int, alpha_deg: float = 0.0) -> list:
    """Render mode 1: Draws the (rotated) airfoil"""
    pixels = np.full((height, width, 4), [0.086, 0.086, 0.118, 1.0], dtype=np.float32)
    t = _get_transformation_matrices(airfoil, width, height, alpha_deg)
    _draw_environment_basics(pixels, width, height, t)

    # Security check: avoid out of bound access in the pixel-array
    valid = (t["x_pix"] >= 1) & (t["x_pix"] < width - 1) & (t["y_pix"] >= 1) & (t["y_pix"] < height - 1)
    x_v, y_v = t["x_pix"][valid], t["y_pix"][valid]

    # draw thick points
    airfoil_color = [1.0, 1.0, 1.0, 1.0]
    pixels[y_v, x_v] = airfoil_color
    pixels[y_v+1, x_v] = airfoil_color
    pixels[y_v-1, x_v] = airfoil_color
    pixels[y_v, x_v+1] = airfoil_color
    pixels[y_v, x_v-1] = airfoil_color

    return pixels.ravel()


def render_pressure_analysis(airfoil: Airfoil, width: int, height: int, alpha_deg: float, solver_results: dict) -> list:
    """
    Render mode 2: Colors panels by local pressure and maps
    the net lift distribution (Pressure Difference) as arrows below the airfoil.
    """
    pixels = np.full((height, width, 4), [0.086, 0.086, 0.118, 1.0], dtype=np.float32)
    t = _get_transformation_matrices(airfoil, width, height, alpha_deg)
    _draw_environment_basics(pixels, width, height, t)

    if solver_results is None or "cp" not in solver_results:
        return pixels.ravel()

    cp = solver_results["cp"]
    n_panels = len(airfoil.x) - 1

    # color the airfoil panels
    for i in range(n_panels):
        val = cp[i]

        if val < 0: # neagtive pressure: Blue
            intensity = min(1.0, abs(val) / 2.5)
            color = [1.0 - intensity, 1.0 - intensity, 1.0, 1.0]

        else: # positive pressure: Red
            intensity = min(1.0, val / 1.0)
            color = [1.0, 1.0 - intensity, 1.0 - intensity, 1.0]

        _draw_line(pixels, width, height, t["x_pix"][i], t["y_pix"][i], t["x_pix"][i+1], t["y_pix"][i+1], color)

    # Draw pressure difference arrows below the plot
    baseline_y = int(height - 60)
    nose_idx = np.argmin(airfoil.x)

    x_c = 0.5 * (airfoil.x[:-1] + airfoil.x[1:])

    x_upper = x_c[:nose_idx]
    cp_upper = cp[:nose_idx]

    x_lower = x_c[nose_idx:]
    cp_lower = cp[nose_idx:]

    # sample uniformly n_stations points at the x-axis
    n_stations = 150
    x_stations = np.linspace(np.min(airfoil.x) + 0.005, np.max(airfoil.x) - 0.005, n_stations)

    for x_s in x_stations:
        # search for the nearest panels and use them to estimate the cp-difference
        idx_up = np.argmin(np.abs(x_upper - x_s))
        idx_lo = np.argmin(np.abs(x_lower - x_s))

        delta_cp = cp_lower[idx_lo] - cp_upper[idx_up]

        mx_pix = int(t["off_x"] + x_s * t["scale"]) # x-coordinate to pixel coordinate

        arrow_len = int(delta_cp * 30.0)

        if 0 <= mx_pix < width and arrow_len != 0:
            target_y = baseline_y - arrow_len

            if arrow_len > 0:
                arrow_color = [0.3, 0.9, 0.4, 0.7] # Green: positive lift
                tip_color = [0.3, 0.9, 0.4, 1.0]
            else:
                arrow_color = [1.0, 0.4, 0.2, 0.7] # Red: negative lift
                tip_color = [1.0, 0.4, 0.2, 1.0]

            _draw_line(pixels, width, height, mx_pix, baseline_y, mx_pix, target_y, arrow_color)

            if 0 <= target_y < height:
                if mx_pix > 0:
                    pixels[target_y, mx_pix - 1] = tip_color
                if mx_pix < width - 1:
                    pixels[target_y, mx_pix + 1] = tip_color

    # Draw a thin grey base line for the arrows to stand on
    start_b = max(0, int(t["off_x"]))
    end_b = min(width, int(t["off_x"] + t["scale"]))
    if 0 <= baseline_y < height:
        pixels[baseline_y, start_b:end_b] = [0.4, 0.4, 0.4, 1.0]

    return pixels.ravel()



# ----------------- Helpers ----------------------

def _draw_line(pixels, width, height, x0, y0, x1, y1, color):
    """Draws a line in the pixel-array. The Bresenham algorithm is used"""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < width and 0 <= y0 < height:
            pixels[y0, x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def _get_transformation_matrices(airfoil: Airfoil, width: int, height: int, alpha_deg: float):
    """
    Calculates the rotated coordinates and the scaling-offsets.
    Returns everything, needed for the render-function
    """
    alpha_rad = np.radians(alpha_deg)
    cos_a = np.cos(-alpha_rad)
    sin_a = np.sin(-alpha_rad)

    # rotate the points
    x_rot = airfoil.x * cos_a - airfoil.y * sin_a
    y_rot = airfoil.x * sin_a + airfoil.y * cos_a

    # scaling
    padding = 60
    min_y, max_y = np.min(airfoil.y), np.max(airfoil.y)
    airfoil_height_range = max_y - min_y if (max_y - min_y) > 0 else 0.1

    max_allowable_w = width - 2 * padding
    max_allowable_h = height - 2 * padding

    scale_x = max_allowable_w
    scale_y = max_allowable_h / airfoil_height_range
    scale = min(scale_x, scale_y) * 0.8 # Multiplied by 0.8 to give some extra room for rotation

    # calculate offsets
    off_x = (width - scale) / 2
    off_y = (height / 2) - (np.sin(alpha_rad) * scale * 0.3)

    # transform to pixel coordinates
    x_pix = (off_x + x_rot * scale).astype(int)
    y_pix = (off_y - y_rot * scale).astype(int)

    return {
        "x_pix": x_pix, "y_pix": y_pix,
        "scale": scale, "off_x": off_x, "off_y": off_y,
        "cos_a": cos_a, "sin_a": sin_a, "alpha_rad": alpha_rad
    }


def _draw_environment_basics(pixels, width, height, t):
    """Draws the rotated base-line and the y=0 line to indicate the direction of the air flow"""
    chord_samples = np.linspace(0.0, 1.0, int(t["scale"]))
    chord_x_pix = (t["off_x"] + chord_samples * t["cos_a"] * t["scale"]).astype(int)
    chord_y_pix = (t["off_y"] - chord_samples * t["sin_a"] * t["scale"]).astype(int)

    valid_chord = (chord_x_pix >= 0) & (chord_x_pix < width) & (chord_y_pix >= 0) & (chord_y_pix < height)
    pixels[chord_y_pix[valid_chord], chord_x_pix[valid_chord]] = [0.25, 0.25, 0.35, 1.0]

    # Horizontal line
    baseline_len = int(t["scale"] * 0.15)
    if 0 <= int(t["off_y"]) < height:
        start_x = max(0, int(t["off_x"]) - baseline_len)
        end_x = min(width, int(t["off_x"]))
        pixels[int(t["off_y"]), start_x:end_x] = [0.4, 0.4, 0.4, 0.5]

