from gui import OBJECT_COLORS


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

    @property
    def prograde(self):
        return self.velocity * 10 ** 10

    @property
    def retrograde(self):
        return -self.velocity * 10 ** 10

    def __repr__(self):
        return f'<DeepSpaceObject {self.label}>'


class SMBH(DeepSpaceObject):
    type_name = 'SMBH'
    icon = '■'
    color = 'grey'

class Star(DeepSpaceObject):
    type_name = 'star'
    icon = '¤'
    color = 'white'

class Rock(DeepSpaceObject):
    type_name = 'rock'
    icon = '•'
    color = 'brown'
