"""
XFOIL Comparison Tab
--------------------
Runs our vortex panel solver and XFOIL side-by-side for any NACA 4-digit
airfoil, and overlays the wind tunnel measurements (only for NACA 2412).

Wind tunnel reference data (Prof):
  chord = span = 100 mm, V = 4.5 m/s  →  Re ≈ 30 000
  L, D measured in gram-force
"""

import threading
import subprocess
import tempfile
import os

import dearpygui.dearpygui as dpg
import numpy as np

from simulations.simulate_in_range import evaluate_cl_range

# ── Wind tunnel reference data ────────────────────────────────────────────────
_WT_ALPHA  = np.array([0.,  2.,  4.,  6.,  8.,  10.])
_WT_L_GF   = np.array([2.57, 3.58, 4.44, 5.10, 5.63, 6.46])
_WT_DL_GF  = np.array([0.08, 0.21, 0.24, 0.32, 0.23, 0.32])
_WT_D_GF   = np.array([0.63, 0.75, 0.89, 1.02, 1.15, 1.38])
_WT_DD_GF  = np.array([0.04, 0.05, 0.13, 0.17, 0.18, 0.11])

def _wt_cl_cd():
    """Convert gram-force measurements to Cl / Cd coefficients."""
    rho, V, c, span = 1.225, 4.5, 0.1, 0.1
    qA = 0.5 * rho * V**2 * (c * span)   # = 0.12403 N
    g  = 9.81e-3                           # 1 gf = 9.81e-3 N
    cl     = _WT_L_GF  * g / qA
    cl_err = _WT_DL_GF * g / qA
    cd     = _WT_D_GF  * g / qA
    cd_err = _WT_DD_GF * g / qA
    return _WT_ALPHA, cl, cl_err, cd, cd_err

# ── XFOIL helper ──────────────────────────────────────────────────────────────

def _run_xfoil(coords, re, alpha_start=0., alpha_end=10., alpha_step=1.):
    """
    Call XFOIL via subprocess.  Returns (alpha, cl, cd) arrays or None on failure.
    Runs synchronously – call from a background thread.
    """
    home = os.path.expanduser("~")
    dat_path   = os.path.join(home, "xfoil_input.dat")
    polar_path = os.path.join(home, "xfoil_polar.txt")

    # Remove stale polar file so we can detect if XFOIL wrote a new one
    if os.path.exists(polar_path):
        os.unlink(polar_path)

    with open(dat_path, 'w') as f:
        f.write("airfoil\n")
        for x, y in coords:
            f.write(f"{x:.6f} {y:.6f}\n")
    commands = (
        f"LOAD {dat_path}\nairfoil\nPANE\nOPER\n"
        f"VISC {re:.4e}\nPACC\n{polar_path}\n\n"
        f"ASEQ {alpha_start} {alpha_end} {alpha_step}\nPACC\nQUIT\n"
    )

    try:
        subprocess.run(['xfoil'], input=commands, capture_output=True,
                       text=True, timeout=60)
    except FileNotFoundError:
        return None, "xfoil not found – install with: brew tap chrislupp/xfoil && brew install xfoil"
    except subprocess.TimeoutExpired:
        return None, "XFOIL timed out"
    finally:
        try:
            os.unlink(dat_path)
        except OSError:
            pass

    if not os.path.exists(polar_path):
        return None, "XFOIL did not write polar file"

    alphas, cls, cds = [], [], []
    with open(polar_path) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    alphas.append(float(parts[0]))
                    cls.append(float(parts[1]))
                    cds.append(float(parts[2]))
                except ValueError:
                    continue
    try:
        os.unlink(polar_path)
    except OSError:
        pass

    if not alphas:
        return None, "Could not parse XFOIL polar output"

    return (np.array(alphas), np.array(cls), np.array(cds)), None


# ── Tab state ─────────────────────────────────────────────────────────────────

class _State:
    def __init__(self):
        self.designs_by_name: dict = {}
        self.design = None
        self.params: dict = {}
        self.re: float = 3e4

        # Results (set from background thread, consumed in tick())
        self.pending_result = None   # dict with keys: ps, xf, wt, error
        self.running = False


_s = _State()

# DearPyGui plot-series tags
_TAG_X_CL    = "xfc_x_cl"
_TAG_Y_CL    = "xfc_y_cl"
_TAG_PS_CL   = "xfc_ps_cl"
_TAG_XF_CL   = "xfc_xf_cl"



# ── Build ─────────────────────────────────────────────────────────────────────

