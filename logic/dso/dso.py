from loguru import logger
import numpy as np


class DeepSpaceObject:
    type_name = 'Object'
    icon = '?'
    color = 'grey'

    def __init__(self, universe, oid):
        self.universe = universe
        self.oid = oid

    def setup(self, name):
        self.name = name
        self.label = f'{self.icon}{self.oid} {self.name}'

    @property
    def position(self):
        return self.universe.engine.get_stat('position', self.oid)

    @property
    def velocity(self):
        return self.universe.engine.get_derivative('position', self.oid)

    @property
    def acceleration(self):
        return self.universe.engine.get_derivative_second('position', self.oid)

    def __repr__(self):
        return f'<DeepSpaceObject {self.label}>'

    def offset_from_parent(self, parent, offset):
        offset_coords = np.random.normal(0, offset, size=3)
        self.position[:] = parent.position + offset_coords
