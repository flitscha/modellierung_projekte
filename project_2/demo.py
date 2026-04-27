import numpy as np
import matplotlib.pyplot as plt
from scipy.sparse import dok_matrix, csr_matrix
from scipy.sparse.linalg import spsolve


def run(nx, ny, plots=False):
    L = 10.0 # length
    H = 1.0 # height

    # material properties
    E = 200e9
    nu = 0.3
    rho_g = -7850.0 * 9.81

    mu = E / (2 * (1 + nu))
    lambda_ = E * nu / ((1 + nu) * (1 - 2 * nu))
    lambda_ = 2 * mu * lambda_ / (lambda_ + 2 * mu)

    x = np.linspace(0, L, nx + 1, endpoint=False)[1:]
    y = np.linspace(0, H, ny + 1, endpoint=False)[1:]
    hx = x[1] - x[0]
    hy = y[1] - y[0]

    vars_ = ['s11', 's22', 's12', 'u', 'v']

    sol = np.zeros(5*nx*ny)
    rhs = np.zeros(5 * nx * ny)
    A = dok_matrix((5 * nx * ny, 5 * nx * ny))

    def idx(var, i, j):
        if isinstance(var, int):
            return var * nx * ny + j * nx + i
        return vars_.index(var) * nx * ny + j * nx + i

    def add_stencil_x_sigma(eq, var, i, j):
        if i == 0:
            A[idx(eq, i, j), idx(var, i + 1, j)] += 1.0 / hx
            A[idx(eq, i, j), idx(var, i, j)] += -1.0 / hx
        elif i == nx - 1:
            # homogeneous Dirichlet
            A[idx(eq, i, j), idx(var, i - 1, j)] += -1.0 / (2 * hx)
        else:
            A[idx(eq, i, j), idx(var, i + 1, j)] += 1.0 / (2 * hx)
            A[idx(eq, i, j), idx(var, i - 1, j)] += -1.0 / (2 * hx)

    def add_stencil_y_sigma(eq, var, i, j):
        if j == 0:
            A[idx(eq, i, j), idx(var, i, j + 1)] += 1.0 / (2 * hy)
        elif j == ny - 1:
            A[idx(eq, i, j), idx(var, i, j - 1)] += -1.0 / (2 * hy)
        else:
            A[idx(eq, i, j), idx(var, i, j + 1)] += 1.0 / (2 * hy)
            A[idx(eq, i, j), idx(var, i, j - 1)] += -1.0 / (2 * hy)

    # add equations for sigma11, sigma22, sigma12
    for i in range(nx):
        for j in range(ny):
            # \partial_x \sigma_11 + \partial_y \sigma_12 = 0
            add_stencil_x_sigma(0, 's11', i, j)
            add_stencil_y_sigma(0, 's12', i, j)

            # \partial_x \sigma_12 + \partial_y \sigma_22 + rho_g = 0
            add_stencil_x_sigma(1, 's12', i, j)
            add_stencil_y_sigma(1, 's22', i, j)
            rhs[idx(1, i, j)] = -rho_g

    def add_stencil_x_uv(eq, var, i, j, coeff):
        if i == 0:
            A[idx(eq, i, j), idx(var, i, j)] += coeff / hx
        elif i == nx - 1:
            A[idx(eq, i, j), idx(var, i, j)] += coeff / hx
            A[idx(eq, i, j), idx(var, i - 1, j)] += -coeff / hx
        else:
            A[idx(eq, i, j), idx(var, i + 1, j)] += coeff / (2 * hx)
            A[idx(eq, i, j), idx(var, i - 1, j)] += -coeff / (2 * hx)

    def add_stencil_y_uv(eq, var, i, j, coeff):
        if j == 0:
            A[idx(eq, i, j), idx(var, i, j + 1)] += coeff / hy
            A[idx(eq, i, j), idx(var, i, j)] += -coeff / hy
        elif j == ny - 1:
            A[idx(eq, i, j), idx(var, i, j)] += coeff / hy
            A[idx(eq, i, j), idx(var, i, j - 1)] += -coeff / hy
        else:
            A[idx(eq, i, j), idx(var, i, j + 1)] += coeff / (2 * hy)
            A[idx(eq, i, j), idx(var, i, j - 1)] += -coeff / (2 * hy)

    # add equations for u, v
    for i in range(nx):
        for j in range(ny):
            # sigma_11 = (lambda + 2*mu) \partial_x u + lambda \partial_y v
            add_stencil_x_uv(2, 'u', i, j, lambda_ + 2 * mu)
            add_stencil_y_uv(2, 'v', i, j, lambda_)
            A[idx(2, i, j), idx('s11', i, j)] += -1

            # sigma_22 = lambda \partial_x u + (lambda + 2*mu) \partial_y v
            add_stencil_x_uv(3, 'u', i, j, lambda_)
            add_stencil_y_uv(3, 'v', i, j, lambda_ + 2 * mu)
            A[idx(3, i, j), idx('s22', i, j)] += -1

            # sigma_12 = mu*(\partial_y u + \partial_x v)
            add_stencil_y_uv(4, 'u', i, j, mu)
            add_stencil_x_uv(4, 'v', i, j, mu)
            A[idx(4, i, j), idx('s12', i, j)] += -1

    # solve the system
    sol = spsolve(csr_matrix(A), rhs)

    s11 = sol[0:nx * ny].reshape((ny, nx)).T
    s22 = sol[nx * ny:2 * nx * ny].reshape((ny, nx)).T
    s12 = sol[2 * nx * ny:3 * nx * ny].reshape((ny, nx)).T
    u = sol[3 * nx * ny:4 * nx * ny].reshape((ny, nx)).T
    v = sol[4 * nx * ny:5 * nx * ny].reshape((ny, nx)).T

    print("Maximal deflection:", v[-1, int(ny / 2)])
    print("Beam theory:", 3 * rho_g * L**4 / (2 * E * H**3))

    if plots:
        fig, axes = plt.subplots(5, 1, figsize=(10, 10))

        data = [u, v, s11, s22, s12]
        titles = ["u1", "u2", "sigma11", "sigma22", "sigma12"]

        # sigma11: stress in x-direction
        # sigma22: stress in y-direction
        # sigma12: schub-spannung
        # u1: verschiebung in x-richtung
        # u2: verschiebung in y-richtung

        for ax, d, t in zip(axes, data, titles):
            im = ax.imshow(d.T, extent=[0, L, 0, H])
            ax.set_title(t)
            fig.colorbar(im, ax=ax)

        plt.tight_layout()
        plt.show()

    return v


run(40, 40, plots=True)
