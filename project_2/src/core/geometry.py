import math
import config


class Rectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, px, py):
        return (
            self.x <= px <= self.x + self.width and
            self.y <= py <= self.y + self.height
        )


class Parallelogram:
    """
    A parallelogram defined by its bottom-left corner, true perpendicular
    thickness, height, and a horizontal skew offset applied to the top edge.

    The public parameter `thickness` is the *perpendicular* distance between
    the two slanted (left / right) sides – i.e. the real wall thickness that
    a 3-D printer will produce.  The internal horizontal span `width` is
    derived automatically:

        side_length = √(skew_x² + height²)
        width       = thickness × side_length / height

    Vertices (counter-clockwise from bottom-left):
        BL = (x,                   y)
        BR = (x + width,           y)
        TR = (x + width + skew_x,  y + height)
        TL = (x + skew_x,          y + height)

    A positive skew_x leans the shape to the right.
    A negative skew_x leans it to the left.

    contains() uses a fast point-in-parallelogram test via local
    (u, v) coordinates so rasterisation stays exact.
    """

    def __init__(self, x, y, thickness, height, skew_x=0.0):
        self.x         = x
        self.y         = y
        self.thickness = thickness
        self.height    = height
        self.skew_x    = skew_x

        # Derive the internal horizontal span from the true thickness.
        # thickness = width * height / side_length
        # → width   = thickness * side_length / height
        side_length = math.sqrt(skew_x ** 2 + height ** 2)
        self.width = thickness * side_length / height

    def contains(self, px, py):
        # Translate so BL is the origin
        lx = px - self.x
        ly = py - self.y

        # Local basis:
        #   e1 = (width, 0)       → horizontal bottom edge
        #   e2 = (skew_x, height) → left side edge
        # Solve [e1 | e2] * [u; v] = [lx; ly]  via Cramer's rule
        det = self.width * self.height
        if det == 0:
            return False

        u = (lx * self.height - ly * self.skew_x) / det
        v = ly / self.height

        return 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0


class Geometry:
    def __init__(self, shapes):
        self.shapes = shapes

    def contains(self, x, y):
        return any(shape.contains(x, y) for shape in self.shapes)

    def bounding_box(self):
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for s in self.shapes:
            if isinstance(s, Parallelogram):
                # All four corners  (self.width is the derived horizontal span)
                corners_x = [s.x, s.x + s.width,
                              s.x + s.skew_x, s.x + s.width + s.skew_x]
                corners_y = [s.y, s.y, s.y + s.height, s.y + s.height]
                min_x = min(min_x, *corners_x)
                max_x = max(max_x, *corners_x)
                min_y = min(min_y, *corners_y)
                max_y = max(max_y, *corners_y)
            else:  # Rectangle
                min_x = min(min_x, s.x)
                min_y = min(min_y, s.y)
                max_x = max(max_x, s.x + s.width)
                max_y = max(max_y, s.y + s.height)

        return min_x, min_y, max_x, max_y

    def approximate_area(self, resolution=1.0):
        # Approximate the area using rasterisation.
        # Exact calculation possible once a geometry-cleaner is implemented.
        min_x, min_y, max_x, max_y = self.bounding_box()

        area = 0.0
        x = min_x
        while x < max_x:
            y = min_y
            while y < max_y:
                if self.contains(x, y):
                    area += resolution * resolution
                y += resolution
            x += resolution

        return area

    def estimate_weight_grams(self):
        """
        Cross-section area (mm²) × extrusion depth (mm) × PLA density (g/mm³).
        """
        area = self.approximate_area(resolution=0.5)
        volume = area * config.BRIDGE_DEPTH  # mm³
        return volume * config.PLA_DENSITY   # grams