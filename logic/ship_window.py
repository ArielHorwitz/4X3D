from loguru import logger
import numpy as np
from functools import partial

from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.camera import Camera
from logic.quaternion import Quaternion as Quat, latlong, unit_vectors


ASCII_ASPECT_RATIO = 29/64


class ShipWindow:
    def __init__(self, universe):
        self.universe = universe
        self.camera = Camera()
        self.show_labels = 1
        self.camera_following = None
        self.camera_tracking = None

    def handle_command(self, command, args):
        if hasattr(self, f'command_{command}'):
            f = getattr(self, f'command_{command}')
            return f(*args)
        try:
            return self.camera.handle_command(command, args)
        except KeyError as e:
            logger.warning(f'ShipWindow requested to handle unknown command: {command} {args}')

    def command_follow(self, index=None):
        def get_pos(index):
            return self.universe.positions[index]
        self.camera.follow(partial(get_pos, index) if index is not None else None)

    def command_track(self, index=None):
        def get_pos(index):
            return self.universe.positions[index]
        self.camera.track(partial(get_pos, index) if index is not None else None)

    def command_look(self, index):
        self.camera.look_at_vector(self.universe.positions[index])

    def command_labels(self):
        self.show_labels = (self.show_labels + 1) % 4
        logger.info(f'Showing labels: {self.show_labels}')

    # Display
    def get_charmap(self, size):
        self.camera.update()
        self.width, self.height = size
        if self.width < 2 or self.height < 2:
            return '??'
        self.height -= 1
        charmap = [[' ']*self.width for _ in range(self.height)]
        self.add_projection_axes(charmap)
        self.add_objects(charmap)
        self.add_crosshair(charmap, horizontal=True, diagonal=True)
        s = '<display>' + '\n'.join(''.join(_) for _ in charmap) + '</display>'
        s = f'{s}\n{self.camera.get_bar()}'
        return s

    def add_objects(self, charmap):
        pix_pos = self.get_projected_pixels(self.universe.positions)
        labels = []
        for i, x, y in pix_pos:
            tag = OBJECT_COLORS[i%len(OBJECT_COLORS)]
            charmap[y][x] = f'<{tag}><bold>•</bold></{tag}>'
            if self.show_labels:
                lbl = CELESTIAL_NAMES[i]
            if self.show_labels > 1:
                lbl = f'#{i}.{lbl}'
            if self.show_labels > 2:
                dist = np.linalg.norm(self.camera.pos - self.universe.positions[i])
                lbl = f'{lbl} ({dist:.1f})'
            if self.show_labels:
                labels.append((x, y, lbl))
        for x, y, label in labels:
            write_label(charmap, x, y, label)

    def add_projection_axes(self, charmap):
        coords = unit_vectors()
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
        pos = pos - self.camera.pos
        rv = Quat.rotate_vectors(pos, self.camera.rotation)
        ll_coords = latlong(rv)
        return ll_coords

    def get_projected_pixels(self, pos):
        # Convert 3d position to mercator projection
        ll_coords = self.get_projected_coords(pos)
        pix = ll_coords * [1, ASCII_ASPECT_RATIO] * self.camera.zoom
        pix += [self.width/2, self.height/2]
        pix[:, 1] = self.height - pix[:, 1]
        above_botleft = (pix[:, 0] >= 0) & (pix[:, 1] >= 0)
        below_topright = (pix[:, 0] < self.width-1) & (pix[:, 1] < self.height-1)
        not_on_camera_pos = (pos != self.camera.pos).sum(axis=-1) > 0
        valid = above_botleft & below_topright & not_on_camera_pos
        pix = pix[valid]
        r = np.concatenate((np.flatnonzero(valid)[:, None], pix), axis=-1)
        r = np.asarray(np.round(r), dtype=np.int32)
        return r


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
