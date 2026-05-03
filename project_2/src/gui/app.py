"""
Bridge Design Tool — main window.

Tabs
----
  Design Explorer  – interactive parameter sliders + live preview  (Phase 1)
  Analysis         – FEM deflection & stress simulation            (Phase 2)
  Optimizer        – weight minimisation under deflection budget   (Phase 3)
"""
import dearpygui.dearpygui as dpg

from gui.tabs import explorer


def run(designs: list):
    dpg.create_context()
    dpg.create_viewport(
        title="Bridge Design Tool",
        width=920,
        height=620,
        resizable=True,
    )
    dpg.setup_dearpygui()

    _apply_theme()

    with dpg.window(tag="main_window", no_title_bar=True, no_move=True,
                    no_resize=True, no_close=True):
        dpg.add_text("Bridge Design Tool", color=(200, 220, 255))
        dpg.add_separator()
        dpg.add_spacer(height=4)

        with dpg.tab_bar(tag="main_tabs"):
            explorer.build("main_tabs", designs)
            #analysis.build("main_tabs")
            #optimizer.build("main_tabs")

    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    # Manual render loop - lets explorer.tick() run every frame in main thread
    while dpg.is_dearpygui_running():
        explorer.tick()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


def _apply_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (22, 22, 30))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (30, 30, 45))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (40, 90, 160))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 40, 55))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,(55, 55, 75))
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

