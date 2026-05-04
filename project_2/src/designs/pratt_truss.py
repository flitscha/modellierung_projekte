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
import math
import config
from core.design import Design
from core.geometry import Geometry, Rectangle, Parallelogram
from core.parameter import IntParameter, FloatParameter


class PrattTrussDesign(Design):

    def __init__(self):
        self.name = "Pratt Truss"

    def parameter_space(self):
        return [
            IntParameter("num_panels",       2,  20),
            FloatParameter("chord_thickness", config.MIN_FEATURE_SIZE, 4.0),
            FloatParameter("post_thickness",  config.MIN_FEATURE_SIZE, 3.0),
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

        # At least one post fits per panel
        panel_w = L / n
        if tp >= panel_w:
            return False

        return True

    def build_geometry(self, params):
        H  = config.BRIDGE_HEIGHT
        L  = config.BRIDGE_LENGTH
        n  = params["num_panels"]
        tc = params["chord_thickness"]   # chord thickness
        tp = params["post_thickness"]
        tb = params["brace_thickness"]

        inner_h = H - 2 * tc             # height between chords
        panel_w = L / n

        shapes = []

        # ── Top chord ──────────────────────────────────────────────
        shapes.append(Rectangle(x=0, y=H - tc, width=L, height=tc))

        # ── Bottom chord ───────────────────────────────────────────
        shapes.append(Rectangle(x=0, y=0, width=L, height=tc))

        # ── Verticals (posts) at every panel boundary ──────────────
        for i in range(n + 1):
            x_post = i * panel_w - tp / 2
            x_post = max(0.0, min(x_post, L - tp))   # clamp to bridge
            shapes.append(Rectangle(
                x=x_post, y=tc, width=tp, height=inner_h
            ))

        # ── Diagonals (Pratt: inward toward centre) ────────────────
        mid = n / 2.0
        for i in range(n):
            x_left  = i * panel_w
            x_right = x_left + panel_w

            if i < mid:
                # Left half: diagonal goes from top-left to bottom-right  (\)
                # skew_x > 0 → top edge shifted right
                skew = panel_w
                bx   = x_left
            else:
                # Right half: diagonal goes from top-right to bottom-left (/)
                # skew_x < 0 → top edge shifted left
                skew = -panel_w
                bx   = x_right - tb   # anchor on the right post

            shapes.append(Parallelogram(
                x=bx,
                y=tc,
                width=tb,
                height=inner_h,
                skew_x=skew,
            ))

        return Geometry(shapes)