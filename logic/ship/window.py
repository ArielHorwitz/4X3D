from loguru import logger
import numpy as np
from functools import partial

from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.camera import Camera



class ShipWindow:
    def __init__(self, universe):
        self.universe = universe
        self.camera = Camera()
        self.show_labels = 2
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
