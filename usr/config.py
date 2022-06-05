from loguru import logger
import json
from pathlib import Path


def file_dump(file, d, clear=True):
    with open(file, 'w' if clear else 'a') as f:
        f.write(d)

def file_load(file):
    with open(file, 'r') as f:
        d = f.read()
    return d


DEFAULT_CONFIG_DATA = {
    # Graphics
    'FPS': 20,
    'DEFAULT_SIMRATE': -100,
    'ASPECT_RATIO_X': 29,
    'ASPECT_RATIO_Y': 64,
    'CROSSHAIR_COLOR': 'pink',
    'SHOW_LABELS': 0,
    # Spawn
    'SPAWN_OFFSET': {
        'star': 10**6,
        'rock': 10**4,
    },
    'SPAWN_RATE': {
        'star': (10, 1),
        'rock': (30, 10),
    },
    'COMPUTER_PLAYERS': 50,
    # Layout
    'LAYOUT_SCREENS': {
        'multi': ['display', 'browser'],
        'debug': ['debug', 'events', 'browser'],
        'display': ['display'],
    },
    # Custom commands
    'CUSTOM_COMMANDS': {
        'debug': 'debug && uni.debug',
        'obs': 'cockpit.follow && cockpit.move -10_000_000',
        'init': '&recursion && recenter && ship.break 1',
        'recenter': f'cockpit.follow && inspect 0 && cockpit.reset_zoom',
    },
    # Hotkeys
    'HOTKEY_COMMANDS': {
        # gui controls
        'enter': 'prompt.focus',
        '^ c': 'prompt.clear',
        'tab': 'layout.screen.next',
        '+ tab': 'layout.screen.prev',
        'f1': 'layout.screen 0',
        'f2': 'layout.screen 1',
        'f3': 'layout.screen 2',
        'f4': 'layout.screen 3',
        '^ f12': 'debug',
        # universe simulation
        'space': 'sim.toggle',
        '^ t': 'sim.tick 1',
        '^ v': 'sim.randv',
        '^ f': 'sim.flipv',
        '^ pageup': 'sim.rate +10 1',
        '^+ pageup': 'sim.rate +100 1',
        '^ pagedown': 'sim.rate -10 1',
        '^+ pagedown': 'sim.rate -100 1',
        # ship window controls
        'I': 'ship.burn',
        'J': 'ship.cut',
        'K': 'ship.break 1',
        '^ l': 'cockpit.labels',
        'up': 'cockpit.move +100',
        '+ up': 'cockpit.move +1',
        'down': 'cockpit.move -100',
        '+ down': 'cockpit.move -1',
        'left': 'cockpit.strafe +100',
        '+ left': 'cockpit.strafe +1',
        'right': 'cockpit.strafe -100',
        '+ right': 'cockpit.strafe -1',
        # ship window pov
        'home': 'cockpit.zoom 2',
        'end': 'cockpit.zoom 0.5',
        '+ home': 'cockpit.zoom 1.25',
        '+ end': 'cockpit.zoom 0.8',
        'd': 'cockpit.rotate +15',
        'D': 'cockpit.rotate +1',
        'a': 'cockpit.rotate -15',
        'A': 'cockpit.rotate -1',
        'w': 'cockpit.rotate 0 +15',
        'W': 'cockpit.rotate 0 +1',
        's': 'cockpit.rotate 0 -15',
        'S': 'cockpit.rotate 0 -1',
        'e': 'cockpit.rotate 0 0 -15',
        'E': 'cockpit.rotate 0 0 -1',
        'q': 'cockpit.rotate 0 0 +15',
        'Q': 'cockpit.rotate 0 0 +1',
        'x': 'cockpit.flip',
        'X': 'cockpit.flip',
    },
}

CONFIG_FILE = Path.cwd() / 'settings.json'
DELETE_CONFIG_FLAG = (Path.cwd() / '.deletesettings').is_file()
if CONFIG_FILE.is_file() and DELETE_CONFIG_FLAG:
    CONFIG_FILE.unlink()
if not CONFIG_FILE.is_file():
    file_dump(CONFIG_FILE, json.dumps(DEFAULT_CONFIG_DATA, indent=2))

CONFIG_DATA = json.loads(file_load(CONFIG_FILE))
logger.debug(f'CONFIG_DATA:\n{CONFIG_DATA}')

CONFIG_DATA['ASPECT_RATIO'] = CONFIG_DATA['ASPECT_RATIO_X'] / CONFIG_DATA['ASPECT_RATIO_Y']
