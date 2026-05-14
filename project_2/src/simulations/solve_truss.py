import numpy as np

import config

def solve_truss(truss, forces=None, fixed_dofs=None, E=config.PLA_ELASTIC_MODULUS_MPA):
    """
    Solves a 2D truss.

    Parameters
    ----------
    truss : Truss
    forces : dict[node_index -> (Fx, Fy)]
    fixed_dofs : list[(node_index, dof)]  # dof: 0=x, 1=y
    E : Young's modulus (Pa)

    Returns
    -------
    displacements : (N, 2)
    forces_in_edges : list[float]
    """

    if forces is None:
        forces = _get_standard_forces(truss)
    if fixed_dofs is None:
        fixed_dofs = _get_standard_fixed_dofs(truss)

    nodes = truss.nodes
    edges = truss.edges

    n = len(nodes)
    dof = 2 * n

    K = np.zeros((dof, dof))
    F = np.zeros(dof)

    # Assemble stiffness matrix
    for edge in edges:
        i, j = edge.i, edge.j
        A = edge.area

        xi, yi = nodes[i].x, nodes[i].y
        xj, yj = nodes[j].x, nodes[j].y

        dx = xj - xi
        dy = yj - yi
        L = np.sqrt(dx*dx + dy*dy)

        c = dx / L
        s = dy / L

        k = (E * A / L) * np.array([
            [c*c, c*s, -c*c, -c*s],
            [c*s, s*s, -c*s, -s*s],
            [-c*c, -c*s, c*c, c*s],
            [-c*s, -s*s, c*s, s*s],
        ])

        dof_map = [
            2*i, 2*i+1,
            2*j, 2*j+1
        ]

        for a in range(4):
            for b in range(4):
                K[dof_map[a], dof_map[b]] += k[a, b]

    # Apply forces
    for node_idx, (Fx, Fy) in forces.items():
        F[2*node_idx]   += Fx
        F[2*node_idx+1] += Fy

    # Apply boundary conditions
    for node_idx, d in fixed_dofs:
        idx = 2*node_idx + d
        K[idx, :] = 0
        K[:, idx] = 0
        K[idx, idx] = 1
        F[idx] = 0

    # Solve
    U = np.linalg.solve(K, F)

    displacements = U.reshape((n, 2))

    # Compute forces in edges
    edge_forces = []

    for edge in edges:
        i, j = edge.i, edge.j
        A = edge.area

        xi, yi = nodes[i].x, nodes[i].y
        xj, yj = nodes[j].x, nodes[j].y

        dx = xj - xi
        dy = yj - yi
        L = np.sqrt(dx*dx + dy*dy)

        c = dx / L
        s = dy / L

        ui = displacements[i]
        uj = displacements[j]

        du = np.array([
            uj[0] - ui[0],
            uj[1] - ui[1]
        ])

        axial_strain = (du[0]*c + du[1]*s) / L
        force = E * A * axial_strain

        edge_forces.append(force)

    # store in truss
    truss.displacements = displacements
    truss.forces = edge_forces

    return displacements, edge_forces


# ----------------- Helpers ------------------------------
def _get_standard_forces(truss):
    """
    A 5kg weight is placed on top of the bridge in the middle
    """
    xs = [n.x for n in truss.nodes]
    min_x, max_x = min(xs), max(xs)
    mid_x = 0.5 * (min_x + max_x)
    top_nodes = [i for i, n in enumerate(truss.nodes) if n.y == config.BRIDGE_HEIGHT]
    mid_node = min(top_nodes, key=lambda i: abs(truss.nodes[i].x - mid_x))

    # apply the 5kg mass at the top-middle node
    forces = {mid_node: (0.0, -config.LOAD_FORCE)}
    return forces


def _get_standard_fixed_dofs(truss):
    """
    The bridge is fixed to the left and right sides with screws from below.

    Therefore, we assume that the bottom-left and bottom-right nodes are fixed
    """

    bottom_nodes = [i for i, n in enumerate(truss.nodes) if n.y == 0]
    left = min(bottom_nodes, key=lambda i: truss.nodes[i].x)
    right = max(bottom_nodes, key=lambda i: truss.nodes[i].x)

    fixed_dofs = [
        (left, 0), (left, 1), # x-direction and y-direction
        (right, 0), (right, 1)
    ]
    return fixed_dofs

