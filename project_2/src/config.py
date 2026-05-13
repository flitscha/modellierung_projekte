BRIDGE_LENGTH = 300.0  # 30 cm
BRIDGE_HEIGHT = 15.0  # 15 mm
# TODO: this should be the maximum height. The bridge is allowed to be thinner.

MIN_FEATURE_SIZE = 0.4  # mm

LOAD_FORCE = 5.0 * 9.81  # 5kg in Newton

MAX_DEFLECTION = 3.0  # mm

PLA_DENSITY = 1.24e-3  # g/mm³
BRIDGE_DEPTH = 30.0  # TODO: ask, what this value will be

# TODO: add material-specific values for PLA

# ── FEM Material defaults ────────────────────────────────────────────────────
FEM_ELASTIC_MODULUS_MPA: float = 2500.0   # E-Modul (z.B. Beton ~2500 MPa)
FEM_POISSON_RATIO: float = 0.35           # Querdehnzahl
FEM_POINT_LOAD_NEWTONS: float = 5.0 * 9.81  # Punktlast [N] (5 kg * g)

# ── FEM Solver defaults ──────────────────────────────────────────────────────
FEM_INITIAL_NX: int = 200                 # Startwert Gitterauflösung (x)
FEM_MAX_NX: int = 3000                     # Maximale Gitterauflösung (x)
FEM_CONVERGENZ_TOL: float = 0.02          # Relative Konvergenztoleranz (2%)
FEM_LOAD_SPREAD_NODES: int = 5            # Über wie viele Knoten die Last verteilt wird

# ── Numerische Stabilität ────────────────────────────────────────────────────
FEM_STIFFNESS_REGULARIZATION: float = 1e-8  # Kleiner Wert gegen singuläre Matrizen
