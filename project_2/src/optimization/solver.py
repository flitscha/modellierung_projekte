"""
Runs Nelder-Mead optimisation over a Design's parameter space.

Numerical robustness:
failures are caught and penalised
"""

import threading
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from core.parameter import IntParameter
from optimization.objective import compute_loss


@dataclass
class ProgressUpdate:
    iteration: int
    best_loss: float
    best_params: dict
    best_result: dict


@dataclass
class OptimisationResult:
    success: bool
    message: str
    best_loss: float | None = None
    best_params: dict  | None = None
    best_result: dict  | None = None
    history_iterations: list[int] = field(default_factory=list)
    history_losses: list[float] = field(default_factory=list)


class OptimisationRun:
    def __init__(self, design, on_progress=None, on_done=None, max_iter=2000):
        self.design = design
        self.on_progress = on_progress
        self.on_done = on_done
        self.max_iter = max_iter

        self._stop_flag = False
        self._thread: threading.Thread | None = None

        self.best_loss: float | None = None
        self.best_params: dict | None = None
        self.best_result: dict | None = None
        self._iterations: list[int] = []
        self._losses: list[float] = []
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
        design = self.design
        param_space = design.parameter_space()
        x0 = np.array([design.default_parameters()[p.name] for p in param_space], dtype=float)
        scales = np.array([p.high - p.low for p in param_space], dtype=float)

        try:
            minimize(
                self._objective,
                x0,
                method="Nelder-Mead",
                options={
                    "maxiter": self.max_iter,
                    "xatol": 1e-3,
                    "fatol": 1e-4,
                    "initial_simplex": _build_simplex(x0, scales, param_space),
                    "adaptive": True,
                },
            )
            result = OptimisationResult(
                success=True, message="converged",
                best_loss=self.best_loss, best_params=self.best_params,
                best_result=self.best_result,
                history_iterations=list(self._iterations),
                history_losses=list(self._losses),
            )
        except StopIteration:
            result = OptimisationResult(
                success=False, message="stopped by user",
                best_loss=self.best_loss, best_params=self.best_params,
                best_result=self.best_result,
                history_iterations=list(self._iterations),
                history_losses=list(self._losses),
            )
        except Exception as e:
            result = OptimisationResult(success=False, message=str(e))

        if self.on_done is not None:
            self.on_done(result)

    def _objective(self, x) -> float:
        """
        Given parameters x, we need to determine how good these parameters are.
        """
        if self._stop_flag:
            raise StopIteration

        params = _vec_to_params(x, self.design.parameter_space())

        # validate geometry rules
        if not self.design.validate(params):
            return 1e6

        # solver (catches singular matrix)
        result = compute_loss(self.design, params)
        if result is None:
            return 1e6

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
                ))

        return loss


# ----------------- Helpers ------------------------------
def _build_simplex(x0: np.ndarray, scales: np.ndarray, param_space) -> np.ndarray:
    n = len(x0)
    simplex = np.zeros((n + 1, n))
    simplex[0] = x0
    for i, p in enumerate(param_space):
        row = x0.copy()
        row[i] = np.clip(x0[i] + 0.15 * scales[i], p.low, p.high)
        simplex[i + 1] = row
    return simplex


def _vec_to_params(x: np.ndarray, param_space) -> dict:
    params = {}
    for val, p in zip(x, param_space):
        val = float(np.clip(val, p.low, p.high))
        params[p.name] = int(round(val)) if isinstance(p, IntParameter) else val
    return params

