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
    'CAMERA_SMOOTH_TIME': 1000,
    'CAMERA_SMOOTH_CURVE': 0.75,
    # Spawn
    'SPAWN_OFFSET': {
        'star': 10**6,
        'rock': 10**4,
    },
    'SPAWN_RATE': {
        'star': (10, 1),
        'rock': (30, 10),
    },
    'COMPUTER_PLAYERS': 5,
    # Custom commands
    'CUSTOM_COMMANDS': {
        'debug': 'gui.debug && uni.debug',
    },
    # Hotkeys
    'HOTKEY_COMMANDS': {
        # gui controls
        'enter': 'gui.prompt.focus',
        '^ c': 'gui.prompt.clear',
        'tab': 'gui.layout.screen.next',
        '+ tab': 'gui.layout.screen.prev',
        'f1': 'gui.layout.screen 0',
        'f2': 'gui.layout.screen 1',
        'f3': 'gui.layout.screen 2',
        'f4': 'gui.layout.screen 3',
        'f5': 'gui.layout.screen 4',
        'f6': 'gui.layout.screen 5',
        'f7': 'gui.layout.screen 6',
        'f8': 'gui.layout.screen 7',
        '^ f12': 'gui.debug',
        # universe simulation
        'space': 'sim.toggle',
        '^ t': 'sim.tick 1',
        '^ pageup': 'sim.rate +10 --d',
        '^+ pageup': 'sim.rate +100 --d',
        '^ pagedown': 'sim.rate -10 --d',
        '^+ pagedown': 'sim.rate -100 --d',
        # ship window controls
        'I': 'ship.burn',
        'J': 'ship.cut',
        'K': 'ship.break --auto',
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
        'd': 'cockpit.rotate --y +15 --scale',
        'D': 'cockpit.rotate --y +1 --scale',
        'a': 'cockpit.rotate --y -15 --scale',
        'A': 'cockpit.rotate --y -1 --scale',
        'w': 'cockpit.rotate --p +15 --scale',
        'W': 'cockpit.rotate --p +1 --scale',
        's': 'cockpit.rotate --p -15 --scale',
        'S': 'cockpit.rotate --p -1 --scale',
        'e': 'cockpit.rotate --r -15 --scale',
        'E': 'cockpit.rotate --r -1 --scale',
        'q': 'cockpit.rotate --r +15 --scale',
        'Q': 'cockpit.rotate --r +1 --scale',
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
