from loguru import logger
import math
import numpy as np
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size, OBJECT_COLORS
from logic.logic import CELESTIAL_NAMES
from logic.quaternion import Quaternion as Quat, latlong


ASCII_ASPECT_RATIO = 29/64
RADIANS_IN_DEGREES = 57.296


class Display(Window):
    def __init__(self, app):
        self.text_control = FormattedTextControl(text='Display')
        super().__init__(content=self.text_control)
        self.app = app
        self.camera_rot = np.asarray([1, 0, 0, 0])
        self.show_labels = False

    # Flight controls
    def move(self, d=1):
        self.app.universe.move(self.camera_axes[0] * d)

    def strafe(self, d=1):
        self.app.universe.move(self.camera_axes[1] * d)

    def fly(self, dv=1):
        self.app.universe.fly(self.camera_axes[0] * dv)

    def break_move(self):
        self.app.universe.break_move()

    # Camera control
    @property
    def camera_pos(self):
        return self.app.universe.my_pos

    @property
    def camera_axes(self):
        return Quat.get_rotated_axes(self.camera_rot)

    def reset_camera(self):
        self.camera_rot = np.asarray([1,0,0,0], dtype=np.float64)

    def rotate_camera(self, yaw=0, pitch=0, roll=0):
        axes = self.camera_axes
        if yaw:
            yaw_qrot = Quat.from_vector_angle(axes[2], yaw)
            logger.debug(f'Rotating: {yaw}° yaw')
            self.camera_rot = Quat.multi(self.camera_rot, yaw_qrot)
        elif pitch:
            pitch_qrot = Quat.from_vector_angle(axes[1], pitch)
            logger.debug(f'Rotating: {pitch}° pitch')
            self.camera_rot = Quat.multi(self.camera_rot, pitch_qrot)
        elif roll:
            roll_qrot = Quat.from_vector_angle(axes[0], roll)
            logger.debug(f'Rotating: {roll}° roll')
            self.camera_rot = Quat.multi(self.camera_rot, roll_qrot)

    def flip_camera(self):
        self.rotate_camera(yaw=180)

    # Display
    def update(self):
        self.width = int(window_size().columns * 0.7)
        self.height = int(window_size().lines - 4)
        charmap = [[' ']*self.width for _ in range(self.height)]
        self.add_projection_axes(charmap)
        self.add_objects(charmap)
        self.add_crosshair(charmap, horizontal=True, diagonal=True)
        s = '<display>' + '\n'.join(''.join(_) for _ in charmap) + '</display>'
        self.text_control.text = HTML(s)

    def add_objects(self, charmap):
        pix_pos = self.get_projected_pixels(self.app.universe.positions)
        labels = []
        for i, x, y in pix_pos:
            tag = OBJECT_COLORS[i%len(OBJECT_COLORS)]
            charmap[y][x] = f'<{tag}><bold>•</bold></{tag}>'
            lbl = ''
            if self.show_labels:
                dist = np.linalg.norm(self.camera_pos - self.app.universe.positions[i])
                lbl = f' ({dist:.1f})'
            labels.append((x, y, f'#{i}.{CELESTIAL_NAMES[i]}{lbl}'))
        for x, y, label in labels:
            write_label(charmap, x, y, label)

    def add_projection_axes(self, charmap):
        inf = 10**100
        coords = np.asarray([
            [inf, 0, 0],
            [-inf, 0, 0],
            [0, inf, 0],
            [0, -inf, 0],
            [0, 0, inf],
            [0, 0, -inf],
        ], dtype=np.float64)
        labels = ['X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-']
        pix_pos = self.get_projected_pixels(coords)
        for i, x, y in pix_pos:
            charmap[y][x] = f'<bold>╬</bold>'
            write_label(charmap, x, y, labels[i])

    def add_crosshair(self, charmap, horizontal=True, diagonal=False):
        cx, cy = round(self.width/2), round(self.height/2)
        if horizontal:
            write_char(charmap, cx, cy-1, '│')
            write_char(charmap, cx, cy+1, '│')
            write_char(charmap, cx-1, cy, '─')
            write_char(charmap, cx+1, cy, '─')
        if diagonal:
            write_char(charmap, cx+1, cy+1, '\\')
            write_char(charmap, cx-1, cy-1, '\\')
            write_char(charmap, cx-1, cy+1, '/')
            write_char(charmap, cx+1, cy-1, '/')

    def get_projected_coords(self, pos):
        pos = pos - self.camera_pos
        rv = Quat.rotate_vectors(pos, self.camera_rot)
        ll_coords = latlong(rv)
        return ll_coords

    def get_projected_pixels(self, pos):
        # Convert 3d position to mercator projection
        ll_coords = self.get_projected_coords(pos)
        pix = ll_coords * [1, ASCII_ASPECT_RATIO]
        pix += [self.width/2, self.height/2]
        pix[:, 1] = self.height - pix[:, 1]
        above_botleft = (pix[:, 0] >= 0) & (pix[:, 1] >= 0)
        below_topright = (pix[:, 0] < self.width-1) & (pix[:, 1] < self.height-1)
        not_on_camera_pos = (pos != self.camera_pos).sum(axis=-1) > 0
        valid = above_botleft & below_topright & not_on_camera_pos
        pix = pix[valid]
        r = np.concatenate((np.flatnonzero(valid)[:, None], pix), axis=-1)
        r = np.asarray(np.round(r), dtype=np.int32)
        return r

    def toggle_labels(self, set_to=None):
        set_to = not self.show_labels if set_to is None else set_to
        self.show_labels = set_to
        self.app.feedback_str = f'Showing labels: {set_to}'


def write_char(charmap, x, y, char, overwrite=False):
    if overwrite or charmap[y][x] == ' ':
        charmap[y][x] = char
        return True
    return False


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
        charmap[y][x+i] = char if char != ' ' else '<whitespace> </whitespace>'


def count_empty_spaces(charmap, x, y):
    if y >= len(charmap):
        return -1
    total = 0
    width = len(charmap[0])
    while x < width and charmap[y][x] == ' ':
        x += 1
        total += 1
    return total
