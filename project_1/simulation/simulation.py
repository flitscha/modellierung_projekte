import numpy as np
from scipy.integrate import odeint

from core.constants import G, PLANET_RADIUS, PLANET_MASS, SPACESHIP_MASS
from utils.config import SIMULATION_SPEED
from core.body import Body


class Simulation:
    def __init__(self):
        r = PLANET_RADIUS + 500e3  # 500 km

        # calculate the start-velocity, such that the orbit is a circle
        v_orbit = (G * PLANET_MASS / r) ** 0.5

        self.planet = Body(PLANET_MASS, [0.0, 0.0], [0.0, 0.0])
        self.ship = Body(SPACESHIP_MASS, [r, 0.0], [0.0, v_orbit])

        self.bodies = [self.planet, self.ship]

    def _get_state_vector(self):
        # builds a big state-vector, that is used in the differencial equation
        return np.concatenate([
            self.planet.pos, self.ship.pos, 
            self.planet.vel, self.ship.vel
        ])

    def _set_state_vector(self, vector):
        # sets the attributes according to a state-vector
        self.planet.pos = vector[0:2]
        self.ship.pos = vector[2:4]
        self.planet.vel = vector[4:6]
        self.ship.vel = vector[6:8]

    def rhs(self, state, t):
        p1_pos, p2_pos = state[0:2], state[2:4]
        p1_vel, p2_vel = state[4:6], state[6:8]

        r_vec = p1_pos - p2_pos
        dist = np.linalg.norm(r_vec)

        force = -G * self.planet.mass * self.ship.mass * r_vec / dist**3

        a1 = force / self.planet.mass
        a2 = -force / self.ship.mass

        return np.concatenate([p1_vel, p2_vel, a1, a2])

    def update(self, dt):
        time_passed = dt * SIMULATION_SPEED

        current_state = self._get_state_vector()
        t_span = [0, time_passed]

        new_state = odeint(self.rhs, current_state, t_span)[-1]

        self._set_state_vector(new_state)
