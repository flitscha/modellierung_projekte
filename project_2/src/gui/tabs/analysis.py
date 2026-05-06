"""
Displays a bridge geometry and runs structural analysis on it.

Two ways to load a design:
    1. Via the Explorer tab -> "Analyse" button (geometry passed directly)
    2. Via the SVG dropdown (SVG parsed back to Geometry)
"""
import os
import dearpygui.dearpygui as dpg

import config
from core.geometry import Geometry
from simulations.solve_truss import solve_truss
from gui.bridge_canvas import render_geometry
from export.svg_parser import parse_svg
from export.svg_exporter import OUTPUT_DIR

CANVAS_W = 1200
CANVAS_H = 150


class _State:
    def __init__(self):
        self.geometry: Geometry | None = None
        self.truss = None
        self.texture_tag = None
        self.dirty = False


_s = _State()


def build(parent_tag: str):
    """Build the Analysis tab and register it under parent_tag."""
    _s.texture_tag = _create_texture()

    with dpg.tab(label="Analysis", parent=parent_tag, tag="tab_analysis"):
        dpg.add_spacer(height=6)
        _build_top_bar()
        dpg.add_spacer(height=10)
        _build_canvas()
        dpg.add_spacer(height=14)
        _build_results()


def tick():
    """Called every frame from the main loop. Redraws only when dirty."""
    _sync_canvas_width()
    if _s.dirty:
        _s.dirty = False
        _redraw()


def load_geometry(geometry: Geometry):
    """
    Called by the Explorer tab when the user clicks 'Analyse'.
    Switches focus to this tab and displays the geometry immediately.
    """
    _s.geometry = geometry
    _s.dirty = True
    _set_status("Loaded from Explorer", (100, 220, 100))
    dpg.set_value("main_tabs", "tab_analysis")


def load_design(geometry, truss):
    _s.geometry = geometry
    _s.truss = truss
    _s.dirty = True
    _set_status("Loaded from Explorer", (100, 220, 100))
    dpg.set_value("main_tabs", "tab_analysis")


# --------------- Layout Builders -------------------
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


def _build_canvas():
    dpg.add_image(_s.texture_tag, tag="analysis_image", width=CANVAS_W, height=CANVAS_H)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=8)
        dpg.add_text(f"length: {config.BRIDGE_LENGTH:.0f} mm", color=(160, 160, 180))
        dpg.add_spacer(width=20)
        dpg.add_text(f"height: {config.BRIDGE_HEIGHT:.0f} mm", color=(160, 160, 180))


def _build_results():
    """Placeholder panels for results."""
    dpg.add_text("Results", color=(200, 200, 200))
    dpg.add_separator()
    dpg.add_spacer(height=6)

    with dpg.group(horizontal=True):
        _build_result_card("Weight", "-- g", "analysis_weight")
        dpg.add_spacer(width=40)
        _build_result_card("Max Deflection", "-- mm", "analysis_deflection")

    dpg.add_spacer(height=14)

    # stress heatmap images will go here
    dpg.add_text("Stress heatmaps - not implemented yet", color=(100, 100, 120))


def _build_result_card(label: str, placeholder: str, tag: str):
    with dpg.group():
        dpg.add_text(label, color=(160, 160, 180))
        dpg.add_text(placeholder, tag=tag)


# -------------------- Logic ------------------------
def _on_svg_selected(sender, svg_filename):
    if not svg_filename:
        return
    path = os.path.join(OUTPUT_DIR, svg_filename)
    try:
        _s.geometry = parse_svg(path)
        _s.dirty = True
        _set_status(f"Loaded: {svg_filename}", (100, 220, 100))
    except Exception as e:
        _set_status(f"Error: {e}", (255, 100, 100))


def _refresh_svg_list():
    svgs = _list_svgs()
    dpg.configure_item("analysis_svg_combo", items=svgs)


def _redraw():
    if _s.geometry is None:
        return

    # --- render geometry (for now) ---
    pixel_data = render_geometry(_s.geometry, CANVAS_W, CANVAS_H)
    dpg.set_value(_s.texture_tag, pixel_data)

    # --- weight ---
    weight = _s.geometry.estimate_weight_grams()
    dpg.set_value("analysis_weight", f"{weight:.1f} g")

    # --- solver ---
    if _s.truss is None:
        dpg.set_value("analysis_deflection", "-- mm")
        return

    try:
        truss = _s.truss
        n = len(truss.nodes)

        # --- find middle bottom node ---
        xs = [node.x for node in truss.nodes]
        min_x, max_x = min(xs), max(xs)
        mid_x = 0.5 * (min_x + max_x)

        # choose closest bottom node
        bottom_nodes = [i for i, node in enumerate(truss.nodes) if node.y == 0]
        mid_node = min(bottom_nodes, key=lambda i: abs(truss.nodes[i].x - mid_x))

        # --- forces ---
        F = 5.0 * 9.81  # Newton
        forces = {
            mid_node: (0.0, -F)
        }

        # --- supports ---
        left_node = min(bottom_nodes, key=lambda i: truss.nodes[i].x)
        right_node = max(bottom_nodes, key=lambda i: truss.nodes[i].x)

        fixed_dofs = [
            (left_node, 0), (left_node, 1),   # fixed
            (right_node, 1)                  # roller
        ]

        # --- solve ---
        displacements, _ = solve_truss(truss, forces, fixed_dofs, E=2500.0)

        # --- max deflection (y) ---
        max_defl = min(d[1] for d in displacements)  # negative value
        max_defl_mm = abs(max_defl)

        dpg.set_value("analysis_deflection", f"{max_defl_mm:.3f} mm")

        _set_status("Solved", (100, 220, 100))

    except Exception as e:
        _set_status(f"Solver error: {e}", (255, 100, 100))
        dpg.set_value("analysis_deflection", "-- mm")


# ----------------- Helpers --------------------------
def _list_svgs() -> list[str]:
    """Return sorted list of SVG filenames from the exports folder."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    return sorted(f for f in os.listdir(OUTPUT_DIR) if f.endswith(".svg"))


def _create_texture() -> int:
    blank = [0.12, 0.12, 0.16, 1.0] * (CANVAS_W * CANVAS_H)
    with dpg.texture_registry():
        return dpg.add_dynamic_texture(width=CANVAS_W, height=CANVAS_H, default_value=blank)


def _sync_canvas_width():
    if dpg.does_item_exist("analysis_image"):
        dpg.configure_item("analysis_image", width=dpg.get_viewport_width() - 20)


def _set_status(msg: str, color: tuple):
    dpg.set_value("analysis_status", msg)
    dpg.configure_item("analysis_status", color=color)

