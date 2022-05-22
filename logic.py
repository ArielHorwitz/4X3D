import numpy as np
from prompt_toolkit import print_formatted_text as print

rng = np.random.default_rng()


class Universe:
    def __init__(self, entity_count=50):
        self.tick = 0
        self.entity_count = entity_count
        self.positions = np.zeros((entity_count, 2), dtype=np.float64)
        self.velocities = np.zeros((entity_count, 2), dtype=np.float64)
        self.randomize_vel()

    def simulate(self, ticks=1):
        self.tick += int(ticks)
        self.positions += self.velocities * ticks

    def randomize_vel(self):
        self.velocities += (rng.random((self.entity_count, 2)) * 2 - 1)

    def center_vel(self):
        v = np.linalg.norm(self.positions, axis=-1)
        mask = v != 0
        d = -self.positions[mask] / v[mask, None]
        self.velocities[mask] = d

    def flip_vel(self):
        self.velocities = -self.velocities

    def reset(self):
        self.positions = np.zeros((self.entity_count, 2), dtype=np.float64)
        self.velocities = np.zeros((self.entity_count, 2), dtype=np.float64)
