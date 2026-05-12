import config
from core.design import Design
from core.geometry import Geometry
from core.parameter import IntParameter, FloatParameter
from core.truss import Truss, Node, Edge


class IBeamDesign(Design):

    def __init__(self):
        self.name = "I-Beam"

    def parameter_space(self):
        return [
            IntParameter("num_beams", 2, 50),
            FloatParameter("beam_thickness", config.MIN_FEATURE_SIZE, 3.0),
            FloatParameter("plate_thickness", config.MIN_FEATURE_SIZE, 3.0),
        ]

    def validate(self, params):
        H = config.BRIDGE_HEIGHT
        L = config.BRIDGE_LENGTH

        n = params["num_beams"]
        t_b = params["beam_thickness"]
        t_p = params["plate_thickness"]

        if 2 * t_p >= H:
            return False

        if n * t_b >= L:
            return False

        return True


    def build_geometry(self, params):
        H = config.BRIDGE_HEIGHT
        L = config.BRIDGE_LENGTH

        n = params["num_beams"]
        t_b = params["beam_thickness"]
        t_p = params["plate_thickness"]

        geo = Geometry()

        # top plate
        geo.add_rectangle(
            x=0,
            y=H - t_p,
            width=L,
            height=t_p
        )

        # bottom plate
        geo.add_rectangle(
            x=0,
            y=0,
            width=L,
            height=t_p
        )

        # vertical beams
        spacing = (L - t_b) / (n - 1)
        for i in range(n):
            x_pos = i * spacing
            geo.add_rectangle(
                x=x_pos,
                y=t_p,
                width=t_b,
                height=H - 2 * t_p
            )

        return geo


    def build_truss(self, params):
        H = config.BRIDGE_HEIGHT
        L = config.BRIDGE_LENGTH

        n   = params["num_beams"]
        t_b = params["beam_thickness"]
        t_p = params["plate_thickness"]

        depth = config.BRIDGE_DEPTH

        # Cross-sectional areas
        A_plate = t_p * depth
        A_web   = t_b * depth

        nodes = []

        spacing = (L - t_b) / (n - 1)

        # bottom nodes
        for i in range(n):
            x = i * spacing
            nodes.append(Node(x, 0.0))

        # top nodes
        for i in range(n):
            x = i * spacing
            nodes.append(Node(x, H))

        def bottom(i):
            return i

        def top(i):
            return i + n

        edges = []

        # bottom chord
        for i in range(n - 1):
            edges.append(Edge(bottom(i), bottom(i + 1), A_plate))

        # top chord
        for i in range(n - 1):
            edges.append(Edge(top(i), top(i + 1), A_plate))

        # vertical beams (webs)
        for i in range(n):
            edges.append(Edge(bottom(i), top(i), A_web))

        return Truss(nodes, edges)
