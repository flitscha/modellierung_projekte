BRIDGE_LENGTH = 300.0 # mm
BRIDGE_DEPTH = 50.0 # mm
BRIDGE_HEIGHT = 15.0 # mm
# NOTE: The project-task also allows bridges that are less high,
# but we only consider bridges that are exactly 15mm high

# The 3D printer can work with an accuracy of up to 0.4mm
MIN_FEATURE_SIZE = 0.4 # mm

# 5kg are placed in the middle of the bridge.
LOAD_FORCE = 5.0 * 9.81 # 5kg in Newton

# The bridge may bend by a maximum of 3mm
MAX_DEFLECTION = 3.0 # mm


# Material settings
PLA_DENSITY = 1.24e-3 # g/mm^3
PLA_ELASTIC_MODULUS_MPA: float = 3000.0 # PLA has an value in between 2000 and 3500
PLA_POISSON_RATIO: float = 0.35

# FEM Solver defaults
FEM_INITIAL_NX: int = 800
FEM_MAX_NX: int = 6000
FEM_CONVERGENZ_TOL: float = 0.02
FEM_LOAD_SPREAD_NODES: int = 5
