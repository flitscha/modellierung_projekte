from gui import app
from designs.naca4 import NACA4Design
from designs.bezier_design import BezierAirfoilDesign

DESIGNS = [
    NACA4Design(),
    BezierAirfoilDesign(),
]

if __name__ == "__main__":
    app.run(DESIGNS)
