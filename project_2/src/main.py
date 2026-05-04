import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from designs.ibeam import IBeamDesign
from designs.pratt_truss import PrattTrussDesign
from designs.howe_truss import HoweTrussDesign
from gui import app

DESIGNS = [
    IBeamDesign(),
    PrattTrussDesign(),
    HoweTrussDesign(),
]

if __name__ == "__main__":
    app.run(DESIGNS)
