from loguru import logger
import arrow
import numpy as np

from gui import format_vector, format_latlong, OBJECT_COLORS
from usr.config import DEFAULT_SIMRATE
from logic import CELESTIAL_NAMES, RNG
from logic.dso.ship import Ship
from logic.dso.dso import DeepSpaceObject


class Universe:
    def __init__(self, controller):
        self.feedback_str = 'Welcome to space.'
        self.controller = controller
        self.tick = 0
        self.auto_simrate = DEFAULT_SIMRATE
        self.ds_objects = []
        self.positions = np.zeros((0, 3), dtype=np.float64)
        self.velocities = np.zeros((0, 3), dtype=np.float64)
        self.make_devship()
        self.make_objects(rocks=5, ships=3)
        self.randomize_positions()
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

    # Simulation
    def do_ticks(self, ticks=1):
        self.tick += int(ticks)
        assert self.positions.dtype == self.velocities.dtype == np.float64
        self.positions += self.velocities * ticks

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
        self.positions = RNG.random((self.object_count, 3)) * 1000 - 500

    def randomize_velocities(self):
        self.velocities += RNG.random((self.object_count, 3)) * 2 - 1

    def flip_velocities(self):
        self.velocities = -self.velocities

    # Deep space objects
    def add_object(self, ds_object):
        new_oid = len(self.ds_objects)
        new_position = np.asarray([[0,0,0]])
        new_velocity = np.asarray([[0,0,0]])
        self.positions = np.concatenate((self.positions, new_position))
        self.velocities = np.concatenate((self.velocities, new_velocity))
        self.ds_objects.append(ds_object)
        assert self.object_count == len(self.ds_objects) == len(self.positions) == len(self.velocities)
        return new_oid

    def make_devship(self):
        self.dev_ship = Ship()
        self.dev_ship_oid = self.add_object(self.dev_ship)
        self.dev_ship.setup(
            universe=self, oid=self.dev_ship_oid,
            name='dev', controller=self.controller,
        )

    def make_objects(self, rocks, ships):
        for i in range(rocks):
            new_rock = DeepSpaceObject()
            new_oid = self.add_object(new_rock)
            new_rock.setup(universe=self, oid=new_oid, name=CELESTIAL_NAMES[i])
        for j in range(ships):
            new_ship = Ship()
            new_oid = self.add_object(new_ship)
            new_ship.setup(
                universe=self, oid=new_oid,
                name=f'XSS. {CELESTIAL_NAMES[i+j+1]}',
                color=RNG.integers(low=0, high=len(OBJECT_COLORS)-1, size=1)[0],
            )

    @property
    def object_count(self):
        return len(self.ds_objects)

    # GUI content
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
        return self.dev_ship.cockpit.get_charmap(size)

    def get_content_debug(self, size):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        proj = self.dev_ship.cockpit.camera.get_projected_coords(self.positions)
        object_summaries = []
        for oid in range(min(30, self.object_count)):
            ob = self.ds_objects[oid]
            object_summaries.append('\n'.join([
                f'<orange><bold>{oid:>3}</bold></orange> <h3>{ob.name}</h3>',
                f'<red>Pos</red>: <code>{format_latlong(proj[oid])}</code> [{format_vector(self.positions[oid])}]',
                f'<red>Vel</red>: <code>{np.linalg.norm(self.velocities[oid]):.4f}</code> [{format_vector(self.velocities[oid])}]',
            ]))
        return '\n'.join([
            f'<h1>Simulation</h1>',
            f'<red>Simrate</red>: <code>{self.auto_simrate}</code>',
            f'<red>Tick</red>: <code>{self.tick}</code>',
            f'<h2>Celestial Objects</h2>',
            '\n'.join(object_summaries),
        ])
