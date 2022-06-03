FPS = 20
DEFAULT_SIMRATE = -5

CELESTIAL_BODIES = 5
COMPUTER_PLAYERS = 100

LAYOUT_SCREENS = {
    'multi': ['display', 'browser'],
    'debug': ['debug', 'events'],
    'display': ['display'],
}

HOTKEY_COMMANDS = {
    '^ f12': 'debug',
    '^ f1': 'layout.screen 0',
    '^ f2': 'layout.screen 1',
    '^ f3': 'layout.screen 2',
    '^ f4': 'layout.screen 3',
    'tab': 'layout.screen.next',
    'enter': 'prompt.focus',
    '^ c': 'prompt.clear',
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
    'K': 'ship.cut',
    'J': 'ship.break 1',
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
}
