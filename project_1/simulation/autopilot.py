import numpy as np
from enum import Enum, auto

from simulation.hohmann import compute_hohmann, HohmannTransfer


class AutopilotState(Enum):
    IDLE = auto()  # waiting for user to start
    WAITING = auto()  # coasting to burn 1 position
    COASTING = auto()  # burn 1 done, coasting to burn 2
    DONE = auto()  # transfer complete


class Autopilot:
    """
    Executes an optimal 2-impulse transfer between two circular orbits.

    State machine
    -------------
    IDLE -> WAITING -> COASTING -> DONE
    """

    def __init__(self):
        self.state: AutopilotState = AutopilotState.IDLE
        self.transfer: HohmannTransfer | None = None
        self._elapsed: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.state not in (AutopilotState.IDLE, AutopilotState.DONE)

    @property
    def time_to_burn2(self) -> float | None:
        if self.state != AutopilotState.COASTING or self.transfer is None:
            return None
        return max(0.0, self.transfer.transfer_time - self._elapsed)

    def start(self, sim) -> HohmannTransfer:
        """
        Compute the transfer and enter WAITING state.
        """
        self.transfer = compute_hohmann(sim.start_orbit, sim.target_orbit)
        self._elapsed = 0.0
        self.state = AutopilotState.WAITING
        return self.transfer

    def update(self, sim, dt: float):
        """Advance the autopilot by dt seconds of sim-time."""
        if self.state == AutopilotState.WAITING:
            # we can do the first burn immediately, since the start-orbit is a circle
            self._execute_burn1(sim)

        elif self.state == AutopilotState.COASTING:
            self._elapsed += dt
            if self._elapsed >= self.transfer.transfer_time:
                self._execute_burn2(sim)

    def reset(self):
        self.state    = AutopilotState.IDLE
        self.transfer = None
        self._elapsed = 0.0

    def _current_radius(self, sim) -> float:
        return float(np.linalg.norm(sim.ship.pos - sim.planet.pos))

    def _execute_burn1(self, sim):
        sim.ship.apply_impulse_tangential(self.transfer.delta_v1)
        self._elapsed = 0.0
        self.state = AutopilotState.COASTING

    def _execute_burn2(self, sim):
        sim.ship.apply_impulse_tangential(self.transfer.delta_v2)
        self.state = AutopilotState.DONE

