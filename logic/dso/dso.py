from gui import OBJECT_COLORS


class DeepSpaceObject:
    OBJECT_COLORS = {
        'smbh': 'grey',
        'star': 'white',
        'rock': 'brown',
        'ship': 'green',
        'escort': 'green',
        'tug': 'yellow',
        'port': 'blue',
        'fighter': 'red',
        '': 'magenta',
        '': 'pink',
        '': 'orange',
        '': 'cyan',
        '': 'purple',
    }
    type_name = 'Object'
    icon = '?'

    def __init__(self, universe, oid):
        self.universe = universe
        self.oid = oid

    def setup(self, name):
        self.color = self.OBJECT_COLORS[self.type_name.lower()]
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
    type_name = 'SMBH'
    icon = '■'

class Star(DeepSpaceObject):
    type_name = 'star'
    icon = '¤'

class Rock(DeepSpaceObject):
    type_name = 'rock'
    icon = '•'
