import pygame
import numpy as np
from dataclasses import dataclass


PARTICLES_PER_BURST = 50
PARTICLE_LIFETIME = 1.0  # seconds (real time, not sim time)
PARTICLE_SPEED_MIN = 1000000.0  # m/s
PARTICLE_SPEED_MAX = 2000000.0  # m/s
SPREAD_ANGLE = np.pi / 6

# Colour gradient: white -> yellow -> orange -> red (by age of particle)
_GRADIENT = [
    (0.0, (255, 255, 220)),
    (0.3, (255, 220, 80)),
    (0.6, (255, 120, 20)),
    (1.0, (180, 20, 0)),
]


def _lerp_color(t: float) -> tuple[int, int, int]:
    """Interpolate along the colour gradient for age fraction t in [0, 1]"""
    for i in range(len(_GRADIENT) - 1):
        t0, c0 = _GRADIENT[i]
        t1, c1 = _GRADIENT[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(int(c0[j] + f * (c1[j] - c0[j])) for j in range(3))
    return _GRADIENT[-1][1]


@dataclass
class Particle:
    pos: np.ndarray  # world-space position
    vel: np.ndarray  # world-space velocity
    age: float = 0.0  # seconds since spawn
    lifetime: float = PARTICLE_LIFETIME


class ParticleSystem:
    """
    Usage
    -----
        # Spawn a burst when an impulse fires:
        particles.spawn_burst(ship.pos, thrust_direction, magnitude)

        # Each frame:
        particles.update(real_dt)
        particles.draw(screen, camera)
    """

    def __init__(self):
        self._particles: list[Particle] = []
        self._rng = np.random.default_rng()

    def spawn_burst(self, world_pos: np.ndarray, thrust_direction: np.ndarray, delta_v_magnitude: float):
        """
        Spawn a burst of particles at world_pos.

        thrust_direction : unit vector pointing IN the thrust direction
        Particles fly in the OPPOSITE direction.
        """
        exhaust_dir = -thrust_direction

        # Scale particle count slightly with impulse size
        n = int(np.clip(PARTICLES_PER_BURST * (delta_v_magnitude / 100.0), 15, PARTICLES_PER_BURST * 2))

        for _ in range(n):
            angle_offset = self._rng.uniform(-SPREAD_ANGLE, SPREAD_ANGLE)
            direction = self._rotate(exhaust_dir, angle_offset)
            speed = self._rng.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)

            self._particles.append(Particle(
                pos=world_pos.copy(),
                vel=direction * speed,
                lifetime=self._rng.uniform(PARTICLE_LIFETIME * 0.5, PARTICLE_LIFETIME)
            ))

    def update(self, real_dt: float):
        """Advance particles by real_dt seconds. Dead particles are removed."""
        alive = []
        for p in self._particles:
            p.age += real_dt
            p.pos = p.pos + p.vel * real_dt
            if p.age < p.lifetime:
                alive.append(p)
        self._particles = alive

    def draw(self, screen: pygame.Surface, camera):
        for p in self._particles:
            t = p.age / p.lifetime  # 0 = fresh, 1 = dead
            alpha = int(255 * (1.0 - t) ** 1.5)  # fade out
            color = _lerp_color(t)
            radius = max(1, int(3.5 * (1.0 - t * 0.6)))
            screen_pos = camera.world_to_screen(p.pos)

            # Draw with alpha via a tiny surface
            surf = pygame.Surface((radius * 2 + 1, radius * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius)
            screen.blit(surf, (screen_pos[0] - radius, screen_pos[1] - radius))

    def clear(self):
        self._particles.clear()

    @staticmethod
    def _rotate(v: np.ndarray, angle: float) -> np.ndarray:
        c, s = np.cos(angle), np.sin(angle)
        return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])

