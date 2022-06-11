from collections import namedtuple

_SPLIT_ATTRS = 'children', 'width', 'height'
_WIN_ATTRS = 'window', 'width', 'height'
_SPLIT_DEFAULTS = [], 1000, 1000
_WIN_DEFAULTS = 'help', 1000, 1000
VSubLayout = namedtuple('VerticalSublayout', _SPLIT_ATTRS, defaults=_SPLIT_DEFAULTS)
HSubLayout = namedtuple('HorizontalSublayout', _SPLIT_ATTRS, defaults=_SPLIT_DEFAULTS)
WSubLayout = namedtuple('WindowSublayout', _WIN_ATTRS, defaults=_WIN_DEFAULTS)
