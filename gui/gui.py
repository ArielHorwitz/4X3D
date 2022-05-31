from loguru import logger
import sys
import traceback
import asyncio
import prompt_toolkit
import arrow
from prompt_toolkit import Application
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import VSplit, HSplit, Window
from prompt_toolkit.widgets import VerticalLine, HorizontalLine, Frame, TextArea
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
import prompt_toolkit.shortcuts

from gui import STYLE, restart_script, window_size
from gui.screenswitch import ScreenSwitcher
from gui.prompt import Prompt
from gui.keybinds import get_keybindings, encode_keyseq
from logic.universe import Universe


FPS = 20
FRAME_TIME = 1 / FPS
logger.info(f'Running at {FPS} FPS ({FRAME_TIME*1000:.1f} ms)')
HOTKEY_COMMANDS = {
    '^ f12': 'debug',
    '^ f1': 'screen 0',
    '^ f2': 'screen 1',
    'tab': 'nextscreen',
    'enter': 'focus',
    # universe simulation
    'space': 'sim toggle',
    '^ t': 'sim ticks 1',
    '^ v': 'sim randomize_vel',
    '^ f': 'sim flip',
    '^ pageup': 'sim rate +10 1',
    '^+ pageup': 'sim rate +100 1',
    '^ pagedown': 'sim rate -10 1',
    '^+ pagedown': 'sim rate -100 1',
    # ship window controls
    '^ l': 'ship labels',
    'up': 'ship move +100',
    '+ up': 'ship move +1',
    'down': 'ship move -100',
    '+ down': 'ship move -1',
    'left': 'ship strafe +100',
    '+ left': 'ship strafe +1',
    'right': 'ship strafe -100',
    '+ right': 'ship strafe -1',
    # ship window pov
    'home': 'ship zoom 2',
    'end': 'ship zoom 0.5',
    '+ home': 'ship zoom 1.25',
    '+ end': 'ship zoom 0.8',
    'd': 'ship rotate +15',
    'D': 'ship rotate +1',
    'a': 'ship rotate -15',
    'A': 'ship rotate -1',
    'w': 'ship rotate 0 +15',
    'W': 'ship rotate 0 +1',
    's': 'ship rotate 0 -15',
    'S': 'ship rotate 0 -1',
    'e': 'ship rotate 0 0 -15',
    'E': 'ship rotate 0 0 -1',
    'q': 'ship rotate 0 0 +15',
    'Q': 'ship rotate 0 0 +1',
    'x': 'ship flip',
    'X': 'ship flip',
}


class App(Application):
    def __init__(self):
        print(HTML('<i>Initializing app...</i>'))
        prompt_toolkit.shortcuts.clear()
        prompt_toolkit.shortcuts.set_title('Space')
        self.universe = Universe()
        self.root_layout = self.get_layout()
        self.commands = self.get_commands()
        kb = get_keybindings(
            global_keys={'^ q': self.exit, '^ w': restart_script},
            condition=self.hotkeys_enabled,
            handler=self.handle_hotkey,
        )

        super().__init__(
            layout=self.root_layout,
            style=STYLE,
            full_screen=True,
            key_bindings=kb,
        )

    def debug(self, *a):
        logger.debug(f'Debug action called: {a}')

    def hotkeys_enabled(self):
        return not self.root_layout.buffer_has_focus

    def get_commands(self):
        return {
            'exit': self.exit,
            'quit': self.exit,
            'restart': restart_script,
            'debug': self.debug,
            'focus': self.focus_prompt,
            'screen': self.screen_switcher.switch_to,
            'nextscreen': self.screen_switcher.next_screen,
        }

    def get_layout(self):
        self.prompt_window = Prompt(self, self.handle_prompt_input)
        self.screen_switcher = ScreenSwitcher(app=self, screens={
            'multi': ['display', 'debug'],
            'display': ['display'],
            'debug': ['debug'],
        })
        root_container = HSplit([
            self.screen_switcher,
            self.prompt_window,
        ])
        return Layout(root_container)

    def handle_prompt_input(self, text):
        self.defocus_prompt()
        if not text:
            return
        command, args = self.resolve_prompt_input(text)
        if command in self.commands:
            logger.debug(f'Running command: {command} {args}')
            c = self.commands[command]
            c(*args)
        else:
            self.universe.handle_command(command, args)

    def resolve_prompt_input(self, s):
        command, *args = s.split(' ')
        args = [try_number(a) for a in args]
        return command, args

    def get_window_content(self, name, size=None):
        size = self.screen_size if size is None else size
        content = self.universe.get_window_content(name, size)
        return HTML(content)

    def defocus_prompt(self):
        self.prompt_window.defocus()

    def focus_prompt(self):
        self.prompt_window.focus()

    def handle_hotkey(self, key):
        if key in HOTKEY_COMMANDS:
            prompt_input = HOTKEY_COMMANDS[key]
            logger.debug(f'Hotkey <{key}> resolved to: {prompt_input}')
            self.handle_prompt_input(prompt_input)
        else:
            logger.debug(f'Unknown hotkey <{key}>')

    async def logic_loop(self):
        while True:
            self.universe.update()
            await asyncio.sleep(FRAME_TIME)

    async def refresh_window(self):
        while True:
            self.screen_switcher.update()
            self.prompt_window.update()
            self.invalidate()
            await asyncio.sleep(FRAME_TIME)

    def run(self):
        self.create_background_task(self.logic_loop())
        self.create_background_task(self.refresh_window())
        asyncio.get_event_loop().run_until_complete(self.run_async(pre_run=self.prerun))

    def prerun(self):
        self.defocus_prompt()

    @property
    def screen_size(self):
        width = window_size().columns - 2
        height = window_size().lines - 4
        return width, height

def try_number(v):
    try:
        r = float(v)
        if r == int(r):
            r = int(r)
        return r
    except ValueError as e:
        return v


def format_exc(e):
    strs = []
    for line in traceback.format_exception(*sys.exc_info()):
        strs.append(str(line))
    return ''.join(strs)
