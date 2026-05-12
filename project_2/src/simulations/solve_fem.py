import numpy as np
from dataclasses import dataclass
from typing import Tuple, List
from scipy.interpolate import griddata

from skfem import *
from skfem.models.elasticity import linear_elasticity

from core.geometry import Geometry
import config


@dataclass
class FEMResult:
    nx: int
    ny: int
    length: float
    height: float
    cell_width: float
    cell_height: float
    material_mask: np.ndarray
    displacement_x: np.ndarray
    displacement_y: np.ndarray
    stress_11: np.ndarray
    stress_22: np.ndarray
    stress_12: np.ndarray
    max_deflection_mm: float
    von_mises_stress: np.ndarray


def solve_fem(
    geometry: Geometry,
    nx: int,
    ny: int,
    elastic_modulus_mpa: float = config.FEM_ELASTIC_MODULUS_MPA,
    poisson_ratio: float = config.FEM_POISSON_RATIO,
    mass_kg: float = 5.0,
) -> FEMResult:

    # 1. Dimensionen (in mm)
    min_x, min_y, max_x, max_y = geometry.clean_shape.bounds
    width = max_x - min_x
    height = max_y - min_y

    # 2. Mesh
    target_area = (width * height) / (nx * ny * 1.5)
    mesh = geometry.build_skfem_mesh(max_area=target_area)
    basis = Basis(mesh, ElementVector(ElementTriP1()))

    # 3. Material (Einheiten: N und mm -> MPa ist korrekt)
    E, nu = elastic_modulus_mpa, poisson_ratio
    mu = E / (2 * (1 + nu))
    lam = E * nu / ((1 + nu) * (1 - 2 * nu))

    # Steifigkeitsmatrix - wir berücksichtigen hier die Dicke (Tiefe) der Brücke
    # falls config.BRIDGE_DEPTH existiert, sonst wird 1mm angenommen.
    thickness = getattr(config, 'BRIDGE_DEPTH', 1.0)
    K = asm(linear_elasticity(lam, mu), basis) * thickness
    f = np.zeros(basis.N)

    # ------------------------------------------------------------
    # 4. LAST: 5 kg in Newton, verteilt auf einen Bereich
    # ------------------------------------------------------------
    total_force = mass_kg * 9.81  # F in Newton
    center_x = min_x + width / 2
    
    # Wir suchen Knoten an der Oberkante in einem 5% breiten Fenster
    load_dofs = basis.get_dofs(lambda x: 
        (np.abs(x[0] - center_x) <= 0.05 * width) & 
        (x[1] >= max_y - 0.5) # Kleiner Puffer für Mesh-Ungenauigkeit
    )

    force_indices = load_dofs.nodal["u^2"]
    if len(force_indices) > 0:
        # Die Kraft wird negativ (nach unten) auf die Knoten verteilt
        f[force_indices] = -total_force / len(force_indices)
    else:
        # Fallback: Wenn das Fenster zu klein war, nimm den höchsten Punkt am nächsten zur Mitte
        top_node_idx = np.argmin(np.abs(mesh.p[0] - center_x) + np.abs(mesh.p[1] - max_y))
        f[basis.nodal_dofs[1, top_node_idx]] = -total_force

