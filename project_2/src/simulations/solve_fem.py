from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve

from core.geometry import Geometry
from config import BRIDGE_DEPTH

# TODO: understand this code

# ──────────────────────────────────────────────────────────────────────────────
# Result container (unchanged interface!)
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Main FEM solver (Q4 elements, plane stress)
# ──────────────────────────────────────────────────────────────────────────────

def solve_fem(
    geometry: Geometry,
    nx: int,
    ny: int,
    elastic_modulus_mpa: float = 2500.0,
    poisson_ratio: float = 0.35,
    point_load_newtons: float = 5.0 * 9.81,
) -> FEMResult:

    length, height = _get_bridge_dimensions(geometry)

    dx = length / nx
    dy = height / ny

    # ── Material matrix (plane stress) ────────────────────────────────────────
    E = elastic_modulus_mpa
    nu = poisson_ratio

    D = (E / (1 - nu**2)) * np.array([
        [1, nu, 0],
        [nu, 1, 0],
        [0, 0, (1 - nu) / 2]
    ])

    # ── Nodes ────────────────────────────────────────────────────────────────
    nnx = nx + 1
    nny = ny + 1
    n_nodes = nnx * nny
    n_dof = 2 * n_nodes

    def node(i, j):
        return j * nnx + i

    def dof(n, comp):
        return 2 * n + comp  # 0=u, 1=v

    # ── Geometry mask (cells) ────────────────────────────────────────────────
    xs = np.linspace(dx/2, length - dx/2, nx)
    ys = np.linspace(dy/2, height - dy/2, ny)

    material = np.zeros((nx, ny), dtype=bool)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            material[i, j] = geometry.contains(x, y)

    # ── Stiffness matrix ─────────────────────────────────────────────────────
    K = lil_matrix((n_dof, n_dof))
    f = np.zeros(n_dof)

    # ── Element stiffness (constant for all cells) ───────────────────────────
    Ke = _quad4_element_stiffness(dx, dy, D)

    # ── Assembly ─────────────────────────────────────────────────────────────
    for i in range(nx):
        for j in range(ny):
            if not material[i, j]:
                continue

            n0 = node(i, j)
            n1 = node(i+1, j)
            n2 = node(i+1, j+1)
            n3 = node(i, j+1)

            nodes = [n0, n1, n2, n3]

            dofs = []
            for n in nodes:
                dofs += [dof(n, 0), dof(n, 1)]

            for a in range(8):
                for b in range(8):
                    K[dofs[a], dofs[b]] += Ke[a, b]

    K = K.tocsr()
    K = K + 1e-8 * csr_matrix(np.eye(K.shape[0]))

    # ── Boundary conditions ──────────────────────────────────────────────────
    # left bottom: u=v=0
    n_left = node(0, 0)
    _fix_dof(K, f, dof(n_left, 0), 0.0)
    _fix_dof(K, f, dof(n_left, 1), 0.0)

    # right bottom: u=v=0
    n_right = node(nx, 0)
    _fix_dof(K, f, dof(n_right, 0), 0.0)
    _fix_dof(K, f, dof(n_right, 1), 0.0)


    # ── Load (mid bottom node) ───────────────────────────────────────────────
    mid = nx // 2

    for i in range(mid - 2, mid + 3): # distribute the weight a bit (the computation gets more stable)
        n = node(i, 0)
        f[dof(n, 1)] -= point_load_newtons / 5

    # ── Solve ────────────────────────────────────────────────────────────────
    u = spsolve(csr_matrix(K), f)

    if not np.all(np.isfinite(u)):
        raise RuntimeError("FEM solver produced NaNs (matrix likely singular)")

    # ── Extract fields ───────────────────────────────────────────────────────
    Ux = np.zeros((nx, ny))
    Uy = np.zeros((nx, ny))

    s11 = np.zeros((nx, ny))
    s22 = np.zeros((nx, ny))
    s12 = np.zeros((nx, ny))

    for i in range(nx):
        for j in range(ny):
            if not material[i, j]:
                continue

            n0 = node(i, j)
            n1 = node(i+1, j)
            n2 = node(i+1, j+1)
            n3 = node(i, j+1)

            nodes = [n0, n1, n2, n3]

            ue = np.zeros(8)
            for k, n in enumerate(nodes):
                ue[2*k]   = u[dof(n, 0)]
                ue[2*k+1] = u[dof(n, 1)]

            B = _quad4_B_matrix(dx, dy)
            strain = B @ ue
            stress = D @ strain

            s11[i, j], s22[i, j], s12[i, j] = stress

            Ux[i, j] = np.mean([u[dof(n, 0)] for n in nodes])
            Uy[i, j] = np.mean([u[dof(n, 1)] for n in nodes])

    von_mises = np.sqrt(s11**2 - s11*s22 + s22**2 + 3*s12**2)
    von_mises[~material] = 0

    max_deflection = float(np.max(np.abs(Uy)))

    return FEMResult(
        nx, ny,
        length, height,
        dx, dy,
        material,
        Ux, Uy,
        s11, s22, s12,
        max_deflection,
        von_mises
    )


