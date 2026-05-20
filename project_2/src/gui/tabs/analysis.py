import os
import threading
import datetime
import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image as _PILImage

import config
from core.geometry import Geometry
from simulations.solve_truss import solve_truss
from simulations.solve_fem import solve_fem_adaptive, FEMResult
from gui.bridge_canvas import render_geometry
from export.svg_parser import parse_svg
from export.svg_exporter import OUTPUT_DIR

CANVAS_W = 1200
CANVAS_H = 150

# Heatmap image dimensions (for the FEM field plots)
HEATMAP_W = 600
HEATMAP_H = 200

# Folder where PNG exports are written
PLOT_EXPORT_DIR = os.path.join(os.path.dirname(OUTPUT_DIR), "fem_plots")


class _State:
    def __init__(self):
        self.geometry: Geometry | None = None
        self.truss = None
        self.fem_result: FEMResult | None = None

        self.texture_geometry = None
        self.texture_disp_y = None
        self.texture_s11 = None
        self.texture_s22 = None
        self.texture_s12 = None
        self.texture_vonmises = None

        self.dirty_geometry = False
        self.fem_running = False
        self.fem_dirty = False # new FEM result waiting to be drawn


_s = _State()


def build(parent_tag: str):
    """Build the Analysis tab and register it under parent_tag."""
    _s.texture_geometry = _create_texture(CANVAS_W, CANVAS_H)
    _s.texture_disp_y = _create_texture(HEATMAP_W, HEATMAP_H)
    _s.texture_s11 = _create_texture(HEATMAP_W, HEATMAP_H)
    _s.texture_s22 = _create_texture(HEATMAP_W, HEATMAP_H)
    _s.texture_s12 = _create_texture(HEATMAP_W, HEATMAP_H)
    _s.texture_vonmises = _create_texture(HEATMAP_W, HEATMAP_H)

    with dpg.tab(label="Analysis", parent=parent_tag, tag="tab_analysis"):
        dpg.add_spacer(height=6)
        _build_top_bar()
        dpg.add_spacer(height=10)
        _build_geometry_canvas()
        dpg.add_spacer(height=14)
        _build_truss_results()
        dpg.add_separator()
        dpg.add_spacer(height=10)
        _build_fem_section()


def tick():
    """Called every frame from the main loop."""
    _sync_canvas_width()
    if _s.dirty_geometry:
        _s.dirty_geometry = False
        _redraw_geometry()
        _run_truss_solver()
    if _s.fem_dirty:
        _s.fem_dirty = False
        _redraw_fem_heatmaps()


def load_geometry(geometry: Geometry):
    """Called by the Explorer tab (geometry only, no truss)."""
    _s.geometry = geometry
    _s.truss = None
    _s.fem_result = None
    _s.dirty_geometry = True
    _set_status("Loaded from Explorer", (100, 220, 100))
    dpg.set_value("main_tabs", "tab_analysis")


def load_design(geometry: Geometry, truss):
    """Called by the Explorer tab (geometry + truss)."""
    _s.geometry = geometry
    _s.truss    = truss
    _s.fem_result = None
    _s.dirty_geometry = True
    _set_status("Loaded from Explorer", (100, 220, 100))
    dpg.set_value("main_tabs", "tab_analysis")


# ----------------- Layout builders ----------------------------
def _build_top_bar():
    with dpg.group(horizontal=True):
        dpg.add_text("Load SVG:")
        dpg.add_combo(
            tag="analysis_svg_combo",
            items=_list_svgs(),
            width=220,
            callback=_on_svg_selected,
        )
        dpg.add_button(label="refresh", width=28, callback=_refresh_svg_list)
        dpg.add_spacer(width=30)
        dpg.add_text("Status:")
        dpg.add_text("No design loaded", tag="analysis_status", color=(160, 160, 180))


