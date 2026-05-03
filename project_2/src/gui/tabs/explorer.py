"""
Design Explorer Tab:
Select a bridge design, tweak parameters with sliders
"""
import dearpygui.dearpygui as dpg

import config
from core.parameter import IntParameter
from gui.bridge_canvas import render_geometry

CANVAS_W = 1200
CANVAS_H = 150


class _State:
    def __init__(self):
        self.design = None
        self.params: dict = {}
        self.texture_tag = None
        self.dirty = False


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
        dpg.add_text("Status:")
        dpg.add_text("", tag="explorer_status")


def _build_canvas():
    dpg.add_image(_s.texture_tag, tag="explorer_image", width=CANVAS_W, height=CANVAS_H)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=8)
        dpg.add_text(f"length: {config.BRIDGE_LENGTH:.0f} mm", color=(160, 160, 180))
        dpg.add_spacer(width=20)
        dpg.add_text(f"height: {config.BRIDGE_HEIGHT:.0f} mm", color=(160, 160, 180))


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
        dpg.add_button(
            label="Analyse",
            width=160, height=36,
            # TODO: call function to analyze the current geometry
            callback=lambda: _set_status("Analysis not yet implemented", (160, 160, 180)),
        )
        dpg.add_spacer(height=6)
        dpg.add_button(
            label="Export SVG",
            width=160, height=36,
            # TODO: call svg_exporter with current geometry
            callback=lambda: _set_status("SVG export not yet implemented", (160, 160, 180)),
        )
        dpg.add_spacer(height=6)
        dpg.add_button(label="Randomise", width=160, height=36, callback=_randomise)



# -------------- Logic -----------------------
def _select_design(design):
    _s.design = design
    _s.params = design.default_parameters()
    _rebuild_sliders(design)
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


def _redraw():
    if _s.design is None:
        return
    if not _s.design.validate(_s.params):
        _set_status("Invalid parameters", (255, 180, 0))
        return
    geometry = _s.design.build_geometry(_s.params)
    pixel_data = render_geometry(geometry, CANVAS_W, CANVAS_H)
    dpg.set_value(_s.texture_tag, pixel_data)
    _set_status("Valid", (100, 220, 100))


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

