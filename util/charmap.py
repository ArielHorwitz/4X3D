from loguru import logger
import numpy as np

from util import format_latlong, format_vector, EPSILON
from util._3d import AXES_VECTORS
from util.config import CONFIG_DATA


WHITESPACE = '<whitespace> </whitespace>'


class TooSmallError(Exception):
    pass


class CharMap:
    """Character Map

    This class uses a camera to project points in 3D space to a 2D map of
    characters (multiline string), essentially acting as a window to a Camera
    object.

    To use, initialize the character map with POV camera and window size.
    Add elements to the character map (such as objects or crosshairs).
    Finally, call the draw() method to get a string ready for printing.

    A TooSmallError will be raised if the requested size is too small.
    """
    def __init__(self, camera, size, show_bar=True, minimum_label_size=4):
        self.camera = camera
        self.width, self.height = size
        self.show_bar = show_bar
        self.size = self.width, self.height
        # Things get wonky if there isn't enough room for a crosshair (3x3)
        # Also consider that the bar will take up one row
        self.minimum_size = 3, 3 + self.show_bar
        if self.width < self.minimum_size[0] or self.height < self.minimum_size[1]:
            raise TooSmallError(f'CharMap too small:\nRequested {self.size} minimum {self.minimum_size}')
        if self.show_bar:
            self.height -= 1
        self.minimum_label_size = minimum_label_size
        self.center = self.width // 2, self.height // 2
        self.charmap = [[' '] * self.width for _ in range(self.height)]
        self.camera.update()

    # Drawing
    def draw(self):
        map_str = '\n'.join(''.join(_) for _ in self.charmap)
        if self.show_bar:
            map_str = f'<map>{map_str}</map>\n<bar>{self.__get_bar()}</bar>'
        return map_str

    def __get_bar(self):
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

    # Map elements
    def add_objects(self, points, icon, tag, labels=None):
        """Add a list of objects to the character map.

        Similar to add_object(), however icon, tag, and labels are given as
        functions that take an index (of the point from points) and return its
        respective icon, tag, and labels. We do this since any given point
        may or may not end up in the CharMap, and therefore only need a subset
        of icons, tags, and labels (depending on each point being in the
        camera's POV).

        See add_object() for details on what tags and labels represent.

        points  -- a list of 3D points
        icon    -- a function that takes an index (of point) and returns the
                    character to draw for it
        tag     -- a function that takes and index (of point) and returns a
                    tag for the icon
        labels  -- a function that takes an index (of point) and returns a
                    sequence of labels to write for it
        """
        pix_pos = self._get_projected_pixels(points)
        for i, x, y in pix_pos:
            self.write_char(x, y, icon(i), tag(i))
        if labels:
            for i, x, y in pix_pos:
                for label in labels(i):
                    self.write_label(x+1, y, *label)

    def add_object(self, point, icon, tag=None, labels=None):
        """Add an object to the character map.
        A tag is an HTML tag (usually the color name) or None for plain text.
        A label is a tuple of 2 strings: text and aforementioned tag.

        points  -- a 3D point
        icon    -- the character to draw at that point
        tag     -- a tag for the icon
        labels  -- a sequence of labels
        """
        pix_pos = self._get_projected_pixel(point)
        if pix_pos is None:
            return
        x, y = pix_pos
        self.write_char(x, y, icon, tag)
        if labels:
            for label in labels:
                self.write_label(x+1, y, *label)
        return True

    def add_projection_axes(self):
        labels = ['X+', 'X-', 'Y+', 'Y-', 'Z+', 'Z-']
        pix_pos = self._get_projected_pixels(AXES_VECTORS)
        for i, x, y in pix_pos:
            self.write_char(x, y, '╬', 'bold')
            self.write_label(x, y, labels[i])

    def add_crosshair(self, point=None, color=CONFIG_DATA['CROSSHAIR_COLOR']):
        if point is None:
            cx, cy = self.center
        else:
            pix_pos = self._get_projected_pixel(point)
            if pix_pos is None:
                return
            cx, cy = pix_pos
        scoords = (cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)  # 2 vertical, 2 horizontal
        dcoords = (cx+1, cy+1), (cx-1, cy-1), (cx-1, cy+1), (cx+1, cy-1)  # 2 left diag, 2 right diag
        straight = sum(self._check_empty(*c) for c in scoords)
        diagonal = sum(self._check_empty(*c) for c in dcoords)
        if diagonal >= straight:
            diag_chars = '\\\\//'
            for i, (cx, cy) in enumerate(dcoords):
                self.write_char(cx, cy, diag_chars[i], color, ignore_fail=True)
        else:
            straight_chars = '││──'
            for i, (cx, cy) in enumerate(scoords):
                self.write_char(cx, cy, straight_chars[i], color, ignore_fail=True)

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

    # Writing to map
    def write_char(self, x, y, char, tag=None, overwrite=False, ignore_fail=False):
        assert len(char) == 1
        if tag:
            char = f'<{tag}>{char}</{tag}>'
        try:
            if overwrite or self._check_empty(x, y):
                self.charmap[y][x] = char
                return True
        except IndexError as e:
            if not ignore_fail:
                m = f'Trying to write to charmap at {x}, {y}; max at {len(charmap[0])-1}, {len(charmap)-1}.'
                logger.warning(m)
                raise IndexError(m)
        return False

    def write_label(self, x, y, label, tag=None, pad_right=True, allow_offset=True):
        if pad_right:
            label = f'{label} '
        label_size = len(label)
        normal = self._count_empty_spaces(x, y, label_size)
        label_fits_normal = normal >= label_size
        if label_fits_normal:
            self._insert_label(x, y, label, tag)
            return
        if not allow_offset:
            if normal >= self.minimum_label_size:
                self._insert_label(x, y, label, tag)
            return
        # Check if label fits below
        below = self._count_empty_spaces(x, y+1, label_size)
        if below >= label_size:
            self._insert_label(x, y+1, label, tag)
            return
        # Check if label fits above
        above = self._count_empty_spaces(x, y-1, label_size)
        if above >= label_size:
            self._insert_label(x, y-1, label, tag)
            return
        # Use location with the most room for label
        options = np.asarray([above, normal, below])
        idy = np.argmax(options) - 1
        if options[idy] >= self.minimum_label_size:
            self._insert_label(x, y+idy, label, tag)

    def _insert_label(self, x, y, label, tag=None):
        for i, char in enumerate(label):
            # Check if next pixel is
            if x+i+1 >= self.width or self.charmap[y][x+i+1] != ' ':
                if i > 0 and tag is not None:
                    self.charmap[y][x+i-1] = f'{self.charmap[y][x+i-1]}</{tag}>'
                break
            if i == 0 and tag:
                char = f'<{tag}>{char}'
            self.charmap[y][x+i] = char if char != ' ' else WHITESPACE
        else:
            if tag is not None:
                self.charmap[y][x+i] = f'{self.charmap[y][x+i]}</{tag}>'

    def _count_empty_spaces(self, x, y, max_chars=float('inf')):
        total = 0
        while self._check_empty(x, y) and total < max_chars:
            total += 1
            x += 1
        return total

    def _check_empty(self, x, y):
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.charmap[y][x] == ' '
        return False

    # Projections
    def _get_projected_pixels(self, points):
        """Convert 3D positions to mercator projection (latitude, longitude)"""
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

    def _get_projected_pixel(self, point):
        """Convert a single 3D position to mercator projection (latitude, longitude)"""
        pix_pos = self._get_projected_pixels(np.asarray([point]))
        if len(pix_pos) == 0:
            return None
        return pix_pos[0, 1:]
