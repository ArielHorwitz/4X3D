from loguru import logger
import arrow
import numpy as np
from prompt_toolkit import print_formatted_text as print

from logic import CELESTIAL_NAMES, RNG
from gui import format_vector


class Universe:
    def __init__(self, entity_count=20):
        self.tick = 0
        self.entity_count = entity_count
        self.positions = np.zeros((entity_count, 3), dtype=np.float64)
        self.velocities = np.zeros((entity_count, 3), dtype=np.float64)
        self.randomize_pos()
        self.randomize_vel()

    def match_velocities(self, a, b):
        self.velocities[a] = self.velocities[b]

    def match_positions(self, a, b):
        self.positions[a] = self.positions[b]

    def simulate(self, ticks=1):
        self.tick += int(ticks)
        assert self.positions.dtype == self.velocities.dtype == np.float64
        self.positions += self.velocities * ticks / 1000

    def randomize_pos(self):
        self.positions += (RNG.random((self.entity_count, 3)) * 20 - 10)
        self.positions[0] = 0

    def randomize_vel(self):
        self.velocities += (RNG.random((self.entity_count, 3)) * 2 - 1)
        self.velocities[0] = 0

    def center_vel(self):
        v = np.linalg.norm(self.positions, axis=-1)
        mask = v != 0
        d = -self.positions[mask] / v[mask, None]
        self.velocities[mask] = d

    def flip_vel(self):
        self.velocities = -self.velocities

    def reset(self):
        self.positions = np.zeros((self.entity_count, 3), dtype=np.float64)
        self.velocities = np.zeros((self.entity_count, 3), dtype=np.float64)

    # GUI
    def get_window_content(self, name, size):
        if hasattr(self, f'get_content_{name}'):
            f = getattr(self, f'get_content_{name}')
            return f(size)
        else:
            t = arrow.get().format('YY-MM-DD, hh:mm:ss')
            return '\n'.join([
                f'<h1>{name}</h1>',
                f'<red>Time</red>: <code>{t}</code>',
                f'<red>Size</red>: <code>{size}</code>',
            ])

    def get_content_debug(self, size):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        # proj = self.app.display_window.get_projected_coords(self.app.universe.positions)
        object_summaries = []
        for i in range(min(30, self.entity_count)):
            object_summaries.append('\n'.join([
                f'<h3>{i:>2}.{CELESTIAL_NAMES[i]}</h3>',
                # f'<red>Pos</red>: <code>{format_latlong(proj[i])}</code> [{format_vector(self.positions[i])}]',
                f'<red>Pos</red>: [{format_vector(self.positions[i])}]',
                f'<red>Vel</red>: <code>{np.linalg.norm(self.velocities[i]):.4f}</code> [{format_vector(self.velocities[i])}]',
            ]))
        return '\n'.join([
            f'<h1>Simulation</h1>',
            # f'<red>Auto sim</red>: <code>{self.app.auto_sim}</code>',
            f'<red>Tick</red>: <code>{self.tick}</code>',
            f'<h2>Celestial Names</h2>',
            '\n'.join(object_summaries),
        ])
