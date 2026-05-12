import os
from core.geometry import Geometry

OUTPUT_DIR = "exports"

def export_svg(geometry: Geometry, design_name: str) -> str:
    """Exportiert die bereinigte Geometrie als saubere SVG-Silhouette."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = _next_path(design_name)
    _write_svg(geometry, path)
    return path

def _next_path(design_name: str) -> str:
    safe_name = design_name.lower().replace(" ", "_")
    n = 1
    while True:
        path = os.path.join(OUTPUT_DIR, f"{safe_name}_{n:03d}.svg")
        if not os.path.exists(path):
            return path
        n += 1

def _write_svg(geometry: Geometry, path: str):
    # Wir nutzen das bereinigte Shape
    shape = geometry.clean_shape
    
    # Bounding Box für das Viewbox-Setup
    min_x, min_y, max_x, max_y = shape.bounds
    width = max_x - min_x
    height = max_y - min_y

    # Wir spiegeln das Koordinatensystem für SVG (y-Achse zeigt nach unten)
    # Falls du die Orientierung beibehalten willst, nutzen wir ein Transform
    with open(path, "w") as f:
        f.write(f'<?xml version="1.0" encoding="utf-8" ?>\n')
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" ')
        f.write(f'width="{width}mm" height="{height}mm" ')
        f.write(f'viewBox="{min_x} {min_y} {width} {height}">\n')
        
        # transform="scale(1, -1)" inkl. Translation wäre nötig, 
        # wenn y=0 oben sein soll. Hier bleiben wir erstmal simpel:
        
        # Shapely generiert den kompletten <path>-Tag inkl. d-Attribut
        # Da clean_shape ein MultiPolygon sein kann (falls Teile nicht verbunden sind),
        # funktioniert das trotzdem einwandfrei.
        f.write(f'  <g transform="translate(0, {max_y + min_y}) scale(1, -1)">\n')
        f.write(f'    {shape.svg(fill_color="black")}\n')
        f.write(f'  </g>\n')
        
        f.write('</svg>\n')