# ------------------------------------------------------------
    # 5. RANDBEDINGUNG: Fest-Los-Lager mit Toleranzband
    # ------------------------------------------------------------
    eps = 0.1  # 0.1 mm Toleranz, um Randknoten sicher zu finden

    # Links: Festlager (X und Y gesperrt)
    dofs_left = basis.get_dofs(lambda x: x[0] <= min_x + eps)
    fixed_left = np.union1d(dofs_left.nodal["u^1"], dofs_left.nodal["u^2"])
    
    # Rechts: Loslager (nur Y gesperrt, damit X gleiten kann -> keine künstliche Spannung)
    dofs_right = basis.get_dofs(lambda x: x[0] >= max_x - eps)
    fixed_right = dofs_right.nodal["u^2"]
    
    fixed = np.union1d(fixed_left, fixed_right)

    # Sicherheits-Check: Falls keine Knoten gefunden wurden, bricht das System ab
    if len(fixed) == 0:
        raise ValueError(f"Keine Randknoten für Einspannung gefunden! Bereich: {min_x} bis {max_x}")

    u = solve(*condense(K, f, D=fixed))

    # ------------------------------------------------------------
    # 6. Grid output (unverändert)
    # ------------------------------------------------------------
    dx, dy = width / nx, height / ny
    from shapely.vectorized import contains
    grid_x, grid_y = np.meshgrid(
        np.linspace(min_x + dx/2, max_x - dx/2, nx),
        np.linspace(min_y + dy/2, max_y - dy/2, ny),
        indexing="ij"
    )

    mask = contains(geometry.clean_shape, grid_x, grid_y)
    pts = mesh.p.T
    ux_nodes = u[basis.nodal_dofs[0]]
    uy_nodes = u[basis.nodal_dofs[1]]

    ux = griddata(pts, ux_nodes, (grid_x, grid_y), fill_value=0)
    uy = griddata(pts, uy_nodes, (grid_x, grid_y), fill_value=0)

    ux[~mask] = 0
    uy[~mask] = 0

    return FEMResult(
        nx=nx, ny=ny,
        length=width, height=height,
        cell_width=dx, cell_height=dy,
        material_mask=mask,
        displacement_x=ux,
        displacement_y=uy,
        stress_11=np.zeros_like(ux),
        stress_22=np.zeros_like(ux),
        stress_12=np.zeros_like(ux),
        max_deflection_mm=float(np.max(np.abs(uy))),
        von_mises_stress=np.zeros_like(ux),
    )

def solve_fem_adaptive(
    geometry: Geometry,
    elastic_modulus_mpa: float = config.FEM_ELASTIC_MODULUS_MPA,
    poisson_ratio: float = config.FEM_POISSON_RATIO,
    point_load_newtons: float = config.LOAD_FORCE,
    initial_nx: int = config.FEM_INITIAL_NX,
    max_nx: int = config.FEM_MAX_NX,
    tol: float = config.FEM_CONVERGENZ_TOL,
) -> Tuple[FEMResult, List[Tuple[int, int, float]]]:

    history = []
    prev = None
    nx = initial_nx
    min_x, min_y, max_x, max_y = geometry.clean_shape.bounds
    length, height = max_x - min_x, max_y - min_y

    while nx <= max_nx:
        ny = max(4, round(nx * height / length))
        result = solve_fem(geometry, nx, ny, elastic_modulus_mpa, poisson_ratio, point_load_newtons)
        current = result.max_deflection_mm
        history.append((nx, ny, current))

        if prev is not None:
            rel = abs(current - prev) / (abs(prev) + 1e-12)
            if rel < tol:
                break

        prev = current
        nx = int(nx * 1.5)

    return result, history

def _create_visualization_mask(geometry, nx, ny, dx, dy, min_x, min_y):
    # Nutzt unser schnelles Shapely-contains für die GUI-Maske
    from shapely.vectorized import contains
    xs = np.linspace(min_x + dx/2, min_x + nx*dx - dx/2, nx)
    ys = np.linspace(min_y + dy/2, min_y + ny*dy - dy/2, ny)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    return contains(geometry.clean_shape, X, Y)

def _apply_load(basis, f, total_force, length, height, min_x, min_y):
    # Last in der Mitte oben
    top_center = basis.get_dofs(lambda x: 
                                (np.abs(x[0] - (min_x + length/2)) < 0.05 * length) & 
                                (x[1] > min_y + height - 1e-3)
                                )
    dofs = top_center.nodal["u^2"]
    if len(dofs) > 0:
        f[dofs] = -total_force / len(dofs)

def _gridify_displacement(mesh, u, nx, ny, dx, dy, mask, min_x, min_y):
    pts = mesh.p.T
    ux_nodes = u[basis.nodal_dofs[0]] if 'basis' in locals() else u[0::2]
    uy_nodes = u[basis.nodal_dofs[1]] if 'basis' in locals() else u[1::2]

    xs = np.linspace(min_x + dx/2, min_x + nx*dx - dx/2, nx)
    ys = np.linspace(min_y + dy/2, min_y + ny*dy - dy/2, ny)
    X, Y = np.meshgrid(xs, ys, indexing="ij")

    ux = griddata(pts, ux_nodes, (X, Y), fill_value=0.0)
    uy = griddata(pts, uy_nodes, (X, Y), fill_value=0.0)

    ux[~mask] = 0.0
    uy[~mask] = 0.0
    return ux, uy
