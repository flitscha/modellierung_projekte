"""
Grid Search optimisation over a Design's parameter space.
"""

import threading
from dataclasses import dataclass, field
from itertools import product

import numpy as np

from core.parameter import IntParameter
from optimization.objective import compute_loss


@dataclass
class ProgressUpdate:
    iteration: int
    best_loss: float
    best_params: dict
    best_result: dict
    grid_pct: float = 0.0 # 0–100, grid progress percentage


@dataclass
class OptimisationResult:
    success: bool
    message: str
    best_loss: float | None = None
    best_params: dict | None = None
    best_result: dict | None = None
    history_iterations: list[int] = field(default_factory=list)
    history_losses: list[float] = field(default_factory=list)


_GRID_STEPS = 10 # subdivisions per parameter -> _GRID_STEPS^n_params total evals


class OptimisationRun:
    def __init__(self, design, on_progress=None, on_done=None):
        self.design = design
        self.on_progress = on_progress
        self.on_done = on_done

        self._stop_flag = False
        self._thread: threading.Thread | None = None

        self.best_loss: float | None = None
        self.best_params: dict | None = None
        self.best_result: dict | None = None
        self._iterations: list[int] = []
        self._losses: list[float] = []
        self._counter = 0
        self._grid_pct: float = 0.0

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
        axes = self._build_axes()
        total = int(np.prod([len(a) for a in axes]))

        try:
            opt_result = self._search(axes, total)
        except StopIteration:
            opt_result = OptimisationResult(
                success=False, message="stopped by user",
                best_loss=self.best_loss, best_params=self.best_params,
                best_result=self.best_result,
                history_iterations=list(self._iterations),
                history_losses=list(self._losses),
            )
        except Exception as e:
            opt_result = OptimisationResult(success=False, message=str(e))

        if self.on_done is not None:
            self.on_done(opt_result)


    def _build_axes(self) -> list:
        axes = []
        for p in self.design.parameter_space():
            high = p.low + (p.high - p.low) / 2 # lower half only
            if isinstance(p, IntParameter):
                n = min(_GRID_STEPS, int(high) - p.low + 1)
                axes.append(np.round(np.linspace(p.low, int(high), n)).astype(int))
            else:
                axes.append(np.linspace(p.low, high, _GRID_STEPS))
        return axes


    def _search(self, axes, total) -> OptimisationResult:
        param_space = self.design.parameter_space()
        last_reported_pct = -1

        for eval_counter, combo in enumerate(product(*axes), start=1):
            if self._stop_flag:
                raise StopIteration

            pct = int(eval_counter / total * 100)
            if pct != last_reported_pct:
                last_reported_pct = pct
                self._grid_pct = float(pct)
                self._report_grid_pct(pct, eval_counter, total)

            params = {p.name: val for p, val in zip(param_space, combo)}
            self._evaluate(params)

        return OptimisationResult(
            success=True,
            message=f"grid search complete ({self._counter}/{total} valid evaluations)",
            best_loss=self.best_loss, best_params=self.best_params,
            best_result=self.best_result,
            history_iterations=list(self._iterations),
            history_losses=list(self._losses),
        )


    def _evaluate(self, params):
        if not self.design.validate(params):
            return

        result = compute_loss(self.design, params)
        if result is None:
            return

        loss = result["loss"]
        self._counter += 1

        if self.best_loss is None or loss < self.best_loss:
            self.best_loss = loss
            self.best_params = params
            self.best_result = result
            self._iterations.append(self._counter)
            self._losses.append(self.best_loss)

            if self.on_progress is not None:
                self.on_progress(ProgressUpdate(
                    iteration=self._counter,
                    best_loss=self.best_loss,
                    best_params=dict(params),
                    best_result=dict(result),
                    grid_pct=self._grid_pct,
                ))


    def _report_grid_pct(self, pct: int, eval_counter: int, total: int):
        if self.on_progress is not None:
            self.on_progress(ProgressUpdate(
                iteration=self._counter,
                best_loss=self.best_loss or 0.0,
                best_params=dict(self.best_params) if self.best_params else {},
                best_result=dict(self.best_result) if self.best_result else {},
                grid_pct=float(pct),
            ))
