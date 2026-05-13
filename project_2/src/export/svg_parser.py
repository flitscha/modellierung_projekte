"""
Reconstructs a Geometry object from an SVG file written by svg_export.py.
Supports <rect> and <polygon> elements. (polygons are converted into Parallelograms)
"""

import math
import xml.etree.ElementTree as ET
from core.geometry import Geometry, Rectangle, Parallelogram

SVG_NS = "http://www.w3.org/2000/svg"


def parse_svg(path: str) -> Geometry:
    """
    Load an SVG file produced by svg_export.py and return a Geometry object
    Raises ValueError if the file contains no recognisable shapes.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    vb = _viewbox(root)

    shapes = _parse_rects(root, vb) + _parse_polygons(root, vb)
    if not shapes:
        raise ValueError(f"No supported shapes found in {path!r}")
    return Geometry(shapes)


# ------------------ shape parsers -------------------------
def _parse_rects(root: ET.Element, vb: tuple) -> list:
    # Parse <rect> elements -> Rectangle objects
    _, min_y, _, max_y = vb
    shapes = []
    for elem in root.iter(_tag("rect")):
        svg_y  = float(elem.attrib["y"])
        height = float(elem.attrib["height"])

        y = (max_y - svg_y) - height
        shapes.append(Rectangle(
            x=float(elem.attrib["x"]),
            y=y,
            width=float(elem.attrib["width"]),
            height=height,
        ))
    return shapes


def _parse_polygons(root: ET.Element, vb: tuple) -> list:
    # Parse <polygon> elements -> Parallelogram objects
    _, _, _, max_y = vb
    shapes = []
    for elem in root.iter(_tag("polygon")):
        pts = _parse_points(elem.attrib["points"])
        if len(pts) != 4:
            raise ValueError(
                f"<polygon> with {len(pts)} points is not supported "
                f"(only 4-point parallelograms are recognised)."
            )
        shapes.append(_parallelogram_from_quad(pts, max_y))
    return shapes


def _parallelogram_from_quad(pts: list[tuple[float, float]], svg_max_y: float) -> Parallelogram:
    """
    Reconstruct a Parallelogram from 4 SVG polygon vertices

    The points are sorted robustly (largest SVG-y = bottom, smallest = top)
    """
    pts_by_svg_y = sorted(pts, key=lambda p: p[1], reverse=True)
    bottom = sorted(pts_by_svg_y[:2], key=lambda p: p[0])
    top = sorted(pts_by_svg_y[2:], key=lambda p: p[0])

    bl, br = bottom
    tl, tr = top

    # Horizontal measurements are the same in both coordinate systems.
    x = bl[0]
    width  = br[0] - bl[0]
    skew_x = tl[0] - bl[0]

    svg_bottom = bl[1]
    svg_top = tl[1]
    height = svg_bottom - svg_top

    y = svg_max_y - svg_bottom

    if height == 0:
        raise ValueError("Degenerate parallelogram: height is zero.")

    # Invert the constructor formula: width = thickness * side_length / height
    side_length = math.sqrt(skew_x ** 2 + height ** 2)
    thickness = width * height / side_length

    return Parallelogram(x=x, y=y, thickness=thickness, height=height, skew_x=skew_x)


# ---------------- Helpers ---------------------
def _viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    """
    Return (min_x, min_y, max_x, max_y) from the SVG viewBox attribute.
    Falls back to (0, 0, width, height) if viewBox is absent.
    """
    vb = root.attrib.get("viewBox")
    if vb:
        min_x, min_y, w, h = map(float, vb.split())
        return min_x, min_y, min_x + w, min_y + h

    w = float(root.attrib.get("width", "0").rstrip("mm").rstrip("px"))
    h = float(root.attrib.get("height", "0").rstrip("mm").rstrip("px"))
    return 0.0, 0.0, w, h


def _parse_points(points_str: str) -> list[tuple[float, float]]:
    # Parse the SVG 'points' attribute into a list of (x, y) tuples
    tokens = points_str.replace(",", " ").split()
    if len(tokens) % 2 != 0:
        raise ValueError(
            f"Odd number of coordinates in points attribute: {points_str!r}"
        )
    return [(float(tokens[i]), float(tokens[i + 1])) for i in range(0, len(tokens), 2)]


def _tag(local: str) -> str:
    # Expand a local SVG tag name to its fully-qualified form
    return f"{{{SVG_NS}}}{local}"

