from loguru import logger
import arrow
import numpy as np
import random
from inspect import signature

from gui import format_vector, format_latlong, escape_html
from usr.config import CONFIG_DATA
from logic import CELESTIAL_NAMES, RNG
from logic._3d import latlong_single
from logic.universe.events import EventQueue
from logic.universe.engine import Engine
from logic.dso.dso import DeepSpaceObject
from logic.dso.celestial import CelestialObject, SMBH, Star, Rock
from logic.dso.ship import Ship
from logic.command.admiral import Player, Agent


UNIVERSE_INTERVAL = 1_000_000
UNIVERSE_SIZE = 10**6


class Universe:
    def __init__(self, controller):
        self.feedback_str = 'Welcome to space.'
        self.browse_content_callback = lambda *a: ''
        self.engine = Engine({'position': 3})
        self.events = EventQueue()
        self.controller = controller
        self.tick = 0
        self.__last_tick_time = arrow.now()
        self.auto_simrate = CONFIG_DATA['DEFAULT_SIMRATE']
        self.admirals = []
        self.ds_objects = []
        self.ds_celestials = self.ds_ships = np.ndarray((0), dtype=np.bool)
        self.genesis()
        self.register_commands(controller)
        self.interval_event()
        self.inspect(None)

    def register_commands(self, controller):
        d = {
            'sim': self.toggle_autosim,
            'sim.toggle': self.toggle_autosim,
            'sim.tick': self.do_ticks,
            'sim.rate': self.set_simrate,
            'sim.next_event': self.do_next_event,
            'sim.until_event': self.do_until_event,
            'uni.debug': self.debug,
            'inspect': self.inspect,
            'help': self.help,
            'hotkeys': self.help_hotkeys,
        }
        for command, callback in d.items():
            controller.register_command(command, callback)

    def debug(self, *args, **kwargs):
        logger.debug(f'Universe debug() called: {args} {kwargs}')

    # Genesis
    def genesis(self):
        self.add_player(name='Dev')
        self.generate_smbh()
        for i in range(CONFIG_DATA['COMPUTER_PLAYERS']):
            self.add_agent(name=f'Admiral #{i+1}')
        self.randomize_ship_positions()

    def generate_smbh(self):
        smbh = self.add_object(SMBH, name='SMBH')
        # Generate child stars
        star_count = round(random.gauss(*CONFIG_DATA['SPAWN_RATE']['star']))
        for j in range(star_count):
            self.generate_star(smbh)

    def generate_star(self, parent):
        star = self.add_object(Star, name=random.choice(CELESTIAL_NAMES))
        star.position_from_parent(parent, CONFIG_DATA['SPAWN_OFFSET']['star'])
        # Generate child rocks
        rock_count = round(random.gauss(*CONFIG_DATA['SPAWN_RATE']['rock']))
        for k in range(rock_count):
            self.generate_rock(star)

    def generate_rock(self, parent):
        rock = self.add_object(Rock, name=random.choice(CELESTIAL_NAMES))
        rock.position_from_parent(parent, CONFIG_DATA['SPAWN_OFFSET']['rock'])

    def randomize_ship_positions(self):
        for ship_oid in np.flatnonzero(self.ds_ships):
            parent_oid = random.choice(np.flatnonzero(self.ds_celestials))
            ship = self.ds_objects[ship_oid]
            parent = self.ds_objects[parent_oid]
            ship.position_from_parent(parent, 10**2)

    # Simulation
    def update(self):
        if self.auto_simrate > 0:
            ticks = self.get_autosim_ticks()
            if ticks > 0:
                self.do_ticks(ticks)

    def interval_event(self):
        self.add_event(0, self.tick+UNIVERSE_INTERVAL, self.interval_event,
            'Universe interval')

    def do_until_event(self):
        self.do_ticks(self.events.next.tick - self.tick - 0.00001)

    def do_next_event(self):
        self.do_ticks(self.events.next.tick - self.tick + 0.00001)

    def do_ticks(self, ticks=1):
        assert ticks > 0
        last_tick = self.tick + ticks
        next_event = self.events.pop_next(tick=last_tick)
        while next_event:
            intermediate_ticks = next_event.tick - self.tick
            self.__do_ticks(intermediate_ticks)
            logger.debug(f'Handling event {next_event.uid} @{self.tick}: {next_event.description} ({next_event.callback})')
            next_event.callback(next_event.uid)
            next_event = self.events.pop_next(tick=last_tick)
        intermediate_ticks = last_tick - self.tick
        self.__do_ticks(intermediate_ticks)

    def __do_ticks(self, ticks):
        self.tick += ticks
        self.engine.tick(ticks)
        self.__last_tick_time = arrow.now()

    def toggle_autosim(self, set_to=None):
        if set_to is None:
            set_to = CONFIG_DATA['DEFAULT_SIMRATE'] if self.auto_simrate == 0 else -self.auto_simrate
        self.set_simrate(set_to)
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
        if self.auto_simrate > 0:
            self.__last_tick_time = arrow.now()

    def get_autosim_ticks(self):
        if self.auto_simrate <= 0:
            return 0
        td = arrow.now() - self.__last_tick_time
        return td.total_seconds() * self.auto_simrate

    def add_event(self, uid, tick, callback, description=None):
        if tick < self.tick:
            m = f'Cannot add to universe events at past tick {tick} (currently: {self.tick})'
            logger.error(m)
            raise ValueError(m)
        self.events.add(uid, tick, callback, description)

    @property
    def positions(self):
        return self.engine.get_stat('position')

    @property
    def velocities(self):
        return self.engine.get_derivative('position')

    # Deep space objects
    def add_object(self, dso_cls, **kwargs):
        new_oid = self.object_count
        self.engine.add_objects(1)
        ds_object = dso_cls(universe=self, oid=new_oid)
        assert isinstance(ds_object, DeepSpaceObject)
        self.ds_objects.append(ds_object)
        is_ship = isinstance(ds_object, Ship)
        is_celestial = isinstance(ds_object, CelestialObject)
        self.ds_ships = np.concatenate((self.ds_ships, [is_ship]))
        self.ds_celestials = np.concatenate((self.ds_celestials, [is_celestial]))
        assert self.object_count == len(self.ds_objects) == len(self.ds_ships) == len(self.ds_celestials)
        ds_object.setup(**kwargs)
        return ds_object

    @property
    def object_count(self):
        return self.engine.object_count

    # Admirals
    def add_player(self, name):
        assert len(self.admirals) == 0
        admiral = Player(universe=self, fid=0, name=name)
        self.admirals.append(admiral)
        admiral.setup()

    def add_agent(self, name):
        admiral = Agent(universe=self, fid=len(self.admirals), name=name)
        self.admirals.append(admiral)
        admiral.setup()

    @property
    def player(self):
        return self.admirals[0]

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
        return self.player.get_charmap(size)

    def get_content_debug(self, size):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        ltt = arrow.now() - self.__last_tick_time
        object_summaries = []
        for oid in np.flatnonzero(self.ds_celestials)[:5]:
            ob = self.ds_objects[oid]
            line = f'<{ob.color}>{ob.label} ({ob.type_name})</{ob.color}>'
            object_summaries.append(line)
        object_summaries.append('...')
        for oid in np.flatnonzero(self.ds_ships)[:30]:
            ship = self.ds_objects[oid]
            name = f'<{ship.color}>{ship.label} ({ship.type_name})</{ship.color}>'
            orders = f'<italic>{ship.current_orders}</italic>'
            object_summaries.append(f'{name:<50} {orders}')
            # object_summaries.append(self.inspection_content(oid, size, verbose=False))
        event_str = ''
        if len(self.events) > 0:
            ev = self.events.next
            event_str = f'Next: @{ev.tick:.2f} {escape_html(ev.callback.__name__)}'
        return '\n'.join([
            f'<h1>Simulation</h1>',
            f'<red>Simrate</red>: <code>{self.auto_simrate}</code>',
            f'<red>Tick</red>: <code>{self.tick:.4f}</code>',
            f'<red>Tick time</red>: <code>{ltt}</code>',
            f'<red>Events</red>: <code>{len(self.events)}</code>\n{event_str}',
            f'<h2>Celestial Objects</h2>',
            '\n'.join(object_summaries),
        ])

    def get_content_events(self, size):
        event_count = len(self.events)
        event_summaries = []
        for i in range(min(20, event_count)):
            event = self.events.queue[i]
            event_summaries.append('\n'.join([
                f'<orange><bold>{i:>2}</bold></orange> <h3>@{event.tick:.4f} ({self.tick-event.tick:.4f})</h3> {escape_html(event.callback)}',
                f'<red>{event.uid}</red>: <code>{event.description}</code>',
            ]))
        return '\n'.join([
            f'<h1>Events</h1>',
            f'<red>Total</red>: <code>{len(self.events)}</code>',
            '\n'.join(event_summaries),
        ])

    def get_content_browser(self, size):
        return self.browse_content_callback(size)

    def inspection_content(self, oid, size, verbose=True):
        ob = self.ds_objects[oid]
        ob_type = ob.type_name
        color = ob.color
        ob_rel_vector = ob.position - self.player.position
        dir = latlong_single(ob_rel_vector)
        player_dist = np.linalg.norm(ob_rel_vector)
        p = f'\n{format_vector(ob.position)}' if verbose else ''
        v = f'\n{format_vector(ob.velocity)}' if verbose else ''
        a = f'\n{format_vector(ob.acceleration)}' if verbose else ''
        vmag = np.linalg.norm(ob.velocity)
        vdir = format_latlong(latlong_single(ob.velocity))
        amag = np.linalg.norm(ob.acceleration)
        adir = format_latlong(latlong_single(ob.acceleration))

        extra_lines = []
        if isinstance(ob, Ship):
            extra_lines.extend([
                '<h2>Cockpit</h2>',
                f'<red>Current orders</red>:',
                f'<italic>{ob.current_orders}</italic>',
            ])
            if verbose:
                look = latlong_single(ob.cockpit.camera.current_axes[0])
                extra_lines.append(f'<red>Looking</red>: <code>{format_latlong(look)}</code>')
        title_name = f'<white>#{ob.oid:>3} {escape_html(ob.name)}</white>'
        title_type = f' <{color}>({escape_html(ob_type)})</{color}>'
        return '\n'.join([
            f'<bold><underline>{title_name}{title_type}</underline></bold>',
            f'<red>Pos</red>: <code>{player_dist:.1f} [{format_latlong(dir)}]</code>{p}',
            f'<red>Vel</red>: <code>{vmag:.4f} [{vdir}]</code>{v}',
            f'<red>Acc</red>: <code>{amag:.4f} [{adir}]</code>{a}',
            *extra_lines,
        ])

    def inspect(self, oid=None):
        if oid is None:
            self.browse_content_callback = lambda *a: self.get_content_debug(*a)
            return
        self.browse_content_callback = lambda size, oid=int(oid): self.inspection_content(oid, size)

    def help(self):
        self.browse_content_callback = self.help_content

    def help_content(self, size):
        return '\n'.join([
            f'{k:.<20}: {v.__name__} {signature(v)}'
        for k, v in self.controller.commands.items()])

    def help_hotkeys(self):
        r = '\n'.join([f'{k:>11}: {v}' for k, v in CONFIG_DATA['HOTKEY_COMMANDS'].items()])
        self.browse_content_callback = lambda *a: r
