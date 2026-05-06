"""
Pratt Truss Design
==================
Topology: Two horizontal chords (top + bottom plate) connected by
          vertical posts and diagonal braces.

Pratt convention: diagonals point INWARD toward the centre span,
i.e. they slope from the outer top-chord toward the inner bottom-chord.
Under a centre load this puts the diagonals in tension (efficient for PLA).

Parameters
----------
num_panels      : int   – number of truss panels (spaces between verticals)
chord_thickness : float – height of top and bottom horizontal plate  [mm]
post_thickness  : float – width of vertical posts                    [mm]
brace_thickness : float – width of diagonal braces                   [mm]
"""

import config
from core.design import Design
from core.geometry import Geometry, Rectangle, Parallelogram
from core.parameter import IntParameter, FloatParameter
from core.truss import Node, Edge, Truss


class PrattTrussDesign(Design):

    def __init__(self):
        self.name = "Pratt Truss"

    def parameter_space(self):
        return [
            IntParameter("num_panels", 1, 50),
            FloatParameter("chord_thickness", config.MIN_FEATURE_SIZE, 4.0),
            FloatParameter("post_thickness", config.MIN_FEATURE_SIZE, 3.0),
            FloatParameter("brace_thickness", config.MIN_FEATURE_SIZE, 3.0),
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
        n  = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]
        tb = params["brace_thickness"]

        inner_h = H - 2 * tc
        panel_w = (L - tp) / n

        shapes = []

        # ── Top chord ──────────────────────────────────────────────
        shapes.append(Rectangle(x=0, y=H - tc, width=L, height=tc))

        # ── Bottom chord ───────────────────────────────────────────
        shapes.append(Rectangle(x=0, y=0, width=L, height=tc))

        # ── Verticals (posts) at every panel boundary ──────────────
        for i in range(n+1):
            x_post = i * panel_w
            shapes.append(Rectangle(
                x=x_post, y=tc, width=tp, height=inner_h
            ))

        # ── Diagonals (Howe: outward from centre) ──────────────────
        mid = n / 2.0
        for i in range(n):
            x_left  = i * panel_w
            x_right = x_left + panel_w

            if i < mid:
                # Left half: diagonal goes from bottom-right to top-left (/)
                # skew_x < 0 → top edge shifted left
                skew = -panel_w + tb - tp
                bx   = x_right + tp - tb
            else:
                # Right half: diagonal goes from bottom-right to top-left (\)
                # skew_x > 0 → top edge shifted right
                skew = panel_w - tb + tp
                bx   = x_left

            shapes.append(Parallelogram(
                x=bx,
                y=tc,
                width=tb,
                height=inner_h,
                skew_x=skew,
            ))

        return Geometry(shapes)


    def build_truss(self, params):
        H  = config.BRIDGE_HEIGHT
        L  = config.BRIDGE_LENGTH
        n  = params["num_panels"]

        tc = params["chord_thickness"]
        tp = params["post_thickness"]
        tb = params["brace_thickness"]

        depth = config.BRIDGE_DEPTH

        # Cross-sectional areas
        A_chord = tc * depth
        A_post  = tp * depth
        A_brace = tb * depth

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
            edges.append(Edge(bottom(i), bottom(i+1), A_chord))

        # top chord
        for i in range(n):
            edges.append(Edge(top(i), top(i+1), A_chord))

        # verticals
        for i in range(n + 1):
            edges.append(Edge(bottom(i), top(i), A_post))

        # pratt diagonals
        mid = n / 2.0
        for i in range(n):
            if i < mid:
                # left half: bottom(i+1) -> top(i)
                edges.append(Edge(bottom(i+1), top(i), A_brace))
            else:
                # right half: bottom(i) -> top(i+1)
                edges.append(Edge(bottom(i), top(i+1), A_brace))

        return Truss(nodes, edges)

