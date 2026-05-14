from dataclasses import dataclass
from typing import Tuple, List

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix, coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.sparse import eye as speye

from core.geometry import Geometry
from config import (
    BRIDGE_DEPTH,
    PLA_ELASTIC_MODULUS_MPA,
    PLA_POISSON_RATIO,
    LOAD_FORCE,
    FEM_INITIAL_NX,
    FEM_MAX_NX,
    FEM_CONVERGENZ_TOL,
    FEM_LOAD_SPREAD_NODES,
)


# Result container for a completed FEM simulation.
@dataclass
class FEMResult:
    nx: int
    ny: int
    length: float
    height: float
    cell_width: float
    cell_height: float

    material_mask: np.ndarray # (nx, ny) bool - True where material exists

    displacement_x: np.ndarray # (nx, ny) horizontal displacement per cell
    displacement_y: np.ndarray # (nx, ny) vertical displacement per cell

    stress_11: np.ndarray # (nx, ny) normal stress in x
    stress_22: np.ndarray # (nx, ny) normal stress in y
    stress_12: np.ndarray # (nx, ny) shear stress

    max_deflection_mm: float
    von_mises_stress: np.ndarray # (nx, ny) Von Mises equivalent stress


def solve_fem(
    geometry: Geometry,
    nx: int,
    ny: int,
    elastic_modulus_mpa: float = PLA_ELASTIC_MODULUS_MPA,
    poisson_ratio: float = PLA_POISSON_RATIO,
    point_load_newtons: float = LOAD_FORCE,
) -> FEMResult:
    """
    The geometry is rasterized into an (nx x ny) grid of quad elements.
    Only cells that contain material are added to the stiffness matrix
    """

    length, height = _get_bridge_dimensions(geometry)
    dx, dy = length / nx, height / ny

    D = _plane_stress_material_matrix(elastic_modulus_mpa, poisson_ratio)

    material_mask = _build_material_mask(geometry, nx, ny, dx, dy)

    K, f = _assemble_global_system(material_mask, nx, ny, dx, dy, D)
    K = _regularize(K)
    K = _apply_boundary_conditions(K, f, nx, ny)
    _apply_point_load(f, nx, ny, point_load_newtons)

    u = _solve_linear_system(K, f)

    Ux, Uy, s11, s22, s12 = _extract_fields(u, material_mask, nx, ny, dx, dy, D)
    von_mises = _compute_von_mises(s11, s22, s12, material_mask)

    return FEMResult(
        nx=nx, ny=ny,
        length=length, height=height,
        cell_width=dx, cell_height=dy,
        material_mask=material_mask,
        displacement_x=Ux, displacement_y=Uy,
        stress_11=s11, stress_22=s22, stress_12=s12,
        max_deflection_mm=float(np.max(np.abs(Uy[material_mask]))),
        von_mises_stress=von_mises,
    )


def solve_fem_adaptive(
    geometry: Geometry,
    elastic_modulus_mpa: float = PLA_ELASTIC_MODULUS_MPA,
    poisson_ratio: float = PLA_POISSON_RATIO,
    point_load_newtons: float = LOAD_FORCE,
    initial_nx: int = FEM_INITIAL_NX,
    max_nx: int = FEM_MAX_NX,
    tol: float = FEM_CONVERGENZ_TOL,
) -> Tuple[FEMResult, List[Tuple[int, int, float]]]:
    """
    Adaptive solver. Repeats the simulation with increasing grid resolution.
    Stops early when the max deflection changes by less than 'tol'
    """

    length, height = _get_bridge_dimensions(geometry)
    history: List[Tuple[int, int, float]] = []
    prev_deflection = None
    nx = initial_nx

    while nx <= max_nx:
        # Pick ny so cells stay roughly square.
        ny = max(4, round(nx * height / length))

        result = solve_fem(geometry, nx, ny, elastic_modulus_mpa, poisson_ratio, point_load_newtons)
        deflection = result.max_deflection_mm
        history.append((nx, ny, deflection))

        if prev_deflection is not None:
            relative_change = abs(deflection - prev_deflection) / (abs(prev_deflection) + 1e-12)
            if relative_change < tol:
                break

        prev_deflection = deflection
        nx = int(nx * 1.5)

    return result, history


def _get_bridge_dimensions(geometry: Geometry) -> Tuple[float, float]:
    """
    Returns (length, height) from the geometry bounding box.
    """
    min_x, min_y, max_x, max_y = geometry.bounding_box()
    return max_x - min_x, max_y - min_y


def _build_material_mask(geometry: Geometry, nx: int, ny: int, dx: float, dy: float) -> np.ndarray:
    """
    Returns a bool mask of shape (nx, ny).
    A cell is True if its center point is inside the geometry.
    """
    xs = (np.arange(nx) + 0.5) * dx # (nx,)
    ys = (np.arange(ny) + 0.5) * dy # (ny,)

    # calculate all combinations of xs and ys, using np.meshgrid
    xs_grid, ys_grid = np.meshgrid(xs, ys, indexing='ij') # (nx, ny)

    # like this, everything is vectorized. We avoid slow python-loops
    return geometry.contains(xs_grid, ys_grid).astype(bool)


