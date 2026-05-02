import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from designs.ibeam import IBeamDesign
from gui import app

DESIGNS = [
    IBeamDesign(),
]

if __name__ == "__main__":
    app.run(DESIGNS)
