"""
Exports a Geometry object to an SVG file.
Output folder is created automatically if it doesn't exist.
Files are named  <design_name>_001.svg, _002.svg, ...
"""

import os
from core.geometry import Geometry, Rectangle, Parallelogram

OUTPUT_DIR = "exports"


def export_svg(geometry: Geometry, design_name: str) -> str:
    # Export geometry to SVG and return the path of the written file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = _next_path(design_name)
    _write_svg(geometry, path)
    return path


# --------------- Helpers ---------------------
def _next_path(design_name: str) -> str:
    # Return the next non-existing exports/<design_name>_NNN.svg path
    safe_name = design_name.lower().replace(" ", "_")
    n = 1
    while True:
        path = os.path.join(OUTPUT_DIR, f"{safe_name}_{n:03d}.svg")
        if not os.path.exists(path):
            return path
        n += 1


def _write_svg(geometry: Geometry, path: str) -> None:
    min_x, min_y, max_x, max_y = geometry.bounding_box()
    vb_width  = max_x - min_x
    vb_height = max_y - min_y

    def flip(y_internal: float) -> float:
        # Convert internal y (up) -> SVG y (down) within the viewBox
        return max_y - y_internal

    with open(path, "w") as f:
        f.write(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{vb_width}mm" height="{vb_height}mm" '
            f'viewBox="{min_x} {min_y} {vb_width} {vb_height}">\n'
        )

        for shape in geometry.shapes:
            if isinstance(shape, Parallelogram):
                x, y = shape.x, shape.y
                w, h = shape.width, shape.height
                sx = shape.skew_x

                svg_bottom = flip(y)
                svg_top = flip(y + h)

                pts = (
                    f"{x},{svg_bottom} "
                    f"{x + w},{svg_bottom} "
                    f"{x + w + sx},{svg_top} "
                    f"{x + sx},{svg_top}"
                )
                f.write(f'  <polygon points="{pts}" style="fill:black;" />\n')

            elif isinstance(shape, Rectangle):
                svg_y = flip(shape.y + shape.height)
                f.write(
                    f'  <rect x="{shape.x}" y="{svg_y}" '
                    f'width="{shape.width}" height="{shape.height}" '
                    f'style="fill:black;" />\n'
                )

        f.write('</svg>\n')

