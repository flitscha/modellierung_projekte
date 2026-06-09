"""
Airfoil Design Tool - main window.
Tabs:
    Design Explorer - interactive parameter sliders + live preview
    Optimizer       - lift maximisation under geometric constraints (Coming soon)
"""
import dearpygui.dearpygui as dpg
from gui.tabs import explorer, optimization, xfoil_comparison


def run(designs: list):
    dpg.create_context()
    dpg.create_viewport(
        title="Airfoil Design & Optimization Tool",
        width=1000,
        height=700,
        resizable=True,
    )
    dpg.setup_dearpygui()
    _apply_theme()

    with dpg.window(tag="main_window", no_title_bar=True, no_move=True, no_resize=True, no_close=True):
        dpg.add_text("Airfoil Design Tool", color=(200, 220, 255))
        dpg.add_separator()
        dpg.add_spacer(height=4)

        with dpg.tab_bar(tag="main_tabs"):
            explorer.build("main_tabs", designs)
            optimization.build("main_tabs", designs)
            xfoil_comparison.build("main_tabs", designs)

    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    # Render-Schleife: Ruft tick() für jeden aktiven Tab auf
    while dpg.is_dearpygui_running():
        explorer.tick()
        optimization.tick()
        xfoil_comparison.tick()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


def _apply_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (22, 22, 30))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (30, 30, 45))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (40, 90, 160))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 40, 55))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (55, 55, 75))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 100, 180))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 130, 210))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (80, 160, 220))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (35, 35, 50))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (50, 100, 180))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
    dpg.bind_theme(global_theme)