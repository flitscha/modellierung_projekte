"""
Design Explorer Tab
-------------------
Select a bridge design, tweak parameters with sliders, and instantly see:
  - A live rendered cross-section preview
  - Estimated weight
  - (Phase 2) Deflection analysis via the Analyse button
"""
import dearpygui.dearpygui as dpg

import config
from core.parameter import IntParameter
from gui.bridge_canvas import render_geometry

CANVAS_W = 1200
CANVAS_H = 150

_state = {
    "design": None,
    "params": {},
    "texture_tag": None,
}
_dirty = False



def tick():
    """
    Called every frame from the main loop. Renders only when dirty.
    This prevents the renderer from falling behind and ensures that
    only the current state is rendered.
    """
    global _dirty

    # always keep image width in sync with viewport
    vp_width = dpg.get_viewport_width()
    if dpg.does_item_exist("explorer_image"):
        dpg.configure_item("explorer_image", width=vp_width - 20)

    if _dirty:
        _dirty = False
        _do_refresh()


def _do_refresh():
    design = _state["design"]
    if design is None:
        return

    params = _state["params"]
    if not design.validate(params):
        _set_status("Invalid parameters", (255, 180, 0))
        return

    geometry   = design.build_geometry(params)
    pixel_data = render_geometry(geometry, CANVAS_W, CANVAS_H)
    dpg.set_value(_state["texture_tag"], pixel_data)

    # NOTE: weight-calculation is slow. Either find a better implementation,
    # or only calculate, when pressing a calculate-weight-button

    #weight = geometry.estimate_weight_grams()
    #dpg.set_value("explorer_weight", f"{weight:.2f} g")
    _set_status("Valid", (100, 220, 100))


def _set_status(msg, color):
    dpg.set_value("explorer_status", msg)
    dpg.configure_item("explorer_status", color=color)



# slider helpers
def _on_slider(param_name, value):
    _state["params"][param_name] = value
    global _dirty
    _dirty = True


def _build_sliders(design):
    dpg.delete_item("slider_group", children_only=True)
    _state["params"] = design.default_parameters()

    for p in design.parameter_space():
        val = _state["params"][p.name]
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
            dpg.add_slider_float(default_value=float(val),
                                 format="%.2f mm", **kwargs)

    global _dirty
    _dirty = True


def _on_design_selected(sender, app_data, designs_by_name):
    design = designs_by_name[app_data]
    _state["design"] = design
    _build_sliders(design)


def _randomise():
    design = _state["design"]
    if design is None:
        return
    try:
        sampled = design.sample_parameters()
        _state["params"] = sampled
        for p in design.parameter_space():
            tag = f"slider_{p.name}"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, sampled[p.name])
        global _dirty
        _dirty = True
    except ValueError:
        _set_status("⚠  Could not randomise", (255, 180, 0))



# build the GUI component
def build(parent_tag: str, designs: list):
    designs_by_name = {d.name: d for d in designs}

    # Texture registry must live at top level, not inside a window
    with dpg.texture_registry():
        blank = [0.12, 0.12, 0.16, 1.0] * (CANVAS_W * CANVAS_H)
        _state["texture_tag"] = dpg.add_dynamic_texture(
            width=CANVAS_W, height=CANVAS_H, default_value=blank
        )

    with dpg.tab(label="Design Explorer", parent=parent_tag):

        dpg.add_spacer(height=6)

        # ── top bar ─────────────────────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("Design:")
            dpg.add_combo(
                items=[d.name for d in designs],
                default_value=designs[0].name,
                width=160,
                callback=lambda s, v: _on_design_selected(s, v, designs_by_name),
            )
            dpg.add_spacer(width=30)
            dpg.add_text("Weight:")
            dpg.add_text("—", tag="explorer_weight")
            dpg.add_spacer(width=20)
            dpg.add_text("", tag="explorer_status")

        dpg.add_spacer(height=10)

        # canvas
        with dpg.group(tag="explorer_canvas_group"):
            dpg.add_image(_state["texture_tag"], tag="explorer_image", width=CANVAS_W, height=CANVAS_H)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                dpg.add_text(f"← {config.BRIDGE_LENGTH:.0f} mm →",
                             color=(160, 160, 180))
                dpg.add_spacer(width=20)
                dpg.add_text(f"height: {config.BRIDGE_HEIGHT:.0f} mm",
                             color=(160, 160, 180))

        dpg.add_spacer(height=14)

        # sliders + actions
        with dpg.group(horizontal=True):

            with dpg.group(tag="slider_group"):
                pass  # populated by _build_sliders()

            dpg.add_spacer(width=40)

            with dpg.group():
                dpg.add_text("Actions", color=(200, 200, 200))
                dpg.add_separator()
                dpg.add_spacer(height=6)

                dpg.add_button(
                    label="▶  Analyse",
                    width=160, height=36,
                    # TODO Phase 2: run FEM / Euler-Bernoulli simulation,
                    #               show deflection + stress heatmap
                    callback=lambda: _set_status(
                        "Analysis not yet implemented", (160, 160, 180)
                    ),
                )
                dpg.add_spacer(height=6)

                dpg.add_button(
                    label="⬇  Export SVG",
                    width=160, height=36,
                    # TODO: call svg_exporter with current geometry
                    callback=lambda: _set_status(
                        "SVG export not yet implemented", (160, 160, 180)
                    ),
                )
                dpg.add_spacer(height=6)

                dpg.add_button(
                    label="⟳  Randomise",
                    width=160,
                    callback=_randomise,
                )

    _state["design"] = designs[0]
    _build_sliders(designs[0])

