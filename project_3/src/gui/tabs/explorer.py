"""
Design Explorer Tab:
Select an airfoil design, tweak parameters with sliders
"""
import os
import dearpygui.dearpygui as dpg

from core.parameter import IntParameter
from gui.airfoil_canvas import render_geometry, render_pressure_analysis
from simulations.solver import solve_panel_method
from simulations.simulate_in_range import evaluate_cl_range

CANVAS_W = 1000
CANVAS_H = 600


class _State:
    def __init__(self):
        self.design = None
        self.designs_by_name = {}
        self.params: dict = {}
        self.texture_tag = None
        self.dirty = False
        self.mode = "pressure"
        self.solver_enabled = True # panel-solver
        self.live_alpha = 0.0


_s = _State()


def build(parent_tag: str, designs: list):
    """Build the Design Explorer tab and register it under parent_tag."""
    _s.texture_tag = _create_texture()
    _s.designs_by_name = {d.name: d for d in designs}

    with dpg.tab(label="Design Explorer", parent=parent_tag, tag="tab_explorer"):
        dpg.add_spacer(height=6)
        _build_top_bar(designs, _s.designs_by_name)
        dpg.add_spacer(height=10)
        _build_canvas()
        dpg.add_spacer(height=14)
        _build_controls()

    _select_design(designs[0])


def tick():
    """Called every frame from the main loop. Redraws only when dirty."""
    _sync_canvas_width()
    if _s.dirty:
        _s.dirty = False
        _redraw()


def load_params(design_name: str, params: dict):
    """
    Loads parameters into the Explorer and marks it dirty for redraw.
    Called from the Optimisation tab
    """
    design = _s.designs_by_name.get(design_name)
    if design is None:
        return

    _select_design(design)
    _s.params = dict(params)

    for p in design.parameter_space():
        tag = f"slider_{p.name}"
        if dpg.does_item_exist(tag):
            val = params[p.name]
            dpg.set_value(tag, int(val) if isinstance(p, IntParameter) else float(val))

    _s.dirty = True


# ----------------- Layout builders ----------------------------
def _build_top_bar(designs, designs_by_name):
    with dpg.group(horizontal=True):
        dpg.add_text("Design:")
        dpg.add_combo(
            items=[d.name for d in designs],
            default_value=designs[0].name,
            width=160,
            callback=lambda s, v: _select_design(designs_by_name[v]),
        )
        dpg.add_spacer(width=30)
        dpg.add_text("View:")
        dpg.add_combo(
            items=["geometry", "pressure"], # For now only geometry, later "pressure_distribution"
            default_value="pressure",
            width=120,
            callback=lambda s, v: _set_mode(v),
        )
        dpg.add_spacer(width=20)
        dpg.add_checkbox(
            label="Live Simulation",
            default_value=True,
            callback=lambda s, v: _set_solver_mode(v),
        )
        dpg.add_spacer(width=20)
        dpg.add_text("Status:")
        dpg.add_spacer(width=5)
        dpg.add_text("", tag="explorer_status")


def _build_canvas():
    dpg.add_image(_s.texture_tag, tag="explorer_image", width=CANVAS_W, height=CANVAS_H)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=8)
        dpg.add_text("Max Thickness: ", color=(160, 160, 180))
        dpg.add_text("-- %", tag="explorer_thickness", color=(255, 200, 10))
        dpg.add_spacer(width=20)
        dpg.add_text("Max Camber: ", color=(160, 160, 180))
        dpg.add_text("-- %", tag="explorer_camber", color=(255, 200, 10))
        dpg.add_spacer(width=20)
        dpg.add_text("Live Cl (0°): ", color=(160, 160, 180))
        dpg.add_text("--", tag="explorer_mean_cl", color=(255, 200, 10))


def _build_controls():
    with dpg.group(horizontal=True):
        # Left side container for parameters and the new AoA control
        with dpg.group():
            dpg.add_text("Geometry Design Parameters", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=4)
            dpg.add_group(tag="slider_group")
            dpg.add_spacer(height=10)

            dpg.add_text("Simulation Parameters", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=4)
            # The new Angle of Attack slider (0° to 10°)
            dpg.add_slider_float(
                label="Angle of Attack (Alpha)",
                default_value=_s.live_alpha,
                min_value=-10.0,
                max_value=10.0,
                format="%.1f deg",
                width=340,
                callback=_on_alpha_slider,
                tag="slider_live_alpha"
            )

        dpg.add_spacer(width=40)
        _build_actions()


