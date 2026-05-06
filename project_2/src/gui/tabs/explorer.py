"""
Design Explorer Tab:
Select a bridge design, tweak parameters with sliders
"""
import dearpygui.dearpygui as dpg

import config
from core.parameter import IntParameter
from gui.bridge_canvas import render_geometry, render_truss
from export.svg_exporter import export_svg
from simulations.solve_truss import solve_truss

CANVAS_W = 1200
CANVAS_H = 150


class _State:
    def __init__(self):
        self.design = None
        self.params: dict = {}
        self.texture_tag = None
        self.dirty = False
        self.mode = "geometry"
        self.solver_enabled = True # truss-solver


_s = _State()


def build(parent_tag: str, designs: list):
    """Build the Design Explorer tab and register it under parent_tag."""
    _s.texture_tag = _create_texture()
    designs_by_name = {d.name: d for d in designs}

    with dpg.tab(label="Design Explorer", parent=parent_tag):
        dpg.add_spacer(height=6)
        _build_top_bar(designs, designs_by_name)
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
            items=["geometry", "truss"],
            default_value="geometry",
            width=120,
            callback=lambda s, v: _set_mode(v),
        )
        dpg.add_spacer(width=20)
        dpg.add_checkbox(
            label="Live Simulation",
            default_value=True,
            callback=lambda s, v: _set_truss_mode(v),
        )
        dpg.add_spacer(width=20)
        dpg.add_text("Status:")
        dpg.add_spacer(width=5)
        dpg.add_text("", tag="explorer_status")


def _build_canvas():
    dpg.add_image(_s.texture_tag, tag="explorer_image", width=CANVAS_W, height=CANVAS_H)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=8)
        dpg.add_text(f"length: {config.BRIDGE_LENGTH:.0f} mm", color=(160, 160, 180))
        dpg.add_spacer(width=20)
        dpg.add_text(f"height: {config.BRIDGE_HEIGHT:.0f} mm", color=(160, 160, 180))
        dpg.add_spacer(width=20)
        dpg.add_text("Deflection: ", color=(160, 160, 180))
        dpg.add_text("-- mm", tag="explorer_deflection", color=(255, 200, 10))
        dpg.add_spacer(width=20)
        dpg.add_text("Weight: ", color=(160, 160, 180))
        dpg.add_text("-- g", tag="explorer_weight", color=(255, 200, 10))


def _build_controls():
    with dpg.group(horizontal=True):
        dpg.add_group(tag="slider_group")
        dpg.add_spacer(width=40)
        _build_actions()


def _build_actions():
    with dpg.group():
        dpg.add_text("Actions", color=(200, 200, 200))
        dpg.add_separator()
        dpg.add_spacer(height=6)
        dpg.add_button(label="Analyse", width=160, height=36, callback=_on_analyse)
        dpg.add_spacer(height=6)
        dpg.add_button(label="Export SVG", width=160, height=36, callback=_on_export_svg)
        dpg.add_spacer(height=6)
        dpg.add_button(label="Randomise", width=160, height=36, callback=_randomise)



# -------------- Logic -----------------------
def _select_design(design):
    _s.design = design
    _s.params = design.default_parameters()
    _rebuild_sliders(design)
    _s.dirty = True

def _set_mode(mode):
    _s.mode = mode
    _s.dirty = True

def _set_truss_mode(value):
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
            dpg.add_slider_float(default_value=float(val), format="%.2f mm", **kwargs)


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


def _on_analyse():
    if _s.design is None:
        return
    if not _s.design.validate(_s.params):
        _set_status("Cannot analyse — invalid parameters", (255, 180, 0))
        return
    # Import here to avoid circular imports at module load time
    from gui.tabs import analysis
    geometry = _s.design.build_geometry(_s.params)
    try:
        truss = _s.design.build_truss(_s.params)
        analysis.load_design(geometry, truss)
    except NotImplementedError:
        analysis.load_geometry(geometry)


def _on_export_svg():
    if _s.design is None:
        return
    if not _s.design.validate(_s.params):
        _set_status("Cannot export — invalid parameters", (255, 180, 0))
        return
    geometry = _s.design.build_geometry(_s.params)
    path = export_svg(geometry, _s.design.name)
    _set_status(f"Saved: {path}", (100, 220, 100))


def _redraw():
    _set_status("ok", (0, 255, 0))
    if _s.design is None:
        return

    if not _s.design.validate(_s.params):
        _set_status("Invalid parameters", (255, 180, 0))
        return

    # draw geometry (or truss)
    geometry = _s.design.build_geometry(_s.params)
    if _s.mode == "geometry":
        pixel_data = render_geometry(geometry, CANVAS_W, CANVAS_H)
        dpg.set_value(_s.texture_tag, pixel_data)
    else:
        try:
            truss = _s.design.build_truss(_s.params)
            pixel_data = render_truss(truss, CANVAS_W, CANVAS_H)
            dpg.set_value(_s.texture_tag, pixel_data)
        except NotImplementedError:
            _set_status("truss not implemented for this design", (255, 0, 0))
            return

    # Truss solver (optional)
    if not _s.solver_enabled:
        return
    try: # TODO: clean up and understand this code
        # weight calculation
        weight = geometry.estimate_weight_grams()

        dpg.set_value(
            "explorer_weight",
            f"{weight:.1f} g"
        )

        # truss solver
        truss = _s.design.build_truss(_s.params)

        # --- middle bottom node ---
        xs = [n.x for n in truss.nodes]
        min_x, max_x = min(xs), max(xs)
        mid_x = 0.5 * (min_x + max_x)

        bottom_nodes = [i for i, n in enumerate(truss.nodes) if n.y == 0]
        mid_node = min(bottom_nodes, key=lambda i: abs(truss.nodes[i].x - mid_x))

        # --- load ---
        F = 5.0 * 9.81
        forces = {mid_node: (0.0, -F)}

        # --- supports ---
        left = min(bottom_nodes, key=lambda i: truss.nodes[i].x)
        right = max(bottom_nodes, key=lambda i: truss.nodes[i].x)

        fixed_dofs = [
            (left, 0), (left, 1),
            (right, 1)
        ]

        # --- solve ---
        displacements, _ = solve_truss(
            truss,
            forces,
            fixed_dofs,
            E=2500.0
        )

        # --- max deflection ---
        max_defl = max(abs(d[1]) for d in displacements)
        dpg.set_value(
            "explorer_deflection",
            f"{max_defl:.3f} mm"
        )

    except Exception as e:
        _set_status(f"Truss-solver error: {e}", (255, 100, 100))
        dpg.set_value("explorer_deflection", "-- mm")


# ----------------- Helpers ------------------------------
def _create_texture() -> int:
    blank = [0.12, 0.12, 0.16, 1.0] * (CANVAS_W * CANVAS_H)
    with dpg.texture_registry():
        return dpg.add_dynamic_texture(width=CANVAS_W, height=CANVAS_H, default_value=blank)


def _sync_canvas_width():
    if dpg.does_item_exist("explorer_image"):
        dpg.configure_item("explorer_image", width=dpg.get_viewport_width() - 20)


def _set_status(msg: str, color: tuple):
    dpg.set_value("explorer_status", msg)
    dpg.configure_item("explorer_status", color=color)