def _plane_stress_material_matrix(E: float, nu: float) -> np.ndarray:
    """
    Builds the plane stress material matrix D.
    D maps strains to stresses: stress = D @ strain.
    Assumes isotropic linear elastic material.
    """
    return (E / (1 - nu**2)) * np.array([
        [1, nu, 0],
        [nu, 1, 0],
        [0, 0, (1 - nu) / 2],
    ])


def _quad4_B_matrix_at_gauss_point(xi: float, eta: float, dx: float, dy: float) -> np.ndarray:
    """
    Computes the B matrix at a single Gauss point (xi, eta).
    B maps element node displacements to strains: strain = B @ u_element.
    Shape is (3, 8) for a Quad4 element with 4 nodes and 2 DOFs each.
    """
    # Shape function derivatives in natural coordinates.
    dN_dxi  = 0.25 * np.array([[-(1-eta), (1-eta), (1+eta), -(1+eta)]])
    dN_deta = 0.25 * np.array([[-(1-xi), -(1+xi), (1+xi), (1-xi)]])

    # Jacobian maps natural coords to physical coords.
    J = np.array([[dx/2, 0], [0, dy/2]])
    dN_xy = np.linalg.inv(J) @ np.vstack((dN_dxi, dN_deta))  # (2, 4)

    # Assemble B using Voigt notation: [eps_xx, eps_yy, gamma_xy].
    B = np.zeros((3, 8))
    for i in range(4):
        B[0, 2*i]     = dN_xy[0, i] # eps_xx = du/dx
        B[1, 2*i + 1] = dN_xy[1, i] # eps_yy = dv/dy
        B[2, 2*i]     = dN_xy[1, i] # gamma_xy = du/dy + dv/dx
        B[2, 2*i + 1] = dN_xy[0, i]
    return B


def _quad4_element_stiffness(dx: float, dy: float, D: np.ndarray) -> np.ndarray:
    """
    Computes the (8, 8) element stiffness matrix for one Quad4 cell.
    Uses 2x2 Gauss integration: Ke = sum_gp( B^T D B detJ ).
    """
    gauss_points = [-1 / np.sqrt(3), 1 / np.sqrt(3)]
    Ke = np.zeros((8, 8))
    detJ = (dx * dy) / 4 # constant for an axis-aligned rectangle

    for xi in gauss_points:
        for eta in gauss_points:
            B = _quad4_B_matrix_at_gauss_point(xi, eta, dx, dy)
            Ke += B.T @ D @ B * detJ * BRIDGE_DEPTH # Gauss weight is 1

    return Ke


def _quad4_B_matrix_cell_center(dx: float, dy: float) -> np.ndarray:
    """
    B matrix evaluated at the cell center (xi=0, eta=0).
    Used for stress recovery after solving. Gives constant strain per element.
    """
    return 0.5 * np.array([
        [-1/dx, 0, 1/dx, 0, 1/dx, 0, -1/dx, 0],
        [0, -1/dy, 0, -1/dy, 0, 1/dy, 0, 1/dy],
        [-1/dy, -1/dx, -1/dy, 1/dx, 1/dy, 1/dx, 1/dy, -1/dx],
    ])


def _node_index(i: int, j: int, nnx: int) -> int:
    # Returns the global node index for grid position (i, j).
    return j * nnx + i


def _dof_index(node: int, component: int) -> int:
    # Returns the global DOF index. component: 0 = u (horizontal), 1 = v (vertical).
    return 2 * node + component


def _assemble_global_system(
    material_mask: np.ndarray, nx: int, ny: int, dx: float, dy: float, D: np.ndarray
) -> Tuple[csr_matrix, np.ndarray]:
    """
    Assembles the global stiffness matrix K and load vector f.
    """
    nnx   = nx + 1
    n_dof = 2 * nnx * (ny + 1)
    f = np.zeros(n_dof)

    Ke = _quad4_element_stiffness(dx, dy, D) # same for every cell

    # Indices of all material cells.
    ci, cj = np.where(material_mask) # ci = x-index, cj = y-index
    n_elem = len(ci)

    if n_elem == 0:
        return csr_matrix((n_dof, n_dof)), f

    # Global node indices for the four corners of each element (n_elem each).
    n0 = cj * nnx + ci # bottom-left  (i, j)
    n1 = cj * nnx + (ci + 1) # bottom-right (i+1, j)
    n2 = (cj + 1) * nnx + (ci + 1) # top-right (i+1, j+1)
    n3 = (cj + 1) * nnx + ci # top-left (i, j+1)

    # Element DOF array, shape (n_elem, 8): [u0,v0, u1,v1, u2,v2, u3,v3]
    elem_dofs = np.stack([
        2*n0, 2*n0+1, 2*n1, 2*n1+1,
        2*n2, 2*n2+1, 2*n3, 2*n3+1,
    ], axis=1) # (n_elem, 8)

    # Build COO triplets for all 8x8 Ke entries across all elements.
    # rows_e[e,a,b] = global row DOF of element e for Ke entry (a,b).
    rows_e = np.array(np.broadcast_to(elem_dofs[:, :, np.newaxis], (n_elem, 8, 8))).ravel()
    cols_e = np.array(np.broadcast_to(elem_dofs[:, np.newaxis, :], (n_elem, 8, 8))).ravel()
    vals_e = np.array(np.broadcast_to(Ke[np.newaxis, :, :], (n_elem, 8, 8))).ravel()

    K = coo_matrix((vals_e, (rows_e, cols_e)), shape=(n_dof, n_dof))
    return K.tocsr(), f