def _build_actions():
    # Use a horizontal layout container to place actions and detailed results side-by-side
    with dpg.group(horizontal=True):
        # Left side: Action Buttons
        with dpg.group():
            dpg.add_text("Actions", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=6)
            dpg.add_button(label="Analyse (0°-10°)", width=160, height=36, callback=_on_run_full_analysis)
            dpg.add_spacer(height=6)
            dpg.add_button(label="Export Selig", width=160, height=36, callback=_on_export_selig)
            dpg.add_spacer(height=6)
            dpg.add_button(label="Randomise", width=160, height=36, callback=_randomise)

        dpg.add_spacer(width=30)

        # Right side: Detailed Sweep Results (Populated when user clicks "Analyse")
        with dpg.group():
            dpg.add_text("Range Analysis Results (0° to 10°)", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=6)

            with dpg.group(horizontal=True):
                dpg.add_text("Minimum Cl: ", color=(160, 160, 180))
                dpg.add_text("N/A", tag="explorer_min_cl", color=(100, 220, 255))

            with dpg.group(horizontal=True):
                dpg.add_text("Maximum Cl: ", color=(160, 160, 180))
                dpg.add_text("N/A", tag="explorer_max_cl", color=(100, 220, 255))

            with dpg.group(horizontal=True):
                dpg.add_text("Average Cl: ", color=(160, 160, 180))
                dpg.add_text("N/A", tag="explorer_avg_cl", color=(100, 220, 255))

        dpg.add_spacer(width=30)

        # buttons to open matplotlib plots
        with dpg.group():
            dpg.add_text("Plots", color=(200, 200, 200))
            dpg.add_separator()
            dpg.add_spacer(height=6)
            dpg.add_button(label="Cl vs Alpha", width=140, height=36, callback=_on_plot_cl)
            dpg.add_spacer(height=6)
            dpg.add_button(label="Cp Distribution", width=140, height=36, callback=_on_plot_cp)


# -------------- Logic -----------------------
def _on_alpha_slider(sender, value):
    _s.live_alpha = value
    _s.dirty = True

def _select_design(design):
    _s.design = design
    _s.params = design.default_parameters()
    _rebuild_sliders(design)
    _s.dirty = True

def _set_mode(mode):
    _s.mode = mode
    _s.dirty = True

def _set_solver_mode(value):
    _s.solver_enabled = value
    _s.dirty = True

def _rebuild_sliders(design):
    dpg.delete_item("slider_group", children_only=True)

    for p in design.parameter_space():
        val = _s.params[p.name]
        kwargs = dict(
            label=p.name,
            tag=f"slider_{p.name}",
            min_value=p.low,
            max_value=p.high,
            width=340,
            callback=lambda s, v, u: _on_slider(u, v),
            user_data=p.name,
            parent="slider_group",
        )
        if isinstance(p, IntParameter):
            dpg.add_slider_int(default_value=int(val), **kwargs)
        else:
            dpg.add_slider_float(default_value=float(val), format="%.3f", **kwargs)


def _on_slider(param_name, value):
    _s.params[param_name] = value
    _s.dirty = True


def _randomise():
    if _s.design is None:
        return
    try:
        _s.params = _s.design.sample_parameters()
        for p in _s.design.parameter_space():
            tag = f"slider_{p.name}"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, _s.params[p.name])
        _s.dirty = True
    except ValueError:
        _set_status("Could not randomise", (255, 180, 0))


def _on_export_selig():
    if _s.design is None:
        return
    if not _s.design.validate(_s.params):
        _set_status("Cannot export — invalid parameters", (255, 180, 0))
        return

    export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "exports")
    os.makedirs(export_dir, exist_ok=True)

    airfoil = _s.design.build_airfoil(_s.params)
    filename = os.path.join(export_dir, f"{airfoil.name}.dat")
    airfoil.save_selig(filename)
    _set_status(f"Saved: {airfoil.name}.dat", (100, 220, 100))


