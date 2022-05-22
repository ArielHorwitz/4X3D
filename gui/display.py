import numpy as np
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size, OBJECT_COLORS


class Display(Window):
    def __init__(self, app):
        self.text_control = FormattedTextControl(text='Display')
        super().__init__(content=self.text_control)
        self.app = app

    def update(self):
        self.width = int(window_size().columns * 0.7)
        self.height = int(window_size().lines - 4)
        positions = self.app.universe.positions
        s = [[' ']*self.width for _ in range(self.height)]
        pos = positions + (self.width//2, self.height//2)
        labels = []
        for i, (x, y) in enumerate(parse_positions(pos)):
            if any([
                x < 0,
                y < 0,
                x >= self.width,
                y >= self.height,
            ]):
                continue
            tag = OBJECT_COLORS[i%len(OBJECT_COLORS)]
            s[y][x] = f'<{tag}><bold>•</bold></{tag}>'
            labels.append((x, y, f'Object #{i}'))
        for x, y, label in labels:
            write_label(s, x, y, label)
        s = '<display>' + '\n'.join(''.join(_) for _ in s) + '</display>'
        self.text_control.text = HTML(s)


def write_label(charmap, x, y, name):
    mode = None
    x += 1
    normal = count_empty_spaces(charmap, x, y)
    if normal >= len(name):
        insert_label(charmap, x, y, name)
        return
    below = count_empty_spaces(charmap, x, y+1)
    if below >= len(name):
        insert_label(charmap, x, y+1, name)
        return
    above = count_empty_spaces(charmap, x, y-1)
    if above >= len(name):
        insert_label(charmap, x, y-1, name)
        return
    options = [above, normal, below]
    idy = np.argmax(np.asarray(options)) - 1
    if options[idy] > 3:
        insert_label(charmap, x, y+idy, name)


def insert_label(charmap, x, y, name):
    width = len(charmap[0])
    for i, char in enumerate(name):
        if x+i >= width or charmap[y][x+i] != ' ':
            break
        charmap[y][x+i] = char


def count_empty_spaces(charmap, x, y):
    if y >= len(charmap):
        return -1
    total = 0
    width = len(charmap[0])
    while x < width and charmap[y][x] == ' ':
        x += 1
        total += 1
    return total


def parse_positions(a):
    return tuple((round(xy[0]), round(xy[1])) for xy in a)
