from loguru import logger
from pathlib import Path
import arrow
import math
import numpy as np
import random
import itertools
from functools import partial
from collections import deque
from inspect import signature

from util import (
    file_load,
    is_number,
    is_index,
    format_vector,
    format_latlong,
    escape_html,
    escape_if_malformed,
    CELESTIAL_NAMES,
    )
from util.argparse import arg_validation
from util.config import CONFIG_DATA
from util.argparse import EXAMPLE_SPECSTRING
from util.controller import Controller
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
NO_SIZE_LIMIT = 10_000, 10_000
PROMPT_LINE_SPLIT = ' && '
PROMPT_LINE_SPLIT_ESCAPE = escape_html(PROMPT_LINE_SPLIT)


class Universe:
    def __init__(self, controller):
        self.controller = controller
        self.controller.set_feedback(self.output_feedback)
        self.display_controller = Controller('Logic Display', feedback=self.output_feedback)
        self.console_stack = deque()
        self.feedback_stack = deque()
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
        self.register_display_cache()
        self.output_feedback('<orange><bold>Welcome to space.</bold></orange>')
        self.output_console('Need help? Press enter and use the <code>help</code> command.')

    def gui_prepared(self):
        self.refresh_display_cache()

    def register_commands(self, controller):
        commands = [
            ('sim', self.toggle_autosim),
            ('sim.toggle', self.toggle_autosim),
            ('sim.tick', self.do_ticks),
            ('sim.rate', self.set_simrate),
            ('sim.next_event', self.do_next_event),
            ('sim.until_event', self.do_until_event),
            ('uni.debug', self.debug),
            ('echo', self.echo),
            ('print', self.print),
            ('print.clear', self.clear_console),
            ('browse', self.browse),
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
            if ' ' in line:
                command, arg_string = line.split(' ', 1)
            else:
                command, arg_string = line, ''
            is_silent = any(command.startswith(silent) for silent in CONFIG_DATA['SILENT_COMMANDS'])
            if not is_silent:
                self.output_console(f'<cyan>$</cyan> {escape_html(line)}')
            r = self.controller.do_command(command, arg_string)
            if not is_silent and isinstance(r, str):
                self.output_console(f'>> {str(r)[:100]}')

    def output_console(self, message):
        message = escape_if_malformed(message, indicate_escaped=True)
        self.console_stack.appendleft(message)
        while len(self.console_stack) > CONSOLE_SCROLLBACK:
            self.console_stack.pop()

    def output_feedback(self, message, also_console=True):
        logger.debug(f'output_feedback: {message}')
        message = escape_if_malformed(message)
        self.feedback_stack.appendleft(message)
        while len(self.feedback_stack) > FEEDBACK_SCROLLBACK:
            self.feedback_stack.pop()
        if also_console:
            self.output_console(message)

    def clear_console(self):
        """Clear the console"""
        self.console_stack.clear()

    def echo(self, message):
        """ArgSpec
        Echo text in the console
        ___
        *MESSAGE Text to echo
        """
        self.output_console(' '.join(str(_) for _ in message))

    def debug(self, *args, **kwargs):
        """Developer debug logic"""
        logger.debug(f'Universe debug() called: {args} {kwargs}')

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
        """ArgSpec
        Simulate ticks
        ___
        TICKS Number of ticks to simulate
        """
        with arg_validation(f'Ticks must be a positive number: {ticks}'):
            assert ticks >= 0
        if ticks == 0:
            return

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

    def set_simrate(self, simrate, delta=False):
        """ArgSpec
        Set simulation speed
        ___
        SIMRATE Simulation rate
        -+d DELTA Add this number to simulation rate (as delta)
        """
        with arg_validation(f'Simulation speed must be a number: {simrate}'):
            assert is_number(simrate)

        sign = -1 if self.auto_simrate < 0 else 1
        if delta:
            self.auto_simrate += simrate * sign
            if sign > 0:
                self.auto_simrate = max(1, self.auto_simrate)
            else:
                self.auto_simrate = min(-1, self.auto_simrate)
        elif simrate != 0:
            self.auto_simrate = simrate
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

    def is_oid(self, oid):
        if not is_index(oid):
            return False
        if oid < 0 or oid >= self.object_count:
            return False
        return True

    def search_oids(self, filter_name=None, fleet_id=None):
        objects = set()
        if filter_name is not None:
            assert isinstance(filter_name, str)
            filter_name = filter_name.lower()
        for ob in self.ds_objects:
            if fleet_id is not None:
                if not isinstance(ob, Ship):
                    continue
                if not ob.oid in self.admirals[fleet_id].fleet_oids:
                    continue
            if filter_name is not None:
                if filter_name not in ob.label.lower():
                    continue
            objects.add(ob.oid)
        return objects

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

    @property
    def admiral_count(self):
        return len(self.admirals)

    def is_fid(self, fid):
        logger.debug(f'is_fid: {fid} {type(fid)}')
        if not is_index(fid):
            logger.debug(f'is_fid: not index')
            return False
        if fid < 0 or fid >= self.admiral_count:
            logger.debug(f'is_fid: not in range')
            return False
        return True

    # GUI content
    def register_display_cache(self):
        for window_name in [
            'console',
            'feedback',
            'debug',
            'events',
            'commands',
            'command',
            'pages',
            'page',
            'sim',
            'objects',
            'inspect',
            'cockpit',
        ]:
            func = getattr(self, f'get_content_{window_name}')
            self.display_controller.register_command(window_name, func)
        self.refresh_display_cache()

    def refresh_display_cache(self):
        self.display_controller.cache('__init', 'Use "help" command for help.')
        self.display_controller.cache('__browser_page', '__init')
        self.display_controller.cache('__browser_options', tuple())
        self.display_controller.cache('__browser_koptions', {})
        self.display_controller.cache('__easter_egg', 'Ho ho ho, you found me!')
        self.display_controller.cache('__malformed_html', '<tag')
        self.display_controller.cache('__all_commands', self.get_content_commands())
        self.display_controller.cache('__all_pages', self.get_content_pages())
        self.display_controller.cache('help', self.__get_content_help())
        self.display_controller.cache('help.commandline', EXAMPLE_SPECSTRING)
        self.display_controller.cache('hotkeys', self.__get_content_hotkeys())

    def get_window_content(self, name, size=NO_SIZE_LIMIT):
        if hasattr(self, f'get_content_{name}'):
            f = getattr(self, f'get_content_{name}')
            return f(size)
        else:
            return '\n'.join([
                f'<h1>{name}</h1>',
                f'<code>{size}</code>',
            ])

    def get_content_display(self, size=NO_SIZE_LIMIT):
        return self.player.get_charmap(size)

    def get_content_console(self, size=NO_SIZE_LIMIT):
        return self.stack_content(self.console_stack, size)

    def get_content_feedback(self, size=NO_SIZE_LIMIT):
        return self.stack_content(self.feedback_stack, size)

    def get_content_objects(self,
            filter_name=None, fleet_id=None,
            max_entries=30, size=NO_SIZE_LIMIT):
        """ArgSpec
        Retrieve info on deep space objects
        ___
        +FILTER_NAME Text in object names to filter for
        -+fleet FLEET_ID Fleet ID to filter for
        -+max MAX_ENTRIES Maximum number of objects to show
        """
        if filter_name is not None:
            filter_name = str(filter_name)
        if fleet_id is not None:
            with arg_validation(f'Invalid fleet ID'):
                assert self.is_fid(fleet_id)
        with arg_validation(f'MAX_ENTRIES must be a positive integer'):
            assert isinstance(max_entries, int)
            assert max_entries > 0
        filtered_oids = self.search_oids(filter_name=filter_name, fleet_id=fleet_id)
        object_summaries = [f'<h2>Deep Space Objects</h2>']
        for i, oid in enumerate(filtered_oids):
            if i >= max_entries:
                break
            ob = self.ds_objects[oid]
            line = f'<{ob.color}>{ob.label} ({ob.type_name})</{ob.color}>'
            if isinstance(ob, Ship):
                orders = f'<italic>{ob.current_orders}</italic>'
                line = f'{line:<50} {orders}'
            object_summaries.append(line)
        return '\n'.join(object_summaries)

    def get_content_debug(self, size=NO_SIZE_LIMIT):
        logfile = file_load(Path.cwd() / 'debug.log')
        log_lines = logfile.split('\n')
        return '\n'.join(escape_if_malformed(l) for l in log_lines[-size[1]:])

    def get_content_sim(self, size=NO_SIZE_LIMIT):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        ltt = arrow.now() - self.__last_tick_time
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
        ])

    def get_content_events(self, size=NO_SIZE_LIMIT):
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

    def get_content_cockpit(self, size=NO_SIZE_LIMIT):
        return '\n'.join([
            self.get_content_inspect(oid=self.player.my_ship.oid),
        ])

    def get_content_browser(self, size=NO_SIZE_LIMIT):
        command = self.display_controller.do_command('__browser_page')
        options = self.display_controller.do_command('__browser_options')
        koptions = self.display_controller.do_command('__browser_koptions')
        return self.display_controller.do_command(command,
            custom_args=options, custom_kwargs=koptions)

    def get_content_inspect(self, oid=None, size=NO_SIZE_LIMIT):
        """ArgSpec
        Retrieve info on a deep space object
        ___
        +OID Object ID
        """
        if oid is None:
            oid = self.player.my_ship.oid
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.is_oid(oid)

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
        title_name = f'<white>#{ob.oid:>3} {escape_if_malformed(ob.name)}</white>'
        title_type = f' <{color}>({escape_html(ob_type)})</{color}>'
        return '\n'.join([
            f'<bold><underline>{title_name}{title_type}</underline></bold>',
            f'<red>Pos</red>: <code>{player_dist:.1f} [{format_latlong(dir)}]</code>{p}',
            f'<red>Vel</red>: <code>{vmag:.4f} [{vdir}]</code>{v}',
            f'<red>Acc</red>: <code>{amag:.4f} [{adir}]</code>{a}',
            *extra_lines,
        ])

    def get_content_commands(self, filter=None, first_level=False, debug=False, size=NO_SIZE_LIMIT):
        """ArgSpec
        Show list of commands
        ___
        +FILTER Show only commands with this filter
        -+first-level FIRST_LEVEL Show only first level commands
        -+debug DEBUG Show extra debug information
        """
        def filter_(nca, filter=filter, first=first_level):
            name, callback, argspec = nca
            if filter is not None and filter not in name:
                    return False
            if first and '.' in  name:
                return False
            return True
        items = [_ for _ in self.controller.sorted_items() if filter_(_)]
        return '\n'.join([''.join([
            f'<orange>{name:<25}</orange>: ',
            f'<green>{escape_html(argspec.desc)}</green> ',
            f'<bold>{escape_html(argspec.spec)}</bold> ',
            f'{callback.__name__}{signature(callback)}' if debug else '',
        ]) for name, callback, argspec in items])

    def get_content_command(self, command_name=None, size=NO_SIZE_LIMIT):
        """ArgSpec
        Show info on commands
        ___
        +COMMAND_NAME Command name
        """
        if command_name is None:
            return self.display_controller.do_command('__all_commands')
        with arg_validation(f'Couldn\'t find command: {command_name}'):
            assert self.controller.has_command(command_name)
        callback, argspec = self.controller.get_command(command_name)
        return argspec.help_verbose

    def get_content_pages(self, filter=None):
        """ArgSpec
        Show list of pages
        ___
        +FILTER Show only pages with this filter
        """
        commands = self.display_controller.commands
        cached = self.display_controller.cached
        if filter is not None:
            all_names = [_ for _ in sorted(commands + cached) if filter in _]
        else:
            all_names = sorted(commands + cached)
        strs = []
        for name in all_names:
            if name.startswith('_'):
                continue
            spec = ''
            if self.display_controller.has_command(name):
                callback, argspec = self.display_controller.get_command(name)
                spec = argspec.spec
            strs.append(f'<cyan>{name:>25}</cyan> <bold>{spec}</bold>')
        return '\n'.join(strs)

    def get_content_page(self, page=None, size=NO_SIZE_LIMIT):
        """ArgSpec
        Show info on pages
        ___
        +PAGE Page to show
        """
        if page is None:
            return self.display_controller.do_command('__all_pages')
        with arg_validation(f'Couldn\'t find page: {page}'):
            assert self.display_controller.has(page)
        if not self.display_controller.has_command(page):
            return f'Page {page} takes no arguments'
        callback, argspec = self.display_controller.get_command(page)
        return argspec.help_verbose

    def print(self, page, options=tuple(), **koptions):
        """ArgSpec
        Print a page in the console

        Similar to browse command, but instead prints in console.
        See pages for what can be printed.
        ___
        PAGE Page to print
        *OPTIONS Positional parameters for page
        **KOPTIONS Keyword parameters for page
        """
        with arg_validation(f'Couldn\'t find page: {page}'):
            assert self.display_controller.has(page)

        s = self.display_controller.do_command(page,
            custom_args=options, custom_kwargs=koptions)
        self.output_console(s)

    def browse(self, page, options=tuple(), **koptions):
        """ArgSpec
        Open a page in the browser

        Opens a page in the browser, which will automatically refresh.
        See pages for what can be printed.
        ___
        PAGE Page to open
        *OPTIONS Positional parameters for page
        **KOPTIONS Keyword parameters for page
        """
        with arg_validation(f'Couldn\'t find page: {page}'):
            assert self.display_controller.has(page)

        self.display_controller.cache('__browser_page', page)
        self.display_controller.cache('__browser_options', options)
        self.display_controller.cache('__browser_koptions', koptions)

    def help(self, *args):
        """Show help"""
        self.print('help')
        self.browse('help')

    def stack_content(self, stack, size=NO_SIZE_LIMIT):
        line_count = size[1]
        sliced = itertools.islice(stack, 0, line_count)
        full = '\n'.join(reversed(list(sliced)))
        lines = full.split('\n')[-line_count:]
        return '\n'.join(lines)

    @property
    def feedback_str(self):
        return self.feedback_stack[0]

    def __get_content_help(self):
        return HELP

    def __get_content_hotkeys(self):
        return 'Registered hotkeys:\n'+'\n'.join([
            f'<green>{k:>11}</green>: <orange>{v}</orange>' for k, v in CONFIG_DATA['HOTKEY_COMMANDS'].items()])



HELP = """<orange><bold>Welcome to space.</bold></orange>

To show this help, press enter to activate the prompt and use the command: <code>help</code>
For a quick tour of the galaxy, use: <code>tour</code>

To see available commands, use: <code>print commands</code>
To learn about a command (e.g. <i>cockpit.rotate</i>), use: <code>print command cockpit.rotate</code>
To see more printables, use: <code>print pages</code>
"""
