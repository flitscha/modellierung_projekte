import xml.etree.ElementTree as ET
import re
from shapely.geometry import Polygon
from core.geometry import Geometry

SVG_NS = "http://www.w3.org/2000/svg"

def parse_svg(path: str) -> Geometry:
    tree = ET.parse(path)
    root = tree.getroot()

    geo = Geometry()
    
    # 1. Alte Rechtecke trotzdem noch unterstützen (Abwärtskompatibilität)
    _parse_rects(root, geo)
    
    # 2. Den neuen Silhouette-Pfad parsen
    _parse_paths(root, geo)

    if not geo.raw_shapes:
        raise ValueError(f"No supported shapes found in {path!r}")

    return geo

def _parse_rects(root, geo):
    for elem in root.iter(_tag("rect")):
        geo.add_rectangle(
            x=float(elem.attrib["x"]),
            y=float(elem.attrib["y"]),
            width=float(elem.attrib["width"]),
            height=float(elem.attrib["height"]),
        )

def _parse_paths(root, geo):
    """Liest <path d="..."> Elemente und wandelt sie in Shapely-Polygone um."""
    for elem in root.iter(_tag("path")):
        d_string = elem.attrib.get("d", "")
        if not d_string:
            continue
            
        # Sehr simpler Parser für "M x,y L x,y ... Z" Formate, 
        # wie sie Shapely generiert:
        # Findet alle Zahlenpaare im Pfad-String
        coords = re.findall(r"([-+]?\d*\.\d+|[-+]?\d+)", d_string)
        pts = []
        for i in range(0, len(coords), 2):
            pts.append((float(coords[i]), float(coords[i+1])))
            
        if len(pts) >= 3:
            geo.raw_shapes.append(Polygon(pts))

def _tag(local: str) -> str:
    return f"{{{SVG_NS}}}{local}"

