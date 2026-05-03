"""
Reconstructs a Geometry object from an exported SVG file.

Only supports <rect> elements for now
"""
import xml.etree.ElementTree as ET
from core.geometry import Geometry, Rectangle

SVG_NS = "http://www.w3.org/2000/svg"


def parse_svg(path: str) -> Geometry:
    """
    Load an SVG file and return a Geometry object.
    Raises ValueError if the file contains no recognisable shapes.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    shapes = _parse_rects(root)

    if not shapes:
        raise ValueError(f"No supported shapes found in {path!r}")

    return Geometry(shapes)


# Shape parsers (one per supported SVG element type)

def _parse_rects(root: ET.Element) -> list:
    shapes = []
    for elem in root.iter(_tag("rect")):
        shapes.append(Rectangle(
            x=float(elem.attrib["x"]),
            y=float(elem.attrib["y"]),
            width=float(elem.attrib["width"]),
            height=float(elem.attrib["height"]),
        ))
    return shapes

# future: _parse_polygons, _parse_paths, …


def _tag(local: str) -> str:
    """Expand a local SVG tag name to its fully-qualified form."""
    return f"{{{SVG_NS}}}{local}"

