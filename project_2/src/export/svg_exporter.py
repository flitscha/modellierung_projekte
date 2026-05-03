"""
Exports a Geometry object to an SVG file.

Output folder is created automatically if it doesn't exist.
Files are named  <design_name>_001.svg, _002.svg
"""
import os

OUTPUT_DIR = "exports"


def export_svg(geometry, design_name: str) -> str:
    # Export geometry to SVG. Returns the path of the written file.
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = _next_path(design_name)
    _write_svg(geometry, path)
    return path


# ----------- Helpers -------------------
def _next_path(design_name: str) -> str:
    """Return the next non-existing exports/<design_name>_NNN.svg path."""
    safe_name = design_name.lower().replace(" ", "_")
    n = 1
    while True:
        path = os.path.join(OUTPUT_DIR, f"{safe_name}_{n:03d}.svg")
        if not os.path.exists(path):
            return path
        n += 1


def _write_svg(geometry, path: str):
    min_x, min_y, max_x, max_y = geometry.bounding_box()
    width  = max_x - min_x
    height = max_y - min_y

    with open(path, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" ')
        f.write(f'width="{width}mm" height="{height}mm" ')
        f.write(f'viewBox="{min_x} {min_y} {width} {height}">\n')
        for shape in geometry.shapes:
            f.write(
                f'  <rect x="{shape.x}" y="{shape.y}" '
                f'width="{shape.width}" height="{shape.height}" '
                f'style="fill:black;" />\n'
            )
        f.write('</svg>\n')