def _on_run_full_analysis():
    """Triggered manually by the 'Analyse' button. Computes the expensive 0-10 deg sweep."""
    if _s.design is None:
        _set_status("Cannot analyse - no design loaded", (255, 180, 0))
        return

    _set_status("Analysing range...", (255, 200, 10))
    airfoil = _s.design.build_airfoil(_s.params)

    try:
        stats = evaluate_cl_range(airfoil, start_deg=0.0, end_deg=10.0, step_deg=1.0)

        # Populate the detailed panel labels with results
        if dpg.does_item_exist("explorer_min_cl"):
            dpg.set_value("explorer_min_cl", f"{stats['min_cl']:.4f}")
        if dpg.does_item_exist("explorer_max_cl"):
            dpg.set_value("explorer_max_cl", f"{stats['max_cl']:.4f}")
        if dpg.does_item_exist("explorer_avg_cl"):
            dpg.set_value("explorer_avg_cl", f"{stats['mean_cl']:.4f}")

        _set_status("Analysis complete", (0, 255, 0))
    except Exception as e:
        _set_status(f"Analysis error: {e}", (255, 100, 100))


def _on_plot_cl():
    if _s.design is None:
        return
    from gui.plots import show_cl_plot
    from simulations.simulate_in_range import evaluate_cl_range
    airfoil = _s.design.build_airfoil(_s.params)
    _set_status("Running sweep...", (255, 200, 10))
    try:
        stats = evaluate_cl_range(airfoil, start_deg=-10.0, end_deg=10.0, step_deg=1.0)
        show_cl_plot(airfoil.name, stats["alpha_range"], stats["all_cl"])
        _set_status("Plot opened", (100, 220, 100))
    except Exception as e:
        _set_status(f"Plot error: {e}", (255, 100, 100))


def _on_plot_cp():
    if _s.design is None:
        return
    from gui.plots import show_cp_plot
    airfoil = _s.design.build_airfoil(_s.params)
    try:
        results = solve_panel_method(airfoil, alpha_deg=_s.live_alpha)
        show_cp_plot(airfoil.name, _s.live_alpha, results["x_c"], results["cp"], results["y_c"])
        _set_status("Plot opened", (100, 220, 100))
    except Exception as e:
        _set_status(f"Plot error: {e}", (255, 100, 100))


def _redraw():
    _set_status("ok", (0, 255, 0))
    if _s.design is None:
        return

    if not _s.design.validate(_s.params):
        _set_status("Invalid parameters", (255, 180, 0))
    else:
        _set_status("Geometry OK", (0, 255, 0))

    airfoil = _s.design.build_airfoil(_s.params)

    # Update geometry numerical information strings
    dpg.set_value("explorer_thickness", f"{_s.params['thickness']*100:.1f} %")
    dpg.set_value("explorer_camber", f"{_s.params['camber']*100:.1f} %")

    # live calculations
    results = None
    if _s.solver_enabled:
        try:
            results = solve_panel_method(airfoil, alpha_deg=_s.live_alpha)
            live_cl = results["cl"]
            dpg.set_value("explorer_mean_cl", f"{live_cl:.4f}")
        except Exception as e:
            _set_status(f"Live solver error: {e}", (255, 100, 100))
            dpg.set_value("explorer_mean_cl", "--")
    else:
        dpg.set_value("explorer_mean_cl", "Disabled")


    # draw geometry
    if _s.mode == "geometry":
        pixel_data = render_geometry(airfoil, CANVAS_W, CANVAS_H, alpha_deg=_s.live_alpha)
        dpg.set_value(_s.texture_tag, pixel_data)
    if _s.mode == "pressure" and results is not None:
        pixel_data = render_pressure_analysis(airfoil, CANVAS_W, CANVAS_H, alpha_deg=_s.live_alpha, solver_results=results)
        dpg.set_value(_s.texture_tag, pixel_data)



# ----------------- Helpers ------------------------------
def _create_texture() -> int:
    blank = [0.12, 0.12, 0.16, 1.0] * (CANVAS_W * CANVAS_H)
    with dpg.texture_registry():
        return dpg.add_dynamic_texture(width=CANVAS_W, height=CANVAS_H, default_value=blank)


def _sync_canvas_width():
    global CANVAS_W
    new_w = max(400, dpg.get_viewport_width() - 40)
    if abs(new_w - CANVAS_W) > 10: # Only resize if change is significant
        CANVAS_W = new_w
        # Re-create texture to match new dimensions
        dpg.delete_item(_s.texture_tag)
        _s.texture_tag = _create_texture()
        dpg.configure_item("explorer_image", texture_tag=_s.texture_tag, width=CANVAS_W)
        _s.dirty = True # Force redraw for new size


def _set_status(msg: str, color: tuple):
    dpg.set_value("explorer_status", msg)
    dpg.configure_item("explorer_status", color=color)

