from loguru import logger
import numpy as np

from logic.quaternion import unit_vectors
from gui import format_latlong, format_vector
from usr.config import ASPECT_RATIO, CROSSHAIR_COLOR


class CharMap:
    MINIMUM_SIZE = 3

    def __init__(self, camera, size, show_bar=True):
        self.camera = camera
        self.width, self.height = size
        self.show_bar = show_bar
        if self.show_bar:
            self.height -= 1
        if self.width < self.MINIMUM_SIZE or self.height < self.MINIMUM_SIZE:
            raise ValueError(f'CharMap size too small: {size} (minimum: {MINIMUM_SIZE}, {MINIMUM_SIZE})')
        self.size = self.width, self.height
        self.center = self.width // 2, self.height // 2
        self.charmap = [[' '] * self.width for _ in range(self.height)]

    def draw(self):
        map_str = '\n'.join(''.join(_) for _ in self.charmap)
        if self.show_bar:
            map_str = f'{map_str}\n{self.get_bar()}'
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

    def add_projection_axes(self):
        coords = unit_vectors()
        labels = ['X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-']
        pix_pos = self.get_projected_pixels(coords)
        for i, x, y in pix_pos:
            self.write_char(x, y, '╬', 'bold')
            self.write_label(x, y, labels[i])

    def add_crosshair(self):
        cx, cy = self.center
        scoords = (cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)  # 2 vertical, 2 horizontal
        dcoords = (cx+1, cy+1), (cx-1, cy-1), (cx-1, cy+1), (cx+1, cy-1)  # 2 left diag, 2 right diag
        straight = sum(self.check_empty(*c) for c in scoords)
        diagonal = sum(self.check_empty(*c) for c in dcoords)
        if diagonal >= straight:
            diag_chars = '\\\\//'
            for i, (cx, cy) in enumerate(dcoords):
                self.write_char(cx, cy, diag_chars[i], CROSSHAIR_COLOR)
        else:
            straight_chars = '││──'
            for i, (cx, cy) in enumerate(scoords):
                self.write_char(cx, cy, straight_chars[i], CROSSHAIR_COLOR)

    def get_projected_pixels(self, points):
        # Convert 3d position to mercator projection (latitude, longitude)
        ll_coords = self.camera.get_projected_coords(points)
        # Stretch to aspect ratio and zoom to get pixel coordinates
        pix = ll_coords * [1, ASPECT_RATIO] * self.camera.zoom
        # Offset such that pixel 0, 0 is at the center
        pix += self.center
        # Reverse vertically such that higher latitudes are higher in the map
        pix[:, 1] = self.height - pix[:, 1]
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

    def write_label(self, x, y, name):
        x += 3
        normal = self.count_empty_spaces(x, y)
        if normal >= len(name):
            self.insert_label(x, y, name)
            return
        below = self.count_empty_spaces(x, y+1)
        if below >= len(name):
            self.insert_label(x, y+1, name)
            return
        above = self.count_empty_spaces(x, y-1)
        if above >= len(name):
            self.insert_label(x, y-1, name)
            return
        options = [above, normal, below]
        idy = np.argmax(np.asarray(options)) - 1
        if options[idy] > 3:
            self.insert_label(x, y+idy, name)

    def insert_label(self, x, y, name):
        for i, char in enumerate(name):
            if x+i+1 >= self.width or self.charmap[y][x+i+1] != ' ':
                break
            self.charmap[y][x+i] = char if char != ' ' else '<whitespace> </whitespace>'

    def count_empty_spaces(self, x, y):
        if y >= self.height:
            return -1
        total = 0
        while x < self.width and self.check_empty(x, y):
            x += 1
            total += 1
        return total

    def check_empty(self, x, y):
        return self.charmap[y][x] == ' '

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
