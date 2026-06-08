from gui import app
from designs.naca4 import NACA4Design

DESIGNS = [
    NACA4Design(),
]

if __name__ == "__main__":
    app.run(DESIGNS)
