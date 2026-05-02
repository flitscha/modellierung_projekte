import config
from core.design import Design
from core.geometry import Geometry, Rectangle
from core.parameter import IntParameter, FloatParameter


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

        shapes = []

        # upper plate
        shapes.append(Rectangle(
            x=0,
            y=H - t_p,
            width=L,
            height=t_p
        ))

        # lower plate
        shapes.append(Rectangle(
            x=0,
            y=0,
            width=L,
            height=t_p
        ))

        # vertical beams
        spacing = (L - t_b) / (n - 1)
        start_x = 0

        for i in range(n):
            x_pos = start_x + i * spacing

            shapes.append(Rectangle(
                x=x_pos,
                y=t_p,
                width=t_b,
                height=H - 2 * t_p
            ))

        return Geometry(shapes)

