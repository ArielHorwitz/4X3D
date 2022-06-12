from loguru import logger
import arrow
import math
import numpy as np
import random
import itertools
from functools import partial
from collections import deque
from inspect import signature

from util import format_vector, format_latlong, escape_html, CELESTIAL_NAMES
from util.config import CONFIG_DATA
from util._3d import latlong_single
from logic.universe.events import EventQueue
from logic.universe.engine import Engine
from logic.dso.dso import DeepSpaceObject
from logic.dso.celestial import CelestialObject, SMBH, Star, Rock
from logic.dso.ship import Ship
from logic.command.admiral import Player, Agent


UNIVERSE_SIZE = 10**6
TINY_TICK = 0.00001
CONSOLE_SCROLLBACK = 1000
FEEDBACK_SCROLLBACK = 20
PROMPT_LINE_SPLIT = ' && '
PROMPT_LINE_SPLIT_ESCAPE = escape_html(PROMPT_LINE_SPLIT)


class Universe:
    def __init__(self, controller):
        self.controller = controller
        self.controller.set_feedback(lambda s: self.output_feedback(escape_html(s)))
        self.console_stack = deque()
        self.feedback_stack = deque()
        self.get_content_browser = lambda *a: 'Use "help" command for help.'
        self.engine = Engine({'position': 3})
        self.events = EventQueue()
        self.tick = 0
        self.__last_tick_time = arrow.now()
        self.auto_simrate = CONFIG_DATA['DEFAULT_SIMRATE']
        self.admirals = []
        self.ds_objects = []
        self.ds_celestials = self.ds_ships = np.ndarray((0), dtype=np.bool)
        self.genesis()
        self.register_commands(controller)
        self.output_feedback('<orange><bold>Welcome to space.</bold></orange>')
        self.output_console('Need help? Press enter and use the "help" command.')

    def register_commands(self, controller):
        commands = [
            ('sim', self.toggle_autosim),
            ('sim.toggle', self.toggle_autosim),
            ('sim.tick', self.do_ticks),
            ('sim.rate', self.set_simrate),
            ('sim.next_event', self.do_next_event),
            ('sim.until_event', self.do_until_event),
            ('uni.debug', self.debug),
            ('inspect', self.inspect),
            ('print', self.print),
            ('help', self.help),
        ]
        for command in commands:
            controller.register_command(*command)

    def handle_input(self, input_text, allow_aliases=True):
        if PROMPT_LINE_SPLIT in input_text:
            lines = input_text.split(PROMPT_LINE_SPLIT)
        elif PROMPT_LINE_SPLIT_ESCAPE in input_text:
            lines = input_text.split(PROMPT_LINE_SPLIT_ESCAPE)
        else:
            lines = [input_text]
        for line in lines:
            if line in CONFIG_DATA['CUSTOM_COMMANDS']:
                line_text = CONFIG_DATA['CUSTOM_COMMANDS'][line]
                self.output_console(f'<blue>$</blue> {escape_html(line)} -> {escape_html(line_text)}')
                self.handle_input(line_text, allow_aliases=False)
                continue
            command, *args = line.split(' ')
            logger.debug(f'Resolved prompt input: {line} -> {command} {args}')
            is_silent = any(command.startswith(silent) for silent in CONFIG_DATA['SILENT_COMMANDS'])
            if not is_silent:
                self.output_console(f'<cyan>$</cyan> {line}')
            r = self.controller.do_command(command, args)
            if not is_silent and isinstance(r, str):
                self.output_console(f'>> {str(r)[:100]}')


    def output_console(self, message):
        self.console_stack.appendleft(str(message))
        while len(self.console_stack) > CONSOLE_SCROLLBACK:
            self.console_stack.pop()

    def output_feedback(self, message, also_console=True):
        self.feedback_stack.appendleft(str(message))
        while len(self.feedback_stack) > FEEDBACK_SCROLLBACK:
            self.feedback_stack.pop()
        if also_console:
            self.output_console(message)

    def debug(self, *args, **kwargs):
        """Developer debug logic"""
        logger.debug(f'Universe debug() called: {args} {kwargs}')

    # Parsers
    def parse_oid(self, oid):
        if oid is None:
            return self.player.my_ship.oid
        oid = int(oid)
        if oid < 0 or oid >= self.object_count:
            return f'expected valid object ID, instead got: {oid} (last oid: {self.object_count-1})'
        return oid

    def parse_ship_oid(self, oid):
        if oid is None:
            return self.player.my_ship.oid
        oid = int(oid)
        if oid < 0 or oid >= self.object_count:
            return f'expected valid ship ID, instead got: {oid} (last oid: {self.object_count-1})'
        if not self.ds_ships[oid]:
            return f'expected valid ship ID, instead got non-ship ID: {oid} (last oid: {self.object_count-1})'
        return oid

    def parse_player_ship(self, oid):
        if oid is None:
            return self.player.my_ship.oid
        oid = int(oid)
        if oid not in self.player.fleet_oids and oid != self.player.my_ship.oid:
            self.output_feedback(f'<underline>oid#{oid} not in my fleet</underline>:')
            self.player.print_fleet()
            return f'expected player ship ID, instead got: {oid}'
        return oid

    # Genesis
    def genesis(self):
        self.generate_smbh()
        self.add_player(name='Dev')
        for i in range(CONFIG_DATA['COMPUTER_PLAYERS']):
            self.add_agent(name=f'Admiral #{i+1}')

    def generate_smbh(self):
        smbh = self.add_object(SMBH, name='SMBH')
        # Generate child stars
        star_count = round(random.gauss(*CONFIG_DATA['SPAWN_RATE']['star']))
        for j in range(star_count):
            self.generate_star(smbh)

    def generate_star(self, parent):
        star = self.add_object(Star, name=random.choice(CELESTIAL_NAMES))
        star.offset_from_parent(parent, CONFIG_DATA['SPAWN_OFFSET']['star'])
        # Generate child rocks
        rock_count = round(random.gauss(*CONFIG_DATA['SPAWN_RATE']['rock']))
        for k in range(rock_count):
            self.generate_rock(star)

    def generate_rock(self, parent):
        rock = self.add_object(Rock, name=random.choice(CELESTIAL_NAMES))
        rock.offset_from_parent(parent, CONFIG_DATA['SPAWN_OFFSET']['rock'])

    # Simulation
    def update(self):
        if self.auto_simrate > 0:
            ticks = self.get_autosim_ticks()
            if ticks > 0:
                self.do_ticks(ticks)

    def do_until_event(self):
        """Run simulation until but not including next event"""
        self.do_ticks(self.events.next.tick - self.tick - TINY_TICK)

    def do_next_event(self):
        """Run simulation to complete next event"""
        self.do_ticks(self.events.next.tick - self.tick + TINY_TICK)

    def do_ticks(self, ticks=1):
        """Simulate ticks
        TICKS Number of ticks to simulate
        """
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
        """Toggle universe simulation"""
        if set_to is None:
            set_to = CONFIG_DATA['DEFAULT_SIMRATE'] if self.auto_simrate == 0 else -self.auto_simrate
        self.set_simrate(set_to)

    def set_simrate(self, value, delta=False):
        """Set simulation speed
        VALUE Simulation rate
        --d DELTA Use value as delta
        """
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
        s = 'in progress' if self.auto_simrate > 0 else 'paused'
        tag = 'green' if self.auto_simrate > 0 else 'orange'
        self.output_feedback(f'<{tag}>Simulation {s}</{tag}> ({self.auto_simrate:.1f})')

    def get_autosim_ticks(self):
        if self.auto_simrate <= 0:
            return 0
        td = arrow.now() - self.__last_tick_time
        return td.total_seconds() * self.auto_simrate

    def add_event(self, uid, tick, callback, description=None):
        if tick is None:
            tick = self.tick + TINY_TICK
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
        player = Player(universe=self, fid=0, name=name)
        self.admirals.append(player)
        player.setup(self.controller)

    def add_agent(self, name):
        admiral = Agent(universe=self, fid=len(self.admirals), name=name)
        self.admirals.append(admiral)
        admiral.setup()

    @property
    def player(self):
        return self.admirals[0]

    def get_player_oid(self):
        return self.player.my_ship.oid

    # GUI content
    def get_window_content(self, name, size):
        if hasattr(self, f'get_content_{name}'):
            f = getattr(self, f'get_content_{name}')
            return f(size)
        else:
            return '\n'.join([
                f'<h1>{name}</h1>',
                f'<code>{size}</code>',
            ])

    def get_content_display(self, size):
        return self.player.get_charmap(size)

    def get_content_console(self, size):
        return self.stack_content(self.console_stack, size)

    def get_content_feedback(self, size):
        return self.stack_content(self.feedback_stack, size)

    def stack_content(self, stack, size):
        line_count = size[1]
        sliced = itertools.islice(stack, 0, line_count)
        full = '\n'.join(reversed(list(sliced)))
        lines = full.split('\n')[-line_count:]
        return '\n'.join(lines)

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

    def get_content_cockpit(self, size):
        return '\n'.join([
            self.inspection_content(oid=self.player.my_ship.oid, size=size),
        ])

    def inspection_content(self, oid, size):
        ob = self.ds_objects[oid]
        ob_type = ob.type_name
        color = ob.color
        ob_rel_vector = ob.position - self.player.position
        dir = latlong_single(ob_rel_vector)
        player_dist = np.linalg.norm(ob_rel_vector)
        p = f'\n{format_vector(ob.position)}'
        v = f'\n{format_vector(ob.velocity)}'
        a = f'\n{format_vector(ob.acceleration)}'
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

    def print(self, content_name, set_browser=False):
        """Print content to console
        CONTENT_NAME Content to print
        --b SET_BROWSER Also open in browser
        """
        callback = partial(self.get_window_content, content_name)
        self.output_console(callback((10000, 10000)))
        if set_browser:
            self.set_browser_content(callback)

    def set_browser_content(self, callback, print=False):
        self.get_content_browser = callback
        logger.debug(f'setting browser content: {callback}')
        if print:
            logger.debug(f'setting browser content print')
            self.output_console(callback((10000, 10000)))

    def inspect(self, oid):
        """Inspect a deep space object
        OID Object ID
        """
        self.set_browser_content(lambda size, oid=oid: self.inspection_content(oid, size), print=True)

    def help(self, *args):
        """Show help"""
        self.set_browser_content(self.get_content_help, print=True)

    def help_hotkeys(self, *args):
        """Show hotkeys"""
        self.set_browser_content(self.get_content_help_hotkey, print=True)

    @property
    def feedback_str(self):
        return self.feedback_stack[0]

    def get_content_help(self, *a):
        formatted_commands = '\n'.join([''.join([
            f'<orange>{name:<25}</orange>: ',
            f'<green>{escape_html(argspec.desc)}</green> ',
            f'<bold>{escape_html(argspec.spec)}</bold> ',
            f'{callback.__name__}{signature(callback)}',
        ]) for name, callback, argspec in self.controller.sorted_items()])
        return f'Registered commands:\n{formatted_commands}'

    def get_content_hotkeys(self, *a):
        return 'Registered hotkeys:\n'+'\n'.join([f'{k:>11}: {v}' for k, v in CONFIG_DATA['HOTKEY_COMMANDS'].items()])