def build(parent_tag: str, designs: list):
    _s.designs_by_name = {d.name: d for d in designs}

    with dpg.tab(label="XFOIL Comparison", parent=parent_tag, tag="tab_xfoil"):
        dpg.add_spacer(height=6)
        _build_top_bar(designs)
        dpg.add_spacer(height=10)
        _build_plots()
        dpg.add_spacer(height=14)
        _build_table()

    _select_design(designs[0])


def tick():
    """Called every frame from the main loop."""
    result = _s.pending_result
    if result is not None:
        _s.pending_result = None
        _apply_result(result)


# ── Layout ────────────────────────────────────────────────────────────────────

def _build_top_bar(designs):
    with dpg.group(horizontal=True):
        dpg.add_text("Design:")
        dpg.add_combo(
            items=[d.name for d in designs],
            default_value=designs[0].name,
            width=160,
            callback=lambda s, v: _select_design(_s.designs_by_name[v]),
        )
        dpg.add_spacer(width=20)
        dpg.add_text("Re:")
        dpg.add_input_float(
            tag="xfc_re_input",
            default_value=3e4,
            format="%.0f",
            width=110,
            step=0,
            callback=lambda s, v: setattr(_s, 're', max(1000., v)),
        )
        dpg.add_spacer(width=20)
        dpg.add_button(
            label="Run Comparison",
            tag="xfc_btn_run",
            width=150, height=32,
            callback=_on_run,
        )
        dpg.add_spacer(width=16)
        dpg.add_text("Status:", color=(160, 160, 180))
        dpg.add_spacer(width=4)
        dpg.add_text("idle", tag="xfc_status", color=(160, 160, 180))

    dpg.add_spacer(height=6)

    # Parameter sliders (populated when design is selected)
    with dpg.group(horizontal=True):
        with dpg.group():
            dpg.add_text("Geometry Parameters", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=4)
            dpg.add_group(tag="xfc_slider_group")

    dpg.add_spacer(height=4)
    dpg.add_text(
        "Note: wind tunnel data (error bars) only shown for NACA 2412.",
        color=(140, 140, 160),
    )


def _build_plots():
    with dpg.group(horizontal=True):
        # Left: Cl vs alpha
        with dpg.plot(label="Cl vs alpha", height=280, width=-2, tag="xfc_plot_cl"):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="alpha [deg]", tag=_TAG_X_CL)
            with dpg.plot_axis(dpg.mvYAxis, label="Cl", tag=_TAG_Y_CL):
                dpg.add_line_series([], [], label="Panel solver (inviscid)",
                                    tag=_TAG_PS_CL)
                dpg.add_line_series([], [], label="XFOIL",
                                    tag=_TAG_XF_CL)





def _build_table():
    dpg.add_text("Results Table", color=(200, 200, 200))
    dpg.add_separator()
    dpg.add_spacer(height=4)
    dpg.add_group(tag="xfc_table_group")


# ── Logic ─────────────────────────────────────────────────────────────────────

def _select_design(design):
    _s.design = design
    _s.params = design.default_parameters()
    _rebuild_sliders(design)
    _clear_plots()
    _set_status("idle", (160, 160, 180))


def _rebuild_sliders(design):
    dpg.delete_item("xfc_slider_group", children_only=True)
    for p in design.parameter_space():
        val = _s.params[p.name]
        dpg.add_slider_float(
            label=p.name,
            tag=f"xfc_slider_{p.name}",
            default_value=float(val),
            min_value=p.low,
            max_value=p.high,
            format="%.3f",
            width=300,
            callback=lambda s, v, u: _s.params.__setitem__(u, v),
            user_data=p.name,
            parent="xfc_slider_group",
        )


def _on_run():
    if _s.running or _s.design is None:
        return
    if not _s.design.validate(_s.params):
        _set_status("Invalid parameters", (255, 180, 0))
        return

    _s.running = True
    dpg.configure_item("xfc_btn_run", enabled=False)
    _set_status("running...", (255, 200, 10))
    _clear_plots()

    airfoil = _s.design.build_airfoil(_s.params)
    re      = _s.re

    def _worker():
        # Panel solver
        try:
            ps = evaluate_cl_range(airfoil, 0., 10., 1.)
            ps_data = (np.array(ps["alpha_range"]), np.array(ps["all_cl"]))
        except Exception as e:
            _s.pending_result = {"error": f"Panel solver error: {e}"}
            _s.running = False
            return

        # XFOIL
        xf_data, xf_err = _run_xfoil(airfoil.coords, re)

        # Wind tunnel (only for NACA 2412)
        is_2412 = (
            abs(_s.params.get("camber", -1)     - 0.02) < 1e-9 and
            abs(_s.params.get("camber_pos", -1) - 0.40) < 1e-9 and
            abs(_s.params.get("thickness", -1)  - 0.12) < 1e-9
        )
        wt = _wt_cl_cd() if is_2412 else None

        _s.pending_result = {
            "airfoil_name": airfoil.name,
            "ps":  ps_data,
            "xf":  xf_data,
            "xf_err": xf_err,
            "wt":  wt,
            "error": None,
        }
        _s.running = False

    threading.Thread(target=_worker, daemon=True).start()


