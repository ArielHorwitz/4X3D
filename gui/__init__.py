
import os, sys
from prompt_toolkit.styles import Style
from logic.quaternion import latlong


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
    # 'display': 'bg:#222222',
    'highlight': '#000000 bg:#ffffff',
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
    return ', '.join(f"{f'{round(_, rounding)}°':>7}" for _ in latlong(v))


def format_vector(v, rounding=1):
    return ','.join(f'{round(_, rounding):>5}' for _ in v)
