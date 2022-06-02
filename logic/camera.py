from loguru import logger
import numpy as np
from logic.quaternion import Quaternion as Quat, latlong_single, latlong, unit_vectors
from gui import format_latlong, format_vector, ASCII_ASPECT_RATIO


class Camera:
    def __init__(self):
        self.pos = np.asarray([0,0,0], dtype=np.float64)
        self.reset_zoom()
        self.reset_rotation()
        self.following = None
        self.tracking = None
        self.commands = {
            'move': self.move,
            'strafe': self.strafe,
            'reset_rotation': self.reset_rotation,
            'reset_zoom': self.reset_zoom,
            'flip': self.flip,
            'zoom': self.adjust_zoom,
            'rotate': self.rotate,
        }

    def follow(self, callback=None):
        if callback is not None:
            assert callable(callback)
        self.following = callback

    def track(self, callback=None):
        if callback is not None:
            assert callable(callback)
        self.tracking = callback

    def update(self):
        if self.following is not None:
            self.pos = np.copy(self.following())
        if self.tracking is not None:
            self.look_at_vector(self.tracking(), disable_track=False)

    def set_position(self, point):
        self.pos = np.asarray(point, dtype=np.float64)

    def move(self, d=1, disable_follow=True):
        self.pos += self.current_axes[0] * d
        if disable_follow:
            self.follow(None)

    def strafe(self, d=1, disable_follow=True):
        self.pos += self.current_axes[1] * d
        if disable_follow:
            self.follow(None)

    @property
    def zoom(self):
        return self.__zoom_level

    @property
    def current_axes(self):
        return Quat.get_rotated_axes(self.rotation)

    def reset_zoom(self):
        self.__zoom_level = 1

    def reset_rotation(self, disable_track=True):
        self.rotation = np.asarray([1,0,0,0], dtype=np.float64)
        if disable_track:
            self.track(None)

    def rotate(self, yaw=0, pitch=0, roll=0, consider_zoom=True, disable_track=True):
        axes = self.current_axes
        if consider_zoom:
            yaw /= self.__zoom_level
            pitch /= self.__zoom_level
        if yaw:
            yaw_qrot = Quat.from_vector_angle(axes[2], yaw)
            self.rotation = Quat.multi(self.rotation, yaw_qrot)
        elif pitch:
            pitch_qrot = Quat.from_vector_angle(axes[1], pitch)
            self.rotation = Quat.multi(self.rotation, pitch_qrot)
        elif roll:
            roll_qrot = Quat.from_vector_angle(axes[0], roll)
            self.rotation = Quat.multi(self.rotation, roll_qrot)
        if disable_track:
            self.track(None)

    def flip(self):
        self.rotate(yaw=180, consider_zoom=False)
        self.track(None)

    def adjust_zoom(self, zoom_multiplier):
        self.__zoom_level = max(0.5, self.__zoom_level * zoom_multiplier)

    def look_at_vector(self, vector, reset_axes=True, disable_track=True):
        if reset_axes:
            self.reset_rotation(disable_track=disable_track)
        rotated = Quat.rotate_vector(vector - self.pos, self.rotation)
        lat, long = latlong_single(rotated)
        self.rotate(yaw=lat, consider_zoom=False, disable_track=disable_track)
        self.rotate(pitch=long, consider_zoom=False, disable_track=disable_track)

    @property
    def lat_long(self):
        return latlong_single(self.current_axes[0])

    # Projected view character map
    def get_charmap(self, size, points, tags, labels, show_bar=True):
        width, height = size
        if width < 3 or height < 3:
            return '┼'
        self.update()
        bar_str = ' ' * width
        if show_bar:
            height -= 1
            size = width, height
            bar_str = f'\n{self.get_bar()}'
        charmap = [[' '] * width for _ in range(height)]
        self.add_projection_axes(charmap, size)
        self.add_objects(charmap, size, points, tags, labels)
        self.add_crosshair(charmap, size, horizontal=True, diagonal=True)
        map_str = '\n'.join(''.join(_) for _ in charmap)
        map_str = f'{map_str}{bar_str}'
        return map_str

    def get_bar(self):
        following = '<grey>FLW</grey>' if self.following is None else '<h2>FLW</h2>'
        tracking = '<grey>TRK</grey>' if self.tracking is None else '<h2>TRK</h2>'
        camera_str = f'{following} {tracking}'
        return ' | '.join([
            f'<code>{camera_str}</code>',
            f'<code>{format_latlong(self.lat_long)}</code>',
            f'<code>x{self.zoom:.2f}</code>',
            f'<code>[{format_vector(self.pos)}]</code>',
        ])

    def add_objects(self, charmap, size, points, tags, labels):
        pix_pos = self.get_projected_pixels(points, size)
        for i, x, y in pix_pos:
            write_char(charmap, x, y, wrap_tags('•', [tags[i], 'bold']))
            write_label(charmap, x, y, labels[i])

    def add_projection_axes(self, charmap, size):
        coords = unit_vectors()
        labels = ['X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-']
        pix_pos = self.get_projected_pixels(coords, size)
        for i, x, y in pix_pos:
            write_char(charmap, x, y, wrap_tag('╬', 'bold'))
            write_label(charmap, x, y, labels[i])

    def add_crosshair(self, charmap, size, horizontal=True, diagonal=False):
        width, height = size
        cx, cy = round(width/2), round(height/2)
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
        rv = Quat.rotate_vectors(pos - self.pos, self.rotation)
        ll_coords = latlong(rv)
        return ll_coords

    def get_projected_pixels(self, points, size):
        # Convert 3d position to mercator projection
        width, height = size
        ll_coords = self.get_projected_coords(points)
        pix = ll_coords * [1, ASCII_ASPECT_RATIO] * self.zoom
        pix += [width/2, height/2]
        pix[:, 1] = height - pix[:, 1]
        above_botleft = (pix[:, 0] >= 0) & (pix[:, 1] >= 0)
        below_topright = (pix[:, 0] < width-1) & (pix[:, 1] < height-1)
        not_on_camera_pos = (points != self.pos).sum(axis=-1) > 0
        valid = above_botleft & below_topright & not_on_camera_pos
        pix = pix[valid]
        r = np.concatenate((np.flatnonzero(valid)[:, None], pix), axis=-1)
        r = np.asarray(np.round(r), dtype=np.int32)
        return r


def write_char(charmap, x, y, char, overwrite=False):
    try:
        if overwrite or charmap[y][x] == ' ':
            charmap[y][x] = char
            return True
    except IndexError as e:
        m = f'Trying to write to charmap at {x}, {y}; max at {len(charmap[0])-1}, {len(charmap)-1}.'
        logger.warning(m)
        raise IndexError(m)
    return False

def wrap_tags(s, tags):
    for tag in tags:
        s = wrap_tag(s, tag)
    return s

def wrap_tag(s, tag):
    return f'<{tag}>{s}</{tag}>'

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
