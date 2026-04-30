"""
Brücken-Simulation mit SVG-Materialmaske
==========================================
Basiert auf dem Professorcode (2D lineare Elastizität, FDM).

Anpassungen:
  - SVG wird als Materialmaske eingelesen (schwarz=Material, weiß=Luft)
  - E_local = E_mat wo Material, E_mat * 1e-6 wo Luft (numerisch stabil)
  - Beide Seiten eingespannt: u=v=0 via Penalty-Methode
  - Punktlast F in der Mitte oben als Körperkraft auf obere Zellen
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.sparse import dok_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
import cairosvg
from PIL import Image
import io, sys, os, glob


def svg_to_mask(svg_path, nx, ny):
    """Rasterisiert SVG auf nx×ny Grid. Gibt bool-Array [ny,nx] zurück: True=Material."""
    png = cairosvg.svg2png(url=svg_path, output_width=nx, output_height=ny)
    arr = np.array(Image.open(io.BytesIO(png)).convert("L"))
    return arr < 128


def run(svg_path, nx=200, ny=100, plots=True, save_path=None):
    L = 300e-3
    H = 15e-3
    hx = L / nx
    hy = H / ny

    E_mat = 3.5e9
    nu    = 0.36
    E_air = E_mat * 1e-6

    F = 5.0 * 9.81

    mask = svg_to_mask(svg_path, nx, ny)
    mat_ratio = mask.mean()
    print(f"  Materialanteil: {mat_ratio*100:.1f}%")

    def lame(i, j):
        E  = E_mat if mask[j, i] else E_air
        mu = E / (2*(1+nu))
        la = E * nu / ((1+nu)*(1-2*nu))
        return mu, la, la + 2*mu

    vars_ = ['s11', 's22', 's12', 'u', 'v']
    def idx(var, i, j):
        v = var if isinstance(var, int) else vars_.index(var)
        return v * nx*ny + j*nx + i

    N = 5 * nx * ny
    A   = dok_matrix((N, N))
    rhs = np.zeros(N)

    def add_dx_sig(eq, var, i, j):
        if i == 0:
            A[idx(eq,i,j), idx(var,i+1,j)] += 1/hx
            A[idx(eq,i,j), idx(var,i,  j)] -= 1/hx
        elif i == nx-1:
            A[idx(eq,i,j), idx(var,i-1,j)] -= 1/(2*hx)
        else:
            A[idx(eq,i,j), idx(var,i+1,j)] += 1/(2*hx)
            A[idx(eq,i,j), idx(var,i-1,j)] -= 1/(2*hx)

    def add_dy_sig(eq, var, i, j):
        if j == 0:
            A[idx(eq,i,j), idx(var,i,j+1)] += 1/(2*hy)
        elif j == ny-1:
            A[idx(eq,i,j), idx(var,i,j-1)] -= 1/(2*hy)
        else:
            A[idx(eq,i,j), idx(var,i,j+1)] += 1/(2*hy)
            A[idx(eq,i,j), idx(var,i,j-1)] -= 1/(2*hy)

    for i in range(nx):
        for j in range(ny):
            add_dx_sig(0, 's11', i, j)
            add_dy_sig(0, 's12', i, j)
            add_dx_sig(1, 's12', i, j)
            add_dy_sig(1, 's22', i, j)

    def add_dx_uv(eq, var, i, j, c):
        if i == 0:
            A[idx(eq,i,j), idx(var,i,  j)] += c/hx
        elif i == nx-1:
            A[idx(eq,i,j), idx(var,i,  j)] += c/hx
            A[idx(eq,i,j), idx(var,i-1,j)] -= c/hx
        else:
            A[idx(eq,i,j), idx(var,i+1,j)] += c/(2*hx)
            A[idx(eq,i,j), idx(var,i-1,j)] -= c/(2*hx)

    def add_dy_uv(eq, var, i, j, c):
        if j == 0:
            A[idx(eq,i,j), idx(var,i,j+1)] += c/hy
            A[idx(eq,i,j), idx(var,i,j  )] -= c/hy
        elif j == ny-1:
            A[idx(eq,i,j), idx(var,i,j  )] += c/hy
            A[idx(eq,i,j), idx(var,i,j-1)] -= c/hy
        else:
            A[idx(eq,i,j), idx(var,i,j+1)] += c/(2*hy)
            A[idx(eq,i,j), idx(var,i,j-1)] -= c/(2*hy)

    for i in range(nx):
        for j in range(ny):
            mu, la, la2mu = lame(i, j)
            add_dx_uv(2, 'u', i, j, la2mu)
            add_dy_uv(2, 'v', i, j, la)
            A[idx(2,i,j), idx('s11',i,j)] -= 1

            add_dx_uv(3, 'u', i, j, la)
            add_dy_uv(3, 'v', i, j, la2mu)
            A[idx(3,i,j), idx('s22',i,j)] -= 1

            add_dy_uv(4, 'u', i, j, mu)
            add_dx_uv(4, 'v', i, j, mu)
            A[idx(4,i,j), idx('s12',i,j)] -= 1

    # Beidseitig eingespannt via Penalty
    PENALTY = 1e20
    for j in range(ny):
        for var in ['u', 'v']:
            for ic in [0, nx-1]:
                r = idx(var, ic, j)
                A[r, r] += PENALTY

    # Last als Körperkraft auf obere Zellen in der Mitte
    n_load  = max(2, nx // 5)
    i0      = nx//2 - n_load//2
    i1      = i0 + n_load
    f_body  = -F / (n_load * hx * hy)
    for i in range(i0, i1):
        rhs[idx(1, i, ny-1)] += f_body

    print(f"  System: {N} Gl.,  nnz = {A.nnz}")
    sol = spsolve(csr_matrix(A), rhs)

    s11 = sol[0*nx*ny:1*nx*ny].reshape((ny, nx))
    s22 = sol[1*nx*ny:2*nx*ny].reshape((ny, nx))
    s12 = sol[2*nx*ny:3*nx*ny].reshape((ny, nx))
    u   = sol[3*nx*ny:4*nx*ny].reshape((ny, nx))
    v   = sol[4*nx*ny:5*nx*ny].reshape((ny, nx))

    v_max = abs(v[:, nx//2].min())
    print(f"  Max. Durchbiegung: {v_max*1e3:.4f} mm")

    b_depth    = 50e-3
    I_full     = b_depth * H**3 / 12
    delta_beam = F * L**3 / (192 * E_mat * I_full)
    print(f"  Balkentheorie (Vollrechteck): {delta_beam*1e3:.4f} mm")

    if plots:
        fig, axes = plt.subplots(2, 3, figsize=(14, 7))
        name = os.path.basename(svg_path).replace(".svg", "")
        fig.suptitle(
            f"{name}  |  Material: {mat_ratio*100:.1f}%  |  "
            f"Max. Durchbiegung: {v_max*1e3:.3f} mm  "
            f"({'OK <=3mm' if v_max*1e3 <= 3.0 else 'ZU VIEL >3mm'})",
            fontsize=12
        )
        extent = [0, L*1e3, 0, H*1e3]

        def show(ax, data, title, cmap='RdBu_r', air_nan=True):
            d = np.where(mask, data, np.nan) if air_nan else data.astype(float)
            vabs = np.nanmax(np.abs(d)) if air_nan else None
            im = ax.imshow(d, extent=extent, origin='lower', cmap=cmap,
                           aspect='auto',
                           vmin=-vabs if vabs else None,
                           vmax= vabs if vabs else None)
            ax.set_title(title, fontsize=10)
            ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]")
            fig.colorbar(im, ax=ax, shrink=0.8)

        show(axes[0,0], mask.astype(float), "Materialmaske", cmap='Blues', air_nan=False)
        show(axes[0,1], v*1e3, "v [mm]  (negativ = nach unten)")
        show(axes[0,2], u*1e3, "u [mm]  (horizontal)")
        show(axes[1,0], s11/1e6, "sigma_11 [MPa]")
        show(axes[1,1], s22/1e6, "sigma_22 [MPa]")
        show(axes[1,2], s12/1e6, "sigma_12 [MPa]")

        plt.tight_layout()
        out = save_path or svg_path.replace(".svg", f"_sim_{nx}x{ny}.png")
        plt.savefig(out, dpi=130, bbox_inches='tight')
        print(f"  -> {out}")
        plt.close()

    return {
        "name":      os.path.basename(svg_path).replace(".svg",""),
        "mat_ratio": mat_ratio,
        "v_max_mm":  v_max * 1e3,
        "v": v, "u": u, "s11": s11, "s22": s22, "s12": s12,
        "mask": mask,
    }


if __name__ == "__main__":
    default_svg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_svgs")
    svg_dir = sys.argv[1] if len(sys.argv) > 1 else default_svg_dir
    nx, ny  = 300, 15

    files = sorted(glob.glob(os.path.join(svg_dir, "*.svg")))
    if not files:
        print(f"Keine SVGs in {svg_dir}"); sys.exit(1)

    results = []
    for f in files:
        print(f"\n{os.path.basename(f)}")
        print("-" * 40)
        try:
            r = run(f, nx=nx, ny=ny, plots=True)
            results.append(r)
        except Exception as e:
            print(f"  FEHLER: {e}")
            import traceback; traceback.print_exc()

    print(f"\n{'='*58}")
    print("  RANKING  (Ziel: delta <= 3 mm, moeglichst wenig Material)")
    print(f"{'='*58}")
    results.sort(key=lambda r: r["v_max_mm"])
    for i, r in enumerate(results):
        ok = "OK" if r["v_max_mm"] <= 3.0 else "ZU VIEL"
        print(f"  {i+1}. {r['name']:<22}  "
              f"delta = {r['v_max_mm']:6.3f} mm  "
              f"Mat = {r['mat_ratio']*100:5.1f}%  {ok}")