def _apply_result(result):
    dpg.configure_item("xfc_btn_run", enabled=True)

    if result.get("error"):
        _set_status(result["error"], (255, 100, 100))
        return

    name = result.get("airfoil_name", "")
    ps   = result["ps"]    # (alpha_arr, cl_arr)
    xf   = result["xf"]    # (alpha, cl, cd) or None
    wt   = result["wt"]    # (alpha, cl, cl_err, cd, cd_err) or None

    # ── Cl plot ──────────────────────────────────────────────────────────────
    dpg.set_value(_TAG_PS_CL, [ps[0].tolist(), ps[1].tolist()])

    if xf is not None:
        dpg.set_value(_TAG_XF_CL, [xf[0].tolist(), xf[1].tolist()])
    else:
        dpg.set_value(_TAG_XF_CL, [[], []])
        xf_err = result.get("xf_err", "XFOIL unavailable")
        _set_status(f"XFOIL: {xf_err}", (255, 180, 0))



    dpg.fit_axis_data(_TAG_X_CL)
    dpg.fit_axis_data(_TAG_Y_CL)

    # ── Cl/Cd plot ────────────────────────────────────────────────────────────




    # ── Table ─────────────────────────────────────────────────────────────────
    _build_result_table(name, ps, xf, wt)

    if xf is not None:
        _set_status("done", (100, 220, 100))
    else:
        _set_status(f"Panel solver done – XFOIL: {result.get('xf_err','?')}", (255, 180, 0))


def _build_result_table(name, ps, xf, wt):
    dpg.delete_item("xfc_table_group", children_only=True)

    with dpg.table(
        parent="xfc_table_group",
        header_row=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
        row_background=True,
    ):
        dpg.add_table_column(label="alpha [deg]")
        dpg.add_table_column(label="Cl  Panel solver")
        dpg.add_table_column(label="Cl  XFOIL")
        dpg.add_table_column(label="Delta Cl (panel - XFOIL)")
        if wt is not None:
            dpg.add_table_column(label="Cl  Wind tunnel (NACA 2412)")

        alpha_ps, cl_ps = ps

        for i, (a, cl_p) in enumerate(zip(alpha_ps, cl_ps)):
            # XFOIL match
            if xf is not None:
                idx = int(np.argmin(np.abs(xf[0] - a)))
                if np.abs(xf[0][idx] - a) < 0.6:
                    cl_xf_str = f"{xf[1][idx]:.4f}"
                    delta_str = f"{cl_p - xf[1][idx]:+.4f}"
                else:
                    cl_xf_str = "—"
                    delta_str = "—"
            else:
                cl_xf_str = "—"
                delta_str = "—"

            # Wind tunnel match
            if wt is not None:
                wt_alpha, wt_cl, wt_cl_err, _, _ = wt
                idx_wt = np.where(np.abs(wt_alpha - a) < 0.6)[0]
                cl_wt_str = f"{wt_cl[idx_wt[0]]:.4f} ±{wt_cl_err[idx_wt[0]]:.4f}" if len(idx_wt) else "—"
            else:
                cl_wt_str = "—"

            with dpg.table_row():
                dpg.add_text(f"{a:.0f}")
                dpg.add_text(f"{cl_p:.4f}")
                dpg.add_text(cl_xf_str)
                dpg.add_text(delta_str)
                if wt is not None:
                    dpg.add_text(cl_wt_str)


def _clear_plots():
    for tag in (_TAG_PS_CL, _TAG_XF_CL):
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, [[], []])
    if dpg.does_item_exist("xfc_table_group"):
        dpg.delete_item("xfc_table_group", children_only=True)


def _set_status(msg: str, color: tuple):
    if dpg.does_item_exist("xfc_status"):
        dpg.set_value("xfc_status", msg)
        dpg.configure_item("xfc_status", color=color)
