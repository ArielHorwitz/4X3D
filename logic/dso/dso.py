from gui import OBJECT_COLORS


class DeepSpaceObject:
    def __init__(self):
        pass

    def setup(self, universe, oid, name, color=0):
        self.universe = universe
        self.oid = oid
        self.name = name
        self.color = color
        assert 0 <= color <= len(OBJECT_COLORS)

    @property
    def position(self):
        return self.universe.positions[self.oid]

    @property
    def velocity(self):
        return self.universe.velocities[self.oid]

    def __repr__(self):
        return f'<DeepSpaceObject #{self.oid} {self.name}>'