def _regularize(K: csr_matrix) -> csr_matrix:
    # Adds a small value to the diagonal to avoid singular matrices
    return K + 1e-8 * speye(K.shape[0], format='csr')


def _fix_dof(K: lil_matrix, f: np.ndarray, idx: int, value: float = 0.0) -> None:
    """
    Sets a single DOF to a fixed value (Dirichlet boundary condition).
    The row is replaced with an identity row and f[idx] is set to value.
    """
    K[idx, :] = 0
    K[idx, idx] = 1
    f[idx] = value


def _apply_boundary_conditions(K: csr_matrix, f: np.ndarray, nx: int, ny: int) -> csr_matrix:
    """
    Fixes both bottom corner nodes (u=0, v=0).
    We can do it this way because in our bridge-designs, the corners are always solid
    """
    nnx = nx + 1
    K = K.tolil()

    for corner_i in [0, nx]:
        n = _node_index(corner_i, 0, nnx)
        _fix_dof(K, f, _dof_index(n, 0))
        _fix_dof(K, f, _dof_index(n, 1))

    return K.tocsr()



def _apply_point_load(f: np.ndarray, nx: int, ny: int, total_load_n: float) -> None:
    # Applies a downward point load at the bridge center top
    nnx = nx + 1
    mid = nx // 2
    half = FEM_LOAD_SPREAD_NODES // 2
    load_per_node = total_load_n / FEM_LOAD_SPREAD_NODES

    for i in range(mid - half, mid - half + FEM_LOAD_SPREAD_NODES):
        n = _node_index(i, ny, nnx)
        f[_dof_index(n, 1)] -= load_per_node


def _solve_linear_system(K: csr_matrix, f: np.ndarray) -> np.ndarray:
    """
    Solves K @ u = f using a sparse direct solver.
    Raises an error if the result contains NaN
    """
    u = spsolve(K, f)
    if not np.all(np.isfinite(u)):
        raise RuntimeError(
            "FEM solver produced NaN. "
            "The stiffness matrix is likely singular. "
            "Check that the geometry is connected and boundary conditions are correct."
        )
    return u


def _extract_fields(
    u: np.ndarray,
    material_mask: np.ndarray,
    nx: int, ny: int,
    dx: float, dy: float,
    D: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Extracts displacement and stress fields from the solution vector u.
    Displacement per cell is the average of its four corner node values.
    Stress is computed as: stress = D @ B @ u_element.
    """

    nnx = nx + 1
    B = _quad4_B_matrix_cell_center(dx, dy) # (3, 8)

    Ux = np.zeros((nx, ny))
    Uy = np.zeros((nx, ny))
    s11 = np.zeros((nx, ny))
    s22 = np.zeros((nx, ny))
    s12 = np.zeros((nx, ny))

    ci, cj = np.where(material_mask)

    # Node indices for the four corners of each material cell.
    n0 = cj * nnx + ci
    n1 = cj * nnx + (ci + 1)
    n2 = (cj + 1) * nnx + (ci + 1)
    n3 = (cj + 1) * nnx + ci

    # Average nodal displacement per cell.
    Ux[ci, cj] = (u[2*n0] + u[2*n1] + u[2*n2] + u[2*n3]) / 4.0
    Uy[ci, cj] = (u[2*n0+1] + u[2*n1+1] + u[2*n2+1] + u[2*n3+1]) / 4.0

    # Element displacement vectors: (n_elem, 8)
    ue = np.stack([
        u[2*n0], u[2*n0+1],
        u[2*n1], u[2*n1+1],
        u[2*n2], u[2*n2+1],
        u[2*n3], u[2*n3+1],
    ], axis=1)

    # Stress for all elements at once: (n_elem, 3) = (n_elem, 8) @ (8, 3)
    stress = ue @ (D @ B).T

    s11[ci, cj] = stress[:, 0]
    s22[ci, cj] = stress[:, 1]
    s12[ci, cj] = stress[:, 2]

    return Ux, Uy, s11, s22, s12


def _compute_von_mises(
    s11: np.ndarray, s22: np.ndarray, s12: np.ndarray, material_mask: np.ndarray
) -> np.ndarray:
    """
    Computes Von Mises stress from the stress components.
    Formula: sqrt(s11^2 - s11*s22 + s22^2 + 3*s12^2).
    """
    vm = np.sqrt(np.maximum(s11**2 - s11 * s22 + s22**2 + 3 * s12**2, 0.0))
    vm[~material_mask] = 0.0 # Non-material cells are set to zero.
    return vm

