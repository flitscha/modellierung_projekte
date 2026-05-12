BRIDGE_LENGTH = 300.0  # 30 cm
BRIDGE_HEIGHT = 15.0  # 15 mm
# TODO: this should be the maximum height. The bridge is allowed to be thinner.

MIN_FEATURE_SIZE = 0.4  # mm

LOAD_FORCE = 5.0 * 9.81  # 5kg in Newton

MAX_DEFLECTION = 3.0  # mm

PLA_DENSITY = 1.24e-3  # g/mm³
BRIDGE_DEPTH = 50.0  # TODO: ask, what this value will be

# TODO: add material-specific values for PLA


# FEM Material defaults
FEM_ELASTIC_MODULUS_MPA: float = 2500.0
FEM_POISSON_RATIO: float = 0.35
FEM_AIR_STIFFNESS_FACTOR: float = 1e-4
FEM_BC_PENALTY: float = 1e30

# FEM Solver defaults
FEM_INITIAL_NX: int = 200
FEM_MAX_NX: int = 800
FEM_CONVERGENZ_TOL: float = 0.02
FEM_LOAD_SPREAD_NODES: int = 5 # distribute the load among FEM_LOAD_SPREAD_NODES nodes
