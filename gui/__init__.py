
import os, sys, traceback
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.controls import FormattedTextControl


class SizeAwareFormattedTextControl(FormattedTextControl):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.last_size = 1, 1

    def create_content(self, width, height):
        self.last_size = width, height
        return super().create_content(width, height)


COLOR_HEXES = {
    'black': '#000000',
    'white': '#ffffff',
    'gray': '#aaaaaa',
    'red': '#ff0000',
    'green': '#00ff00',
    'blue': '#0000ff',
    'yellow': '#ffff00',
    'orange': '#ffbb00',
    'brown': '#bb5500',
    'cyan': '#00ffff',
    'magenta': '#ff00ff',
    'pink': '#ff00aa',
    'purple': '#ff00ff',
}
COLORS = list(COLOR_HEXES.keys())
OBJECT_COLORS = COLORS[3:]
STYLE = Style.from_dict({
    'code': '#44ff00 italic',
    'h1': '#0044ff bold underline bg:#ffffff',
    'h2': '#ffffff bold underline bg:#000055',
    'h3': f'#ffbb00 bold underline',
    'map': 'bg:#00001a',
    'bar': 'bg:#1a0000',
    'highlight': '#000000 bg:#ffffff',
    'darkbg': 'bg:#000055',
    **COLOR_HEXES,
})


def tag(tag, s):
    return f'<{tag}>{s}</{tag}>'


def escape_html(s):
    r = str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return r


def restart_script():
    os.execl(sys.executable, sys.executable, *sys.argv)


def window_size():
    return os.get_terminal_size()


def format_latlong(v, rounding=1):
    return ', '.join(f"{f'{round(_, rounding)}°':>7}" for _ in v)


def format_vector(v):
    return ','.join(f'{f"{_:.3e}":>10}' for _ in v)


def resolve_prompt_input(s):
    command, *args = s.split(' ')
    args = [try_number(a) for a in args]
    return command, args


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
