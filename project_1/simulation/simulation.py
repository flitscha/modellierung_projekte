import numpy as np
from scipy.integrate import odeint
from collections import deque

from core.constants import G, PLANET_MASS, SPACESHIP_MASS
from utils.config import SIMULATION_SPEED, TRAIL_MAX_LENGTH
from core.body import Body
from core.orbit import Orbit


class Simulation:
    def __init__(self):
        # orbits
        self.start_orbit = Orbit.circular(altitude=500e3)  # 500 km
        self.target_orbit = Orbit.circular(altitude=5e6)  # 5,000 km

        # calculate the start-velocity, such that the orbit is a circle
        r = self.start_orbit.semi_major_axis
        v_orbit = (G * PLANET_MASS / r) ** 0.5

        # bodies
        self.planet = Body(PLANET_MASS, [0.0, 0.0], [0.0, 0.0])
        self.ship = Body(SPACESHIP_MASS, [r, 0.0], [0.0, v_orbit])
        self.bodies = [self.planet, self.ship]

        # trial
        # Stores (x, y) world-positions of the ship for the last N steps.
        self.trail: deque[tuple[float, float]] = deque(maxlen=TRAIL_MAX_LENGTH)
        self._record_trail()  # record the initial position right away

    def _record_trail(self):
        self.trail.append((self.ship.pos[0], self.ship.pos[1]))

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
        new_state = odeint(self.rhs, current_state, [0, time_passed])[-1]
        self._set_state_vector(new_state)

        self._record_trail()
