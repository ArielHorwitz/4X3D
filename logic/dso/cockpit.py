from loguru import logger
import numpy as np
from functools import partial

from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.camera import Camera



class Cockpit:
    def __init__(self, ship, controller=None):
        self.ship = ship
        self.camera = Camera()
        self.show_labels = 1
        self.camera_following = None
        self.camera_tracking = None
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

    def look(self, index):
        self.camera.look_at_vector(self.universe.positions[index])

    def toggle_labels(self):
        self.show_labels = (self.show_labels + 1) % 3
        logger.info(f'Showing labels: {self.show_labels}')

    # Display
    def get_charmap(self, size):
        labels = self.get_labels()
        tags = self.get_tags()
        charmap = self.camera.get_charmap(
            size=size,
            points=self.universe.positions,
            tags=tags,
            labels=labels,
        )
        return charmap

    def get_tags(self):
        return [OBJECT_COLORS[dso.color] for dso in self.universe.ds_objects]

    def get_labels(self):
        labels = []
        for oid, ob in enumerate(self.universe.ds_objects):
            lbl = ''
            if self.show_labels:
                lbl = ob.label
            if self.show_labels > 1:
                dist = np.linalg.norm(self.camera.pos - ob.position)
                lbl = f'{lbl} ({dist:.1f})'
            labels.append(lbl)
        return labels
