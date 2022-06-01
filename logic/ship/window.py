from loguru import logger
import numpy as np
from functools import partial

from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.camera import Camera



class ShipWindow:
    def __init__(self, universe, controller):
        self.universe = universe
        self.camera = Camera()
        self.show_labels = 2
        self.camera_following = None
        self.camera_tracking = None
        self.register_commands(controller)

    def register_commands(self, controller):
        # Ship controls
        d = {
            'ship.follow': self.follow,
            'ship.track': self.track,
            'ship.look': self.look,
            'ship.labels': self.toggle_labels,
        }
        for command, callback in d.items():
            controller.register_command(command, callback)
        # Camera controls
        # We build seperate dicts so that camera commands don't overwrite ours
        d = {f'ship.{k}': v for k, v in self.camera.commands.items()}
        for command, callback in d.items():
            controller.register_command(command, callback)

    def follow(self, index=None):
        def get_pos(index):
            return self.universe.positions[index]
        self.camera.follow(partial(get_pos, index) if index is not None else None)

    def track(self, index=None):
        def get_pos(index):
            return self.universe.positions[index]
        self.camera.track(partial(get_pos, index) if index is not None else None)

    def look(self, index):
        self.camera.look_at_vector(self.universe.positions[index])

    def toggle_labels(self):
        self.show_labels = (self.show_labels + 1) % 4
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
        return [OBJECT_COLORS[i % len(OBJECT_COLORS)] for i in range(self.universe.entity_count)]

    def get_labels(self):
        labels = []
        for i, pos in enumerate(self.universe.positions):
            lbl = ''
            if self.show_labels:
                lbl = CELESTIAL_NAMES[i]
            if self.show_labels > 1:
                lbl = f'#{i}.{lbl}'
            if self.show_labels > 2:
                dist = np.linalg.norm(self.camera.pos - pos)
                lbl = f'{lbl} ({dist:.1f})'
            labels.append(lbl)
        return labels
