from loguru import logger
import numpy as np

from util import format_latlong, format_vector, EPSILON
from util._3d import AXES_VECTORS
from util.config import CONFIG_DATA


WHITESPACE = '<whitespace> </whitespace>'


class CharMap:
    MINIMUM_SIZE = 3

    def __init__(self, camera, size, show_bar=True, minimum_label_size=4):
        self.camera = camera
        self.width, self.height = size
        self.minimum_label_size = minimum_label_size
        self.show_bar = show_bar
        if self.show_bar:
            self.height -= 1
        self.size = self.width, self.height
        if self.width < self.MINIMUM_SIZE or self.height < self.MINIMUM_SIZE:
            raise ValueError(f'CharMap size too small: {self.size} (minimum: {self.MINIMUM_SIZE})')
        self.center = self.width // 2, self.height // 2
        self.charmap = [[' '] * self.width for _ in range(self.height)]
        self.camera.update()

    def draw(self):
        map_str = '\n'.join(''.join(_) for _ in self.charmap)
        if self.show_bar:
            map_str = f'<map>{map_str}</map>\n<bar>{self.get_bar()}</bar>'
        return map_str

    def get_bar(self):
        following = '<grey>FLW</grey>' if self.camera.following is None else '<h2>FLW</h2>'
        tracking = '<grey>TRK</grey>' if self.camera.tracking is None else '<h2>TRK</h2>'
        camera_str = f'{following} {tracking}'
        return ' | '.join([
            f'<code>{camera_str}</code>',
            f'<code>{format_latlong(self.camera.lat_long)}</code>',
            f'<code>x{self.camera.zoom:.2f}</code>',
            f'<code>[{format_vector(self.camera.pos)}]</code>',
            f'<code>{self.width}×{self.height}</code>',
        ])

    def add_objects(self, points, icon, tag, label=None):
        pix_pos = self.get_projected_pixels(points)
        labels = []
        for i, x, y in pix_pos:
            self.write_char(x, y, icon(i), tag(i))
            if label:
                labels.append((i, x, y))
        for i, x, y in labels:
            self.write_label(x, y, label(i))

    def add_object(self, point, icon, tag=None, label=None):
        pix_pos = self.get_projected_pixel(point)
        if pix_pos is None:
            return
        x, y = pix_pos
        self.write_char(x, y, icon, tag)
        if label:
            self.write_label(x, y, label)
        return True

    def add_projection_axes(self):
        labels = ['X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-']
        pix_pos = self.get_projected_pixels(AXES_VECTORS)
        for i, x, y in pix_pos:
            self.write_char(x, y, '╬', 'bold')
            self.write_label(x, y, labels[i])

    def add_crosshair(self, point=None, color=CONFIG_DATA['CROSSHAIR_COLOR']):
        if point is None:
            cx, cy = self.center
        else:
            pix_pos = self.get_projected_pixel(point)
            if pix_pos is None:
                return
            cx, cy = pix_pos
        scoords = (cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)  # 2 vertical, 2 horizontal
        dcoords = (cx+1, cy+1), (cx-1, cy-1), (cx-1, cy+1), (cx+1, cy-1)  # 2 left diag, 2 right diag
        straight = sum(self.check_empty(*c) for c in scoords)
        diagonal = sum(self.check_empty(*c) for c in dcoords)
        if diagonal >= straight:
            diag_chars = '\\\\//'
            for i, (cx, cy) in enumerate(dcoords):
                self.write_char(cx, cy, diag_chars[i], color)
        else:
            straight_chars = '││──'
            for i, (cx, cy) in enumerate(scoords):
                self.write_char(cx, cy, straight_chars[i], color)

    def add_prograde_retrograde(self, velocity, show_labels=False, show_speed=False):
        mag = np.linalg.norm(velocity)
        if mag < EPSILON:
            return
        velocity = velocity * 10**10
        pro_label = ret_label = None
        if show_labels:
            pro_label, ret_label = 'PROGRADE', 'RETROGRADE'
        if show_labels and show_speed:
            pro_label = f'PRO ({mag:.3f})'
            ret_label = f'RET ({mag:.3f})'
        self.add_object(velocity, '×', 'green', pro_label)
        self.add_crosshair(velocity, color='green')
        self.add_object(-velocity, '+', 'red', ret_label)
        self.add_crosshair(-velocity, color='red')

    def get_projected_pixels(self, points):
        # Convert 3d position to mercator projection (latitude, longitude)
        ll_coords = self.camera.get_projected_coords(points)
        # Stretch to aspect ratio and zoom to get pixel coordinates
        pix = ll_coords * [1, CONFIG_DATA['ASPECT_RATIO']] * self.camera.zoom
        # Reverse vertically such that position latitudes are up
        pix[:, 1] *= -1
        # Offset such that pixel 0, 0 is at the center
        pix += self.center
        # Filter coordinates off map
        above_botleft = (pix[:, 0] >= 0) & (pix[:, 1] >= 0)
        below_topright = (pix[:, 0] < self.width-1) & (pix[:, 1] < self.height-1)
        not_on_camera_pos = (points != self.camera.pos).sum(axis=-1) > 0
        valid = above_botleft & below_topright & not_on_camera_pos
        pix = pix[valid]
        # Add original indices (such that each point is now: index, x_pixel, y_pixel)
        r = np.concatenate((np.flatnonzero(valid)[:, None], pix), axis=-1)
        # Round to nearest pixel
        r = np.asarray(np.round(r), dtype=np.int32)
        return r

    def get_projected_pixel(self, point):
        pix_pos = self.get_projected_pixels(np.asarray([point]))
        if len(pix_pos) == 0:
            return None
        return pix_pos[0, 1:]

    def write_label(self, x, y, label):
        x += 1  # Offset label to the right of object
        label = f'{label} '  # Add small whitespace as padding
        label_size = len(label)
        normal = self.count_empty_spaces(x, y, label_size)
        if normal >= label_size:
            self.insert_label(x, y, label)
            return
        below = self.count_empty_spaces(x, y+1, label_size)
        if below >= label_size:
            self.insert_label(x, y+1, label)
            return
        above = self.count_empty_spaces(x, y-1, label_size)
        if above >= label_size:
            self.insert_label(x, y-1, label)
            return
        options = [above, normal, below]
        idy = np.argmax(np.asarray(options)) - 1
        if options[idy] > self.minimum_label_size:
            self.insert_label(x, y+idy, label)

    def insert_label(self, x, y, name):
        for i, char in enumerate(name):
            if x+i+1 >= self.width or self.charmap[y][x+i+1] != ' ':
                break
            self.charmap[y][x+i] = char if char != ' ' else WHITESPACE

    def count_empty_spaces(self, x, y, max_chars=float('inf')):
        if y >= self.height:
            return -1
        total = 0
        while x < self.width and total < max_chars and self.check_empty(x, y):
            x += 1
            total += 1
        return total

    def check_empty(self, x, y):
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.charmap[y][x] == ' '
        return False

    def write_char(self, x, y, char, tags=None, overwrite=False):
        assert len(char) == 1
        if tags:
            if isinstance(tags, str):
                char = f'<{tags}>{char}</{tags}>'
            else:
                char = self.wrap_tags(char, tags)
        try:
            if overwrite or self.check_empty(x, y):
                self.charmap[y][x] = char
                return True
        except IndexError as e:
            m = f'Trying to write to charmap at {x}, {y}; max at {len(charmap[0])-1}, {len(charmap)-1}.'
            logger.warning(m)
            raise IndexError(m)
        return False

    @staticmethod
    def wrap_tags(s, tags):
        for tag in tags:
            s = f'<{tag}>{s}</{tag}>'
        return s
