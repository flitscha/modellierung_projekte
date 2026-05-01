
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


class Geometry:
    def __init__(self, shapes):
        self.shapes = shapes

    def contains(self, x, y):
        return any(shape.contains(x, y) for shape in self.shapes)

    def bounding_box(self):
        min_x = min(s.x for s in self.shapes)
        min_y = min(s.y for s in self.shapes)
        max_x = max(s.x + s.width for s in self.shapes)
        max_y = max(s.y + s.height for s in self.shapes)
        return min_x, min_y, max_x, max_y

    def approximate_area(self, resolution=1.0):
        # approximate the area, using rasterisation.

        # It should be possible to calculate it exactly, once the "geometry-cleaner" is implemented
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

