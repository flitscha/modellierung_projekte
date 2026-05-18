import config
from core.design import Design
from core.geometry import Geometry, Parallelogram, Rectangle
from core.parameter import FloatParameter, IntParameter
from core.truss import Truss, Edge, Node
import math


class HoweTrussDesign(Design):

    def __init__(self):
        self.name = "Howe Truss"

    def parameter_space(self):
        return [
            IntParameter("num_panels", 2, 20),
            FloatParameter("chord_thickness", config.MIN_FEATURE_SIZE, 4.0),
            FloatParameter("post_thickness", config.MIN_FEATURE_SIZE, 3.0),
            FloatParameter("brace_thickness", config.MIN_FEATURE_SIZE, 3.0),
        ]

    def validate(self, params):
        H = config.BRIDGE_HEIGHT
        L = config.BRIDGE_LENGTH
        n = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]

        if 2 * tc >= H:
            return False

        panel_w = L / n
        if tp >= panel_w:
            return False

        return True

    def build_geometry(self, params):
        H = config.BRIDGE_HEIGHT
        L = config.BRIDGE_LENGTH
        m = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]
        tb = params["brace_thickness"] # perpendicular thickness

        n = 2 * m # ensure even number of panels

        inner_h = H - 2 * tc
        panel_w = (L - tp) / n

        shapes = []

        # Top chord
        shapes.append(Rectangle(x=0, y=H - tc, width=L, height=tc))

        # Bottom chord
        shapes.append(Rectangle(x=0, y=0, width=L, height=tc))

        # Verticals (posts) at every panel boundary
        for i in range(n + 1):
            x_post = i * panel_w
            shapes.append(Rectangle(
                x=x_post, y=tc, width=tp, height=inner_h
            ))

        # Diagonals (Howe: outward from centre)
        mid = n / 2.0
        for i in range(n):
            x_left = i * panel_w
            x_right = x_left + panel_w

            if i < mid:
                # Left half: diagonal goes from bottom-left to top-right
                # skew_x > 0 -> top edge shifted right
                skew = panel_w
                bx = x_left
            else:
                # Right half: diagonal goes from bottom-right to top-left
                # skew_x < 0 -> top edge shifted left
                skew = -panel_w 
                hor_w = tb * math.sqrt(skew**2 + inner_h**2)/inner_h
                bx = x_right - hor_w + tp

            shapes.append(Parallelogram(
                x=bx,
                y=tc,
                thickness=tb,
                height=inner_h,
                skew_x=skew,
            ))

        return Geometry(shapes)

    def build_truss(self, params):
        H = config.BRIDGE_HEIGHT
        L = config.BRIDGE_LENGTH
        m = params["num_panels"]
        tc = params["chord_thickness"]
        tp = params["post_thickness"]
        tb = params["brace_thickness"]

        n = 2 * m # ensure even number of panels

        depth = config.BRIDGE_DEPTH

        # Cross-sectional areas
        A_chord = tc * depth
        A_post = tp * depth
        A_brace = tb * depth # tb is the perpendicular thickness

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
                # left half: bottom-left -> top-right
                edges.append(Edge(bottom(i), top(i + 1), A_brace))
            else:
                # right half: bottom-right -> top-left
                edges.append(Edge(bottom(i + 1), top(i), A_brace))

        return Truss(nodes, edges)

