"""
Howe Truss Design
=================
Topology: Two horizontal chords (top + bottom plate) connected by
          vertical posts and diagonal braces.

Howe convention: diagonals point OUTWARD away from the centre span,
i.e. they slope from the inner top-chord toward the outer bottom-chord.
This puts the diagonals in compression (contrast with Pratt).

Parameters
----------
num_panels      : int   – number of truss panels (spaces between verticals)
chord_thickness : float – height of top and bottom horizontal plate  [mm]
post_thickness  : float – width of vertical posts                    [mm]
brace_thickness : float – true perpendicular thickness of diagonal braces [mm]
                          (minimum 0.4 mm – 3-D printing constraint)
"""

import config
from core.design import Design
from core.geometry import Geometry
from core.parameter import FloatParameter, IntParameter
from core.truss import Truss, Edge, Node
import math

MIN_BRACE_THICKNESS = 0.4   # mm – smallest wall a 3-D printer can reliably produce


class HoweTrussDesign(Design):

    def __init__(self):
        self.name = "Howe Truss"

    def parameter_space(self):
        return [
            IntParameter("num_panels", 2, 20),
            FloatParameter("chord_thickness", config.MIN_FEATURE_SIZE, 4.0),
            FloatParameter("post_thickness",  config.MIN_FEATURE_SIZE, 3.0),
            FloatParameter("brace_thickness", MIN_BRACE_THICKNESS, 3.0),  # ← 0.4 mm floor
        ]

    def validate(self, params):
        H  = config.BRIDGE_HEIGHT
        L  = config.BRIDGE_LENGTH
        n  = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]

        if 2 * tc >= H:
            return False

        panel_w = L / n
        if tp >= panel_w:
            return False

        return True

    def build_geometry(self, params):
        H  = config.BRIDGE_HEIGHT
        L  = config.BRIDGE_LENGTH
        m  = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]
        tb = params["brace_thickness"]

        n = 2 * m  
        inner_h = H - 2 * tc
        panel_w = (L - tp) / n

        geo = Geometry()

        # ── Chords ──
        geo.add_rectangle(x=0, y=H - tc, width=L, height=tc)
        geo.add_rectangle(x=0, y=0, width=L, height=tc)

        # ── Verticals ──
        for i in range(n + 1):
            geo.add_rectangle(x=i * panel_w, y=tc, width=tp, height=inner_h)

        # ── Diagonals (Howe: outward from centre) ──
        mid = n / 2.0
        
        # Berechnung der horizontalen Breite an der Basis, um tb senkrecht zu erzielen
        diag_len = math.sqrt(panel_w**2 + inner_h**2)
        w_horiz = (tb * diag_len) / inner_h

        for i in range(n):
            x_left  = i * panel_w
            x_right = x_left + panel_w

            if i < mid:
                # \ Typ (unten links nach oben rechts)
                skew = panel_w
                # Ausrichtung: Startet am linken Pfosten
                bx = x_left + (tp/2) - (w_horiz/2)
            else:
                # / Typ (unten rechts nach oben links)
                skew = -panel_w
                # Ausrichtung: Startet am rechten Pfosten
                bx = x_right + (tp/2) - (w_horiz/2)

            geo.add_parallelogram(
                x=bx,
                y=tc,
                width=w_horiz,
                height=inner_h,
                skew_x=skew
            )

        return geo

    def build_truss(self, params):
        H  = config.BRIDGE_HEIGHT
        L  = config.BRIDGE_LENGTH
        m  = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]
        tb = params["brace_thickness"]

        n = 2 * m   # ensure even number of panels

        depth = config.BRIDGE_DEPTH

        # Cross-sectional areas
        A_chord = tc * depth
        A_post  = tp * depth
        A_brace = tb * depth   # tb is now the perpendicular thickness

        panel_w = L / n

        nodes = []

        # bottom nodes
        for i in range(n + 1):
            nodes.append(Node(i * panel_w, 0.0))

        # top nodes
        for i in range(n + 1):
            nodes.append(Node(i * panel_w, H))

        def bottom(i):
            return i

        def top(i):
            return i + (n + 1)

        edges = []

        # bottom chord
        for i in range(n):
            edges.append(Edge(bottom(i), bottom(i + 1), A_chord))

        # top chord
        for i in range(n):
            edges.append(Edge(top(i), top(i + 1), A_chord))

        # verticals
        for i in range(n + 1):
            edges.append(Edge(bottom(i), top(i), A_post))

        # Howe diagonals (outward from centre)
        mid = n / 2.0
        for i in range(n):
            if i < mid:
                # left half: bottom-left → top-right
                edges.append(Edge(bottom(i), top(i + 1), A_brace))
            else:
                # right half: bottom-right → top-left
                edges.append(Edge(bottom(i + 1), top(i), A_brace))

        return Truss(nodes, edges)
