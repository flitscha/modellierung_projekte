import dearpygui.dearpygui as dpg

from gui.bridge_canvas import render_geometry
from optimization.solver import OptimisationRun, ProgressUpdate, OptimisationResult

CANVAS_W = 1200
CANVAS_H = 150

_TAG_LOSS_AXIS_X = "opt_x_axis"
_TAG_LOSS_AXIS_Y = "opt_y_axis"
_TAG_LOSS_SERIES = "opt_loss_series"


class _State:
    def __init__(self):
        self.design = None
        self.designs_by_name = {}
        self.texture_tag = None
        self.run: OptimisationRun | None = None

        self.pending_progress: ProgressUpdate | None = None
        self.pending_done: OptimisationResult | None = None


_s = _State()


def build(parent_tag: str, designs: list):
    _s.designs_by_name = {d.name: d for d in designs}
    _s.texture_tag = _create_texture()

    with dpg.tab(label="Optimisation", parent=parent_tag):
        dpg.add_spacer(height=6)
        _build_top_bar(designs)
        dpg.add_spacer(height=10)
        _build_loss_plot()
        dpg.add_spacer(height=14)
        _build_best_result_panel()

    _select_design(designs[0])


def tick():
    _sync_canvas_width()

    progress = _s.pending_progress
    if progress is not None:
        _s.pending_progress = None
        _update_plot(progress)
        _update_best_panel(progress)

    done = _s.pending_done
    if done is not None:
        _s.pending_done = None
        _on_run_finished(done)


# ----------------- Layout builders ----------------------------
def _build_top_bar(designs):
    with dpg.group(horizontal=True):
        dpg.add_text("Design:")
        dpg.add_combo(
            items=[d.name for d in designs],
            default_value=designs[0].name,
            width=160,
            callback=lambda s, v: _select_design(_s.designs_by_name[v]),
        )
        dpg.add_spacer(width=30)
        dpg.add_button(label="Start", tag="opt_btn_start",
                       width=110, height=32, callback=_on_start)
        dpg.add_spacer(width=8)
        dpg.add_button(label="Stop", tag="opt_btn_stop",
                       width=110, height=32, callback=_on_stop, enabled=False)
        dpg.add_spacer(width=30)
        dpg.add_text("Status:", color=(160, 160, 180))
        dpg.add_spacer(width=4)
        dpg.add_text("idle", tag="opt_status", color=(160, 160, 180))


