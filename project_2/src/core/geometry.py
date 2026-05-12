import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union, triangulate
from sectionproperties.pre.geometry import Geometry as SPGeometry
from skfem import MeshTri

import config


class Geometry:
    def __init__(self):
        # Wir starten mit einer Liste von "naiven" Polygonen
        self.raw_shapes = []
        self._cached_clean_shape = None

    def add_rectangle(self, x, y, width, height):
        # Erzeugt ein Shapely-Rechteck
        coords = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
        self.raw_shapes.append(Polygon(coords))
        self._cached_clean_shape = None

    def add_parallelogram(self, x, y, width, height, skew_x):
        # Erzeugt ein Shapely-Parallelogramm
        coords = [
            (x, y), 
            (x + width, y), 
            (x + width + skew_x, y + height), 
            (x + skew_x, y + height)
        ]
        self.raw_shapes.append(Polygon(coords))
        self._cached_clean_shape = None

    @property
    def clean_shape(self):
        if self._cached_clean_shape is None:
            self._cached_clean_shape = unary_union(self.raw_shapes)
        return self._cached_clean_shape

    def build_skfem_mesh(self, max_area=2.0):
        """Erstellt ein Dreiecksnetz für die FEM-Analyse."""
        shape = self.clean_shape
        
        # 1. Delaunay-Triangulierung der Eckpunkte
        all_triangles = triangulate(shape)
        
        # 2. Nur Dreiecke behalten, die INSIDE der Silhouette liegen
        # Wir nutzen einen kleinen negativen Buffer, um Grenzfälle zu vermeiden
        valid_tris = [t for t in all_triangles if shape.contains(t.centroid)]
        
        pts = []
        elements = []
        pt_map = {}

        for tri in valid_tris:
            tri_idx = []
            # Dreiecke haben in Shapely 4 Punkte (der letzte ist gleich dem ersten)
            for coord in tri.exterior.coords[:-1]:
                if coord not in pt_map:
                    pt_map[coord] = len(pts)
                    pts.append(coord)
                tri_idx.append(pt_map[coord])
            elements.append(tri_idx)

        if not pts:
            raise ValueError("Meshing fehlgeschlagen: Keine gültigen Dreiecke gefunden.")

        return MeshTri(np.array(pts).T, np.array(elements).T)

    def get_area(self):
        """Exakte Fläche ohne Rasterung."""
        return self.clean_shape.area

    def estimate_weight_grams(self):
        volume = self.get_area() * config.BRIDGE_DEPTH
        return volume * config.PLA_DENSITY

    def export_svg(self, filename):
        """Speichert die saubere Außenhülle als SVG."""
        svg_data = self.clean_shape._repr_svg_()
        with open(filename, "w") as f:
            f.write(f'<?xml version="1.0" encoding="utf-8" ?>\n')
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1">\n')
            f.write(svg_data)
            f.write(f'\n</svg>')

