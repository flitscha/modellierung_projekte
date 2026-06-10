import threading
import time
from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import minimize

from optimization.objective import compute_loss

@dataclass
class ProgressUpdate:
    iteration: int
    best_loss: float
    best_params: dict
    best_result: dict
    grid_pct: float = 0.0


@dataclass
class OptimisationResult:
    success: bool
    message: str
    best_loss: float | None = None
    best_params: dict | None = None
    best_result: dict | None = None
    history_iterations: list[int] = field(default_factory=list)
    history_losses: list[float] = field(default_factory=list)


class OptimisationRun:
    def __init__(self, design, on_progress=None, on_done=None):
        self.design = design
        self.on_progress = on_progress
        self.on_done = on_done

        self._stop_flag = False
        self._thread: threading.Thread | None = None
        self.best_loss, self.best_params, self.best_result = None, None, None
        self._iterations, self._losses = [], []
        self._counter = 0

    def start(self):
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, join_timeout: float = 2.0):
        self._stop_flag = True
        if self._thread is not None:
            self._thread.join(timeout=join_timeout)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        param_space = self.design.parameter_space()
        p_names = [p.name for p in param_space]
        bounds = [(p.low, p.high) for p in param_space]

        # use default-values as starting values
        defaults = self.design.default_parameters()
        x0 = np.array([defaults[name] for name in p_names])

        def target_function(x):
            if self._stop_flag:
                raise StopIteration("User stopped")

            self._counter += 1
            current_params = {name: val for name, val in zip(p_names, x)}
            res = compute_loss(self.design, current_params)

            # penalty, if something went wrong
            if res is None:
                return 10.0

            if self.best_loss is None or res["loss"] < self.best_loss:
                self.best_loss = res["loss"]
                self.best_params = current_params
                self.best_result = res
                self._iterations.append(self._counter)
                self._losses.append(self.best_loss)
            return res["loss"]

        # callback for live-UI-Updates after each step
        def ui_callback(xk):
            if self.on_progress and self.best_params:
                pct = min(99.0, (self._counter / 100) * 100.0)
                self.on_progress(ProgressUpdate(
                    iteration=self._counter, best_loss=self.best_loss,
                    best_params=dict(self.best_params), best_result=dict(self.best_result),
                    grid_pct=pct
                ))
            time.sleep(0.01)

        # use minimize from SciPy
        try:
            res = minimize(
                target_function, x0, method='Nelder-Mead',
                bounds=bounds, callback=ui_callback, options={'maxiter': 80}
            )
            opt_result = OptimisationResult(
                success=res.success, message=f"SciPy: {res.message}",
                best_loss=self.best_loss, best_params=self.best_params, best_result=self.best_result,
                history_iterations=list(self._iterations), history_losses=list(self._losses)
            )
        except StopIteration:
            opt_result = OptimisationResult(
                success=False, message="stopped by user",
                best_loss=self.best_loss, best_params=self.best_params, best_result=self.best_result,
                history_iterations=list(self._iterations), history_losses=list(self._losses)
            )
        except Exception as e:
            opt_result = OptimisationResult(success=False, message=str(e))

        if self.on_done:
            self.on_done(opt_result)