def _build_loss_plot():
    dpg.add_text("Loss over iterations", color=(200, 200, 200))
    with dpg.plot(height=220, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Iteration", tag=_TAG_LOSS_AXIS_X)
        dpg.add_plot_axis(dpg.mvYAxis, label="Loss", tag=_TAG_LOSS_AXIS_Y)
        dpg.add_line_series([], [], label="Best loss",
                            parent=_TAG_LOSS_AXIS_Y, tag=_TAG_LOSS_SERIES)


def _build_best_result_panel():
    dpg.add_text("Best solution found", color=(200, 200, 200))
    dpg.add_separator()
    dpg.add_spacer(height=6)

    with dpg.group(horizontal=True):
        with dpg.group():
            dpg.add_text("Metrics", color=(180, 180, 180))
            dpg.add_spacer(height=4)
            for label, tag in [
                ("Loss", "opt_best_loss"),
                ("Deflection", "opt_best_deflection"),
                ("Mass", "opt_best_mass"),
                ("Feasible", "opt_best_feasible"),
            ]:
                with dpg.group(horizontal=True):
                    dpg.add_text(f"{label}:", color=(160, 160, 180), indent=10)
                    dpg.add_text("--", tag=tag, color=(255, 200, 10))

        dpg.add_spacer(width=40)

        with dpg.group():
            dpg.add_text("Parameters", color=(180, 180, 180))
            dpg.add_spacer(height=4)
            dpg.add_group(tag="opt_best_params_group")

    dpg.add_spacer(height=14)
    dpg.add_text("Bridge preview  (shown when run completes)", color=(180, 180, 180))
    dpg.add_spacer(height=4)
    dpg.add_image(_s.texture_tag, tag="opt_canvas", width=CANVAS_W, height=CANVAS_H)


# -------------- Logic -----------------------
def _select_design(design):
    if _s.run is not None and _s.run.running:
        _s.run.stop(join_timeout=2.0)
    _s.design = design
    _s.run = None
    _reset_ui()
    _set_status("idle", (160, 160, 180))
    dpg.configure_item("opt_btn_start", enabled=True)
    dpg.configure_item("opt_btn_stop", enabled=False)


def _on_start():
    if _s.design is None or (_s.run is not None and _s.run.running):
        return
    _reset_ui()
    _set_status("running...", (100, 220, 100))
    dpg.configure_item("opt_btn_start", enabled=False)
    dpg.configure_item("opt_btn_stop", enabled=True)

    _s.run = OptimisationRun(
        design=_s.design,
        on_progress=_on_progress,
        on_done=_on_done,
    )
    _s.run.start()


def _on_stop():
    if _s.run is not None:
        _s.run.stop(join_timeout=0)
    _set_status("stopping …", (255, 200, 10))


def _on_progress(update: ProgressUpdate):
    _s.pending_progress = update


def _on_done(result: OptimisationResult):
    _s.pending_done = result


def _update_plot(progress: ProgressUpdate):
    if _s.run is None:
        return
    xs = list(_s.run._iterations)
    ys = list(_s.run._losses)
    if len(xs) < 2:
        return
    dpg.set_value(_TAG_LOSS_SERIES, [xs, ys])
    dpg.fit_axis_data(_TAG_LOSS_AXIS_X)
    dpg.fit_axis_data(_TAG_LOSS_AXIS_Y)


def _update_best_panel(progress: ProgressUpdate):
    r = progress.best_result
    feasible = r["feasible"]
    defl_color = (100, 220, 100) if feasible else (255, 100, 100)

    dpg.set_value("opt_best_loss", f"{r['loss']:.4f}")
    dpg.set_value("opt_best_deflection", f"{r['deflection_mm']:.3f} mm")
    dpg.configure_item("opt_best_deflection", color=defl_color)
    dpg.set_value("opt_best_mass", f"{r['mass_g']:.1f} g")
    dpg.set_value("opt_best_feasible", "yes" if feasible else "no")
    dpg.configure_item("opt_best_feasible", color=(100, 220, 100) if feasible else (255, 100, 100))

    dpg.delete_item("opt_best_params_group", children_only=True)
    for name, val in progress.best_params.items():
        with dpg.group(horizontal=True, parent="opt_best_params_group"):
            dpg.add_text(f"{name}:", color=(160, 160, 180), indent=10)
            text = f"{val:.2f} mm" if isinstance(val, float) else str(val)
            dpg.add_text(text, color=(255, 200, 10))


def _on_run_finished(result: OptimisationResult):
    if result.success:
        _set_status("done", (100, 220, 100))
    elif result.message == "stopped by user":
        _set_status("stopped", (255, 200, 10))
    else:
        _set_status(f"error: {result.message}", (255, 100, 100))

    dpg.configure_item("opt_btn_start", enabled=True)
    dpg.configure_item("opt_btn_stop", enabled=False)

    # draw canvas
    if result.best_params is not None and _s.design is not None:
        try:
            geometry = _s.design.build_geometry(result.best_params)
            pixel_data = render_geometry(geometry, CANVAS_W, CANVAS_H)
            dpg.set_value(_s.texture_tag, pixel_data)
        except Exception:
            pass


# ----------------- Helpers ------------------------------
def _reset_ui():
    if dpg.does_item_exist(_TAG_LOSS_SERIES):
        dpg.set_value(_TAG_LOSS_SERIES, [[], []])
    for tag in ("opt_best_loss", "opt_best_deflection",
                "opt_best_mass", "opt_best_feasible"):
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, "--")
            dpg.configure_item(tag, color=(255, 200, 10))
    if dpg.does_item_exist("opt_best_params_group"):
        dpg.delete_item("opt_best_params_group", children_only=True)
    if _s.texture_tag is not None:
        blank = [0.12, 0.12, 0.16, 1.0] * (CANVAS_W * CANVAS_H)
        dpg.set_value(_s.texture_tag, blank)


def _create_texture() -> int:
    blank = [0.12, 0.12, 0.16, 1.0] * (CANVAS_W * CANVAS_H)
    with dpg.texture_registry():
        return dpg.add_dynamic_texture(width=CANVAS_W, height=CANVAS_H, default_value=blank)


def _sync_canvas_width():
    if dpg.does_item_exist("opt_canvas"):
        dpg.configure_item("opt_canvas", width=dpg.get_viewport_width() - 20)


def _set_status(msg: str, color: tuple):
    if dpg.does_item_exist("opt_status"):
        dpg.set_value("opt_status", msg)
        dpg.configure_item("opt_status", color=color)

