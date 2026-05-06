
class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Edge:
    def __init__(self, i: int, j: int, area: float):
        self.i = i
        self.j = j
        self.area = area


"""
A truss is an undirected graph. Its edges can have a certain thickness.

In truss-solver, it is assumed that each edge is very stable
and can only rotate at its nodes. (No bending of edges)

This is more efficient than rasterizing the entire problem and calculating 
the bending using differential equations.
"""
class Truss:
    def __init__(self, nodes: list[Node], edges: list[Edge]):
        self.nodes = nodes
        self.edges = edges

        # filled by solver later
        self.displacements = None
        self.forces = None
