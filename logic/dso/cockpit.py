from loguru import logger
import numpy as np
from functools import partial

from usr.config import CONFIG_DATA
from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic._3d.camera import Camera
from logic._3d.charmap import CharMap



class Cockpit:
    def __init__(self, ship, controller=None):
        self.ship = ship
        self.camera = Camera()
        self.show_labels = CONFIG_DATA['SHOW_LABELS']
        self.camera_following = None
        self.camera_tracking = None
        self._last_charmap_state = bytes(1)
        self._last_charmap = ''
        if controller:
            self.register_commands(controller)

    @property
    def universe(self):
        return self.ship.universe

    def register_commands(self, controller):
        # Ship controls
        d = {
            'cockpit.follow': self.follow,
            'cockpit.track': self.track,
            'cockpit.look': self.look,
            'cockpit.snaplook': self.snaplook,
            'cockpit.pro': self.look_prograde,
            'cockpit.retro': self.look_retrograde,
            'cockpit.labels': self.toggle_labels,
        }
        for command, callback in d.items():
            controller.register_command(command, callback)
        # Camera controls
        # We build seperate dicts so that camera commands don't overwrite ours
        d = {f'cockpit.{k}': v for k, v in self.camera.commands.items()}
        for command, callback in d.items():
            controller.register_command(command, callback)

    def follow(self, index=None):
        def get_pos(index):
            return self.universe.positions[index]
        if index is None:
            index = self.ship.oid
        self.camera.follow(partial(get_pos, index) if index is not None else None)

    def track(self, index=None):
        def get_pos(index):
            return self.universe.positions[index]
        self.camera.track(partial(get_pos, index) if index is not None else None)

    def look(self, index, ms=None, smooth=None):
        if ms is None:
            ms = CONFIG_DATA['CAMERA_SMOOTH_TIME']
        if smooth is None:
            smooth = CONFIG_DATA['CAMERA_SMOOTH_CURVE']
        self.camera.swivel_to_point(self.universe.ds_objects[index].position, ms, smooth)

    def snaplook(self, index):
        self.camera.look_at_point(self.universe.positions[index])

    def look_prograde(self):
        self.camera.look_at_point(self.ship.velocity * 10 **10)

    def look_retrograde(self):
        self.camera.look_at_point(-self.ship.velocity * 10 **10)

    def toggle_labels(self):
        self.show_labels = (self.show_labels + 1) % 4
        logger.info(f'Showing labels: {self.show_labels}')

    # Display
    def draw_charmap(self, size):
        if size[0] < CharMap.MINIMUM_SIZE or size[1] < CharMap.MINIMUM_SIZE:
            return 'TooSmall'
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
            return self._last_charmap
        self._last_charmap = self.draw_charmap(size=size)
        self._last_charmap_state = current_state
        return self._last_charmap

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
