import math
import numpy as np
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size, OBJECT_COLORS
from logic.logic import CELESTIAL_NAMES


ASCII_ASPECT_RATIO = 29/64
RADIANS_IN_DEGREES = 57.296


class Display(Window):
    def __init__(self, app):
        self.text_control = FormattedTextControl(text='Display')
        super().__init__(content=self.text_control)
        self.app = app
        self.camera_pos = np.asarray([-100, 0, 0], dtype=np.float64)
        self.show_labels = True

    def toggle_labels(self, set_to=None):
        set_to = not self.show_labels if set_to is None else set_to
        self.show_labels = set_to
        self.app.feedback_str = f'Showing labels: {set_to}'

    def reset_camera(self, x=-100, y=0, z=0):
        self.camera_pos = np.asarray([x, y, z], dtype=np.float64)

    def move_camera(self, x=0, y=0, z=0):
        self.camera_pos += (x, y, z)

    def update(self):
        self.width = int(window_size().columns * 0.7)
        self.height = int(window_size().lines - 4)
        s = [[' ']*self.width for _ in range(self.height)]
        labels = []
        latlongs = self.get_projection(self.app.universe.positions)
        pix_pos = self.latlong2pix(latlongs)
        for i, (x, y) in enumerate(pix_pos):
            x, y = round(x), round(self.height-y)
            if any([x < 0, y < 0, x >= self.width, y >= self.height]):
                continue
            tag = OBJECT_COLORS[i%len(OBJECT_COLORS)]
            s[y][x] = f'<{tag}><bold>•</bold></{tag}>'
            if self.show_labels:
                real_pos = self.app.universe.positions[i]
                rpos = ','.join(f'{c:.1f}' for c in real_pos)
                ll = ','.join(f'{round(_)}°' for _ in latlongs[i])
                lbl = f'{ll} | {rpos}'
                labels.append((x, y, f'{CELESTIAL_NAMES[i]} ({lbl})'))
        for x, y, label in labels:
            write_label(s, x, y, label)
        s = '<display>' + '\n'.join(''.join(_) for _ in s) + '</display>'
        self.text_control.text = HTML(s)

    def get_projection(self, pos):
        # Convert 3d position to mercator projection
        pos = pos - self.camera_pos
        return np.asarray([latlong(c) for c in pos])

    def latlong2pix(self, pos):
        # Aspect ration and offset
        pix = pos * (1, ASCII_ASPECT_RATIO)
        pix += (self.width//2, self.height//2)
        return tuple(tuple(round(x) for x in _) for _ in pix)



def latlong(vector):
    """
    Given an observer at the origin, gives the longitude and latitude
    of a vector projected onto a sphere around the origin/observer,
    such that the 0°, 0° corresponds to a vector at (1, 0, 0) and 45°, 45°
    corresponds to a vector at (1, -1, 1).

    A simpler way of conceptualizing this is considering the observer at
    the origin and using the right hand rule, looking straight at the x+
    axis with the y+ axis to their left and the z+ axis atop them. We
    find the angles to rotate clockwise and pitch up in order to look at
    the vector.
    """
    def pad_plank_length(scalar):
        if scalar < 0:
            return min(scalar, 10**-20)
        return max(scalar, 10**-20)

    magnitude = np.linalg.norm(vector)
    if magnitude == 0:
        return 0, 0

    theta = math.atan(vector[1] / pad_plank_length(vector[0]))
    if vector[0] < 0:
        theta += math.pi
    long = (theta * RADIANS_IN_DEGREES) * -1

    phi = math.asin(vector[2] / pad_plank_length(magnitude))
    lat = (phi * RADIANS_IN_DEGREES)
    return long, lat


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
