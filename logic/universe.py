from loguru import logger
import arrow
import numpy as np

from gui import format_vector, format_latlong
from logic import CELESTIAL_NAMES, RNG
from logic.ship.window import ShipWindow


DEFAULT_SIMRATE = 5


class Universe:
    def __init__(self, controller, entity_count=20):
        self.feedback_str = 'Welcome to space.'
        self.tick = 0
        self.auto_simrate = 100
        self.ship_window = ShipWindow(universe=self, controller=controller)
        self.entity_count = entity_count
        self.positions = np.zeros((entity_count, 3), dtype=np.float64)
        self.velocities = np.zeros((entity_count, 3), dtype=np.float64)
        self.randomize_positions()
        self.randomize_velocities()
        self.register_commands(controller)

    def update(self):
        if self.auto_simrate > 0:
            self.do_ticks(self.auto_simrate)

    def register_commands(self, controller):
        d = {
            'sim': self.toggle_autosim,
            'sim.toggle': self.toggle_autosim,
            'sim.tick': self.do_ticks,
            'sim.rate': self.set_simrate,
            'sim.matchv': self.match_velocities,
            'sim.matchp': self.match_positions,
            'sim.randp': self.randomize_positions,
            'sim.randv': self.randomize_velocities,
            'sim.flipv': self.flip_velocities,
        }
        for command, callback in d.items():
            controller.register_command(command, callback)

    def command_ship(self, *args):
        return self.ship_window.handle_command(args[0], args[1:])

    def do_ticks(self, ticks=1):
        self.tick += int(ticks)
        assert self.positions.dtype == self.velocities.dtype == np.float64
        self.positions += self.velocities * ticks / 1000

    def toggle_autosim(self, set_to=None):
        new = DEFAULT_SIMRATE if self.auto_simrate == 0 else -self.auto_simrate
        self.auto_simrate = new if set_to is None else set_to
        s = 'in progress' if self.auto_simrate > 0 else 'paused'
        tag = 'blank' if self.auto_simrate > 0 else 'orange'
        self.feedback_str = f'<{tag}>Simulation {s}</{tag}>'

    def set_simrate(self, value, delta=False):
        sign = -1 if self.auto_simrate < 0 else 1
        if delta:
            self.auto_simrate += value * sign
            if sign > 0:
                self.auto_simrate = max(1, self.auto_simrate)
            else:
                self.auto_simrate = min(-1, self.auto_simrate)
        elif value != 0:
            self.auto_simrate = value

    def match_velocities(self, a, b):
        self.velocities[a] = self.velocities[b]

    def match_positions(self, a, b):
        self.positions[a] = self.positions[b]

    def randomize_positions(self):
        self.positions = RNG.random((self.entity_count, 3)) * 20 - 10

    def randomize_velocities(self):
        self.velocities += RNG.random((self.entity_count, 3)) * 2 - 1

    def flip_velocities(self):
        self.velocities = -self.velocities

    # Content for GUI
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

    def get_content_display(self, size):
        return self.ship_window.get_charmap(size)

    def get_content_debug(self, size):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        proj = self.ship_window.camera.get_projected_coords(self.positions)
        object_summaries = []
        for i in range(min(30, self.entity_count)):
            object_summaries.append('\n'.join([
                f'<h3>{i:>2}.{CELESTIAL_NAMES[i]}</h3>',
                f'<red>Pos</red>: <code>{format_latlong(proj[i])}</code> [{format_vector(self.positions[i])}]',
                f'<red>Vel</red>: <code>{np.linalg.norm(self.velocities[i]):.4f}</code> [{format_vector(self.velocities[i])}]',
            ]))
        return '\n'.join([
            f'<h1>Simulation</h1>',
            f'<red>Simrate</red>: <code>{self.auto_simrate}</code>',
            f'<red>Tick</red>: <code>{self.tick}</code>',
            f'<h2>Celestial Objects</h2>',
            '\n'.join(object_summaries),
        ])
