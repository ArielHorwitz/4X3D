from loguru import logger
import numpy as np
from functools import partial

from util.config import CONFIG_DATA
from util import OBJECT_COLORS, CELESTIAL_NAMES
from util.camera import Camera
from util.charmap import CharMap



class Cockpit:
    def __init__(self, ship):
        self.ship = ship
        self.camera = Camera()
        self.show_labels = CONFIG_DATA['SHOW_LABELS']
        self.camera_following = None
        self.camera_tracking = None
        self._last_charmap_state = bytes(1)

    @property
    def commands(self):
        cockpit_commands = [
            ('follow', self.follow),
            ('track', self.track),
            ('look', self.look),
            ('snaplook', self.snaplook),
            ('pro', self.look_prograde),
            ('retro', self.look_retrograde),
            ('labels', self.toggle_labels),
        ]
        return cockpit_commands + self.camera.commands

    @property
    def universe(self):
        return self.ship.universe

    def follow(self, index=None):
        """ArgSpec
        Follow a deep space object
        ___
        +INDEX Object ID
        """
        def get_pos(index):
            return self.universe.positions[index]
        if index is None:
            index = self.ship.oid
        self.camera.follow(partial(get_pos, index) if index is not None else None)

    def track(self, index=None):
        """ArgSpec
        Track a deep space object
        ___
        +INDEX Object ID
        """
        def get_pos(index):
            return self.universe.positions[index]
        self.camera.track(partial(get_pos, index) if index is not None else None)

    def look(self, index, ms=None, smooth=None):
        """ArgSpec
        Turn to look at a deep space object
        ___
        INDEX Object ID
        +MS How long to swivel for in ms
        -+s SMOOTH How smoothly to swivel between -1 and 1
        """
        if ms is None:
            ms = CONFIG_DATA['CAMERA_SMOOTH_TIME']
        if smooth is None:
            smooth = CONFIG_DATA['CAMERA_SMOOTH_CURVE']
        self.camera.swivel_to_point(self.universe.ds_objects[index].position, ms, smooth)

    def snaplook(self, index):
        """ArgSpec
        Instantly turn to look at a deep space object
        ___
        INDEX Object ID
        """
        self.camera.look_at_point(self.universe.positions[index])

    def look_prograde(self):
        """Turn to look at prograde vector"""
        self.camera.look_at_point(self.ship.velocity * 10 **10)

    def look_retrograde(self):
        """Turn to look at retrograde vector"""
        self.camera.look_at_point(-self.ship.velocity * 10 **10)

    def toggle_labels(self):
        """Toggle labels"""
        self.show_labels = (self.show_labels + 1) % 4
        logger.info(f'Showing labels: {self.show_labels}')

    # Display
    def draw_charmap(self, size):
        if size[0] < CharMap.MINIMUM_SIZE or size[1] < CharMap.MINIMUM_SIZE:
            return 'Window too small'
        charmap = CharMap(self.camera, size)
        points = self.universe.positions
        label_getter = self.get_label if self.show_labels else None
        charmap.add_objects(
            points=points,
            icon=self.get_icon,
            tag=self.get_tag,
            label=label_getter,
        )
        charmap.add_projection_axes()
        charmap.add_crosshair()
        charmap.add_prograde_retrograde(
            velocity=self.ship.velocity,
            show_labels=self.show_labels,
            show_speed=self.show_labels > 1,
        )
        return charmap.draw()

    def get_charmap(self, size):
        state = ''.join([
            str(self.universe.tick),
            str(size),
            str(self.show_labels),
            str(self.camera.state),
        ])
        current_state = bytes(state, encoding='utf-8')
        if self._last_charmap_state == current_state:
            return None
        self._last_charmap_state = current_state
        return self.draw_charmap(size=size)

    def get_icon(self, oid):
        return self.universe.ds_objects[oid].icon

    def get_tag(self, oid):
        return self.universe.ds_objects[oid].color

    def get_label(self, oid):
        ob = self.universe.ds_objects[oid]
        lbl = ''
        if self.show_labels == 1:
            lbl = f'{ob.oid}'
        elif self.show_labels >= 2:
            lbl = f'{ob.oid}.{ob.name}'
        if self.show_labels == 3:
            dist = np.linalg.norm(self.camera.pos - ob.position)
            lbl = f'{lbl} ({dist:.3e})'
        return lbl
