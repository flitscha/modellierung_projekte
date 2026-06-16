from __future__ import annotations
import numpy as np
import config
from core.design import Design
from core.airfoil import Airfoil
from core.parameter import FloatParameter

def _evaluate_bezier(p0, p1, p2, p3, n=100):
    """Calculate cubic Bezier-curve for n points"""
    t = np.linspace(0, 1, n)[:, None]
    xy = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
    return xy



class BezierAirfoilDesign(Design):
    def __init__(self):
        self.name = "Advanced Bezier Airfoil"

    def parameter_space(self):
        return [
            # Top side
            FloatParameter("top_ctrl1_y", 0.02, 0.32),
            FloatParameter("top_ctrl2_x", 0.15, 0.85),
            FloatParameter("top_ctrl2_y", 0.04, 0.45),

            # bottom side
            FloatParameter("bot_ctrl1_y", -0.22, -0.07),
            FloatParameter("bot_ctrl2_x", 0.15, 0.85),
            FloatParameter("bot_ctrl2_y", -0.15, 0.20),
        ]

    def default_parameters(self):
        return {
            "top_ctrl1_y": 0.11,
            "top_ctrl2_x": 0.30,
            "top_ctrl2_y": 0.14,

            "bot_ctrl1_y": -0.07,
            "bot_ctrl2_x": 0.33,
            "bot_ctrl2_y": -0.04
        }

    def validate(self, params) -> bool:
        # Basic ordering at LE
        if params["top_ctrl1_y"] <= params["bot_ctrl1_y"] + 0.005:
            return False

        if params["top_ctrl2_y"] <= params["bot_ctrl2_y"] + 0.005:
            return False

        t = np.linspace(0, 1, 60)[:, None]

        le = np.array([0.0, 0.0])
        te = np.array([1.0, 0.0])

        p1_top = np.array([0.0, params["top_ctrl1_y"]])
        p2_top = np.array([params["top_ctrl2_x"], params["top_ctrl2_y"]])
        top = (1-t)**3 * le + 3*(1-t)**2*t*p1_top + 3*(1-t)*t**2*p2_top + t**3*te

        p1_bot = np.array([0.0, params["bot_ctrl1_y"]])
        p2_bot = np.array([params["bot_ctrl2_x"], params["bot_ctrl2_y"]])
        bot = (1-t)**3 * le + 3*(1-t)**2*t*p1_bot + 3*(1-t)*t**2*p2_bot + t**3*te

        y_top = top[:, 1]
        y_bot = bot[:, 1]

        thickness = y_top - y_bot
        thickness2 = thickness[1:-1]
        print(thickness)
        #valid = (t[:, 0] > 0.02) & (t[:, 0] < 0.98)

        #thickness_core = thickness[valid]

        if np.min(thickness2) < 0.007:
            return False

        if np.min(thickness) < 0.0:
            return False

        # softer thickness cap
        if np.max(thickness) > 0.20:
            return False

        camber = 0.5 * (y_top + y_bot)
        if np.max(np.abs(camber)) > 0.15:
            return False

        return True

    def build_airfoil(self, params) -> Airfoil:
        # Verwende Panel-Anzahl aus der Config für Konsistenz mit NACA
        n_side = (config.N_PANELS // 2) + 1 

        le = np.array([0.0, 0.0])
        te = np.array([1.0, 0.0])

        # --- OBERSEITE ---
        p1_top = np.array([0.0, params["top_ctrl1_y"]])
        p2_top = np.array([params["top_ctrl2_x"], params["top_ctrl2_y"]])
        upper_curve = _evaluate_bezier(le, p1_top, p2_top, te, n_side)

        # --- UNTERSEITE ---
        p1_bot = np.array([0.0, params["bot_ctrl1_y"]])
        p2_bot = np.array([params["bot_ctrl2_x"], params["bot_ctrl2_y"]])
        lower_curve = _evaluate_bezier(le, p1_bot, p2_bot, te, n_side)

        # In Selig-Format bringen (Oberseite von TE -> LE, Unterseite von LE+1 -> TE)
        upper_selig = upper_curve[::-1]
        lower_selig = lower_curve[1:]

        coords = np.vstack([upper_selig, lower_selig])
        return Airfoil(coords, name="Bezier-Optimized")