# ──────────────────────────────────────────────────────────────────────────────
# Adaptive wrapper
# ──────────────────────────────────────────────────────────────────────────────

def solve_fem_adaptive(
    geometry: Geometry,
    elastic_modulus_mpa=2500.0,
    poisson_ratio=0.35,
    point_load_newtons=5.0 * 9.81,
    initial_nx=200,
    max_nx=800,
    tol=0.02
):

    history = []
    prev = None

    nx = initial_nx

    while nx <= max_nx:
        length, height = _get_bridge_dimensions(geometry)
        ny = max(4, round(nx * height / length))

        res = solve_fem(
            geometry, nx, ny,
            elastic_modulus_mpa,
            poisson_ratio,
            point_load_newtons
        )

        d = res.max_deflection_mm
        history.append((nx, ny, d))

        if prev is not None:
            rel = abs(d - prev) / (abs(prev) + 1e-12)
            if rel < tol:
                break

        prev = d
        nx = int(nx * 1.5)

    return res, history


# ──────────────────────────────────────────────────────────────────────────────
# FEM internals
# ──────────────────────────────────────────────────────────────────────────────
def _quad4_B_matrix_gauss(xi, eta, dx, dy):
    dN_dxi = np.array([
        [-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)]
    ]) * 0.25

    dN_deta = np.array([
        [-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)]
    ]) * 0.25

    J = np.array([
        [dx/2, 0],
        [0, dy/2]
    ])

    invJ = np.linalg.inv(J)

    dN = np.vstack((dN_dxi, dN_deta))
    dN_xy = invJ @ dN

    B = np.zeros((3, 8))
    for i in range(4):
        B[0, 2*i]     = dN_xy[0, i]
        B[1, 2*i + 1] = dN_xy[1, i]
        B[2, 2*i]     = dN_xy[1, i]
        B[2, 2*i + 1] = dN_xy[0, i]

    return B

def _quad4_element_stiffness(dx, dy, D):
    gp = [-1/np.sqrt(3), 1/np.sqrt(3)]
    Ke = np.zeros((8, 8))

    for xi in gp:
        for eta in gp:
            B = _quad4_B_matrix_gauss(xi, eta, dx, dy)
            detJ = (dx * dy) / 4
            Ke += B.T @ D @ B * detJ * BRIDGE_DEPTH

    return Ke


def _quad4_B_matrix(dx, dy):
    # constant strain approximation
    return np.array([
        [-1/dx, 0, 1/dx, 0, 1/dx, 0, -1/dx, 0],
        [0, -1/dy, 0, -1/dy, 0, 1/dy, 0, 1/dy],
        [-1/dy, -1/dx, -1/dy, 1/dx, 1/dy, 1/dx, 1/dy, -1/dx]
    ]) * 0.5


def _fix_dof(K, f, idx, value):
    K[idx, :] = 0
    K[idx, idx] = 1
    f[idx] = value


def _get_bridge_dimensions(geometry: Geometry) -> Tuple[float, float]:
    min_x, min_y, max_x, max_y = geometry.bounding_box()
    return max_x - min_x, max_y - min_y
