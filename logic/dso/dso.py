from gui import OBJECT_COLORS


class DeepSpaceObject:
    OBJECT_COLORS = {
        'smbh': 'grey',
        'star': 'white',
        'rock': 'brown',
        'ship': 'green',
        '': 'red',
        '': 'pink',
        '': 'yellow',
        '': 'orange',
        '': 'blue',
        '': 'cyan',
        '': 'magenta',
        '': 'purple',
    }
    TYPE_NAME = 'Object'

    def __init__(self, universe, oid):
        self.universe = universe
        self.oid = oid

    def setup(self, name):
        self.color = self.OBJECT_COLORS[self.TYPE_NAME.lower()]
        self.name = name
        self.label = f'¤{self.oid} {self.name}'

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


class SMBH(DeepSpaceObject):
    TYPE_NAME = 'SMBH'

class Star(DeepSpaceObject):
    TYPE_NAME = 'star'

class Rock(DeepSpaceObject):
    TYPE_NAME = 'rock'