def _build_geometry_canvas():
    dpg.add_image(_s.texture_geometry, tag="analysis_image", width=CANVAS_W, height=CANVAS_H)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=8)
        dpg.add_text(f"length: {config.BRIDGE_LENGTH:.0f} mm", color=(160, 160, 180))
        dpg.add_spacer(width=20)
        dpg.add_text(f"height: {config.BRIDGE_HEIGHT:.0f} mm", color=(160, 160, 180))


def _build_truss_results():
    dpg.add_text("Truss Solver", color=(200, 200, 200))
    dpg.add_separator()
    dpg.add_spacer(height=6)
    with dpg.group(horizontal=True):
        _result_card("Weight", "-- g", "truss_weight")
        dpg.add_spacer(width=40)
        _result_card("Max Deflection", "-- mm", "truss_deflection")


def _build_fem_section():
    dpg.add_text("FEM Solver", color=(200, 200, 200))
    dpg.add_separator()
    dpg.add_spacer(height=6)

    with dpg.group(horizontal=True):
        dpg.add_button(
            label="Run FEM",
            width=260, height=36,
            callback=_on_run_fem,
        )
        dpg.add_spacer(width=12)
        dpg.add_button(
            label="Export plots as PNG",
            tag="btn_export_plots",
            width=200, height=36,
            callback=_on_export_plots,
        )
        dpg.add_spacer(width=20)
        dpg.add_text("", tag="fem_status", color=(160, 160, 180))

    dpg.add_spacer(height=10)

    with dpg.group(horizontal=True):
        _result_card("FEM Max Deflection", "-- mm", "fem_deflection")
        dpg.add_spacer(width=40)
        _result_card("FEM Max von Mises", "-- MPa", "fem_vonmises_max")
        dpg.add_spacer(width=40)
        _result_card("Convergence", "--", "fem_convergence")

    dpg.add_spacer(height=14)

    # Six heatmap images in two rows
    _heatmap_row(
        [("Vertical displacement [mm]", "heatmap_disp_y", _s.texture_disp_y),
         ("Normal stress  sigma11 [MPa]", "heatmap_s11", _s.texture_s11),
         ("Normal stress  sigma22 [MPa]", "heatmap_s22", _s.texture_s22)],
    )
    dpg.add_spacer(height=10)
    _heatmap_row(
        [("Shear stress  sigma12 [MPa]", "heatmap_s12", _s.texture_s12),
         ("von Mises stress [MPa]", "heatmap_vonmises", _s.texture_vonmises),
         None], # placeholder to keep layout symmetric
    )


def _heatmap_row(entries):
    with dpg.group(horizontal=True):
        for entry in entries:
            if entry is None:
                dpg.add_spacer(width=HEATMAP_W)
                continue
            label, tag, texture = entry
            with dpg.group():
                dpg.add_text(label, color=(160, 160, 180))
                dpg.add_image(texture, tag=tag, width=HEATMAP_W, height=HEATMAP_H)
            dpg.add_spacer(width=20)


def _result_card(label: str, placeholder: str, tag: str):
    with dpg.group():
        dpg.add_text(label, color=(160, 160, 180))
        dpg.add_text(placeholder, tag=tag)


# -------------- Logic -----------------------
def _on_svg_selected(sender, svg_filename):
    if not svg_filename:
        return
    path = os.path.join(OUTPUT_DIR, svg_filename)
    try:
        _s.geometry = parse_svg(path)
        _s.truss    = None
        _s.fem_result = None
        _s.dirty_geometry = True
        _set_status(f"Loaded: {svg_filename}", (100, 220, 100))
    except Exception as exc:
        _set_status(f"Error: {exc}", (255, 100, 100))


def _refresh_svg_list():
    dpg.configure_item("analysis_svg_combo", items=_list_svgs())


def _on_run_fem():
    if _s.geometry is None:
        _set_fem_status("No geometry loaded", (255, 180, 0))
        return
    if _s.fem_running:
        _set_fem_status("Already running...", (255, 180, 0))
        return

    _s.fem_running = True
    _set_fem_status("Running... (this may take a few seconds)", (255, 200, 60))

    thread = threading.Thread(target=_fem_worker, daemon=True)
    thread.start()


def _fem_worker():
    """Runs in a background thread so the GUI stays responsive."""
    try:
        result, history = solve_fem_adaptive(
            geometry=_s.geometry
        )
        _s.fem_result = result

        # Build convergence string  e.g. "20->30->45  delta=0.8 %"
        if len(history) >= 2:
            nx_steps = "->".join(str(h[0]) for h in history)
            last_two = history[-2:]
            rel = abs(last_two[1][2] - last_two[0][2]) / (abs(last_two[0][2]) + 1e-12) * 100
            conv_str = f"{nx_steps}  delta={rel:.1f}%"
        else:
            conv_str = f"{history[0][0]}×{history[0][1]}"

        dpg.set_value("fem_convergence", conv_str)
        dpg.set_value("fem_deflection", f"{result.max_deflection_mm:.4f} mm")
        dpg.set_value("fem_vonmises_max", f"{np.max(result.von_mises_stress):.2f} MPa")
        _set_fem_status("Done", (100, 220, 100))

        _s.fem_dirty = True # signal main thread to redraw textures

    except Exception as exc:
        _set_fem_status(f"Error: {exc}", (255, 100, 100))
    finally:
        _s.fem_running = False


def _on_export_plots():
    """Export the 5 FEM heatmap textures as PNG files."""
    if _s.fem_result is None:
        _set_fem_status("No FEM results to export - run the solver first.", (255, 180, 0))
        return

    os.makedirs(PLOT_EXPORT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    plots = [
        ("disp_y", _s.texture_disp_y, "Vertical displacement [mm]"),
        ("sigma11", _s.texture_s11, "Normal stress sigma11 [MPa]"),
        ("sigma22", _s.texture_s22, "Normal stress sigma22 [MPa]"),
        ("sigma12", _s.texture_s12, "Shear stress sigma12 [MPa]"),
        ("vonmises", _s.texture_vonmises, "von Mises stress [MPa]"),
    ]

    try:
        saved = []
        for name, texture_tag, _label in plots:
            raw = dpg.get_value(texture_tag)  # list of floats, length W*H*4
            arr = np.array(raw, dtype=np.float32).reshape((HEATMAP_H, HEATMAP_W, 4))
            arr = np.flipud(arr)
            img_arr = (arr * 255).clip(0, 255).astype(np.uint8)
            img = _PILImage.fromarray(img_arr, mode="RGBA")

            filename = f"{timestamp}_{name}.png"
            filepath = os.path.join(PLOT_EXPORT_DIR, filename)
            img.save(filepath)
            saved.append(filename)

        _set_fem_status(
            f"Exported {len(saved)} PNGs -> {PLOT_EXPORT_DIR}",
            (100, 220, 100),
        )
    except Exception as exc:
        _set_fem_status(f"Export error: {exc}", (255, 100, 100))


# ----------------- Helpers ------------------------------
def _redraw_geometry():
    if _s.geometry is None:
        return
    pixel_data = render_geometry(_s.geometry, CANVAS_W, CANVAS_H)
    dpg.set_value(_s.texture_geometry, pixel_data)

    weight = _s.geometry.estimate_weight_grams()
    dpg.set_value("truss_weight", f"{weight:.1f} g")


def _run_truss_solver():
    if _s.truss is None:
        dpg.set_value("truss_deflection", "-- mm (no truss)")
        return

    try:
        truss = _s.truss
        displacements, bar_forces = solve_truss(truss)

        max_defl = max(abs(d[1]) for d in displacements)
        dpg.set_value("truss_deflection", f"{max_defl:.4f} mm")

        _set_status("Truss solved", (100, 220, 100))

    except Exception as exc:
        _set_status(f"Truss error: {exc}", (255, 100, 100))
        dpg.set_value("truss_deflection", "-- mm")


def _redraw_fem_heatmaps():
    if _s.fem_result is None:
        return
    r = _s.fem_result

    _upload_heatmap(_s.texture_disp_y, r.displacement_y, r.material_mask, diverging=True)
    _upload_heatmap(_s.texture_s11, r.stress_11, r.material_mask, diverging=True)
    _upload_heatmap(_s.texture_s22, r.stress_22, r.material_mask, diverging=True)
    _upload_heatmap(_s.texture_s12, r.stress_12, r.material_mask, diverging=True)
    _upload_heatmap(_s.texture_vonmises, r.von_mises_stress, r.material_mask, diverging=False)


def _upload_heatmap(texture_tag, field: np.ndarray, mask: np.ndarray, diverging: bool):
    """
    Convert a 2-D numpy field (nx × ny) to a flat RGBA list and upload it to
    a DearPyGui dynamic texture.

    diverging=True -> blue-white-red colormap (for signed quantities)
    diverging=False -> black-yellow-white (for non-negative quantities)
    """
    nx, ny = field.shape

    # Resize field to heatmap dimensions via simple nearest-neighbour
    ix = np.round(np.linspace(0, nx - 1, HEATMAP_W)).astype(int)
    iy = np.round(np.linspace(0, ny - 1, HEATMAP_H)).astype(int)
    resampled = field[np.ix_(ix, iy)] # (HEATMAP_W, HEATMAP_H)
    mask_rs = mask[np.ix_(ix, iy)]

    vals = np.abs(resampled[mask_rs])
    vmax = np.percentile(vals, 98) if mask_rs.any() else 1.0
    if vmax < 1e-12:
        vmax = 1.0

    pixels = []
    for j in range(HEATMAP_H - 1, -1, -1):
        for i in range(HEATMAP_W):
            if not mask_rs[i, j]:
                pixels += [0.08, 0.08, 0.10, 1.0] # dark background
                continue

            t = float(resampled[i, j]) / vmax

            if diverging:
                r, g, b = _colormap_diverging(t)
            else:
                r, g, b = _colormap_sequential(t)

            pixels += [r, g, b, 1.0]

    dpg.set_value(texture_tag, pixels)


def _colormap_diverging(t: float):
    t = max(-1.0, min(1.0, t))
    if t < 0:
        s = -t
        return (1.0 - s, 1.0 - s, 1.0)
    else:
        return (1.0, 1.0 - t, 1.0 - t)


def _colormap_sequential(t: float):
    t = max(0.0, min(1.0, t))
    if t < 0.33:
        s = t / 0.33
        return (0.0, 0.0, s)
    elif t < 0.66:
        s = (t - 0.33) / 0.33
        return (0.0, s, 1.0 - s * 0.5)
    else:
        s = (t - 0.66) / 0.34
        return (s, 1.0, s)



# -------------- More helpers --------------------------
def _create_texture(w: int, h: int) -> int:
    blank = [0.08, 0.08, 0.10, 1.0] * (w * h)
    with dpg.texture_registry():
        return dpg.add_dynamic_texture(width=w, height=h, default_value=blank)


def _sync_canvas_width():
    if dpg.does_item_exist("analysis_image"):
        dpg.configure_item("analysis_image", width=dpg.get_viewport_width() - 20)


def _list_svgs() -> list[str]:
    if not os.path.isdir(OUTPUT_DIR):
        return []
    return sorted(f for f in os.listdir(OUTPUT_DIR) if f.endswith(".svg"))


def _set_status(msg: str, color: tuple):
    if dpg.does_item_exist("analysis_status"):
        dpg.set_value("analysis_status", msg)
        dpg.configure_item("analysis_status", color=color)


def _set_fem_status(msg: str, color: tuple):
    if dpg.does_item_exist("fem_status"):
        dpg.set_value("fem_status", msg)
        dpg.configure_item("fem_status", color=color)

