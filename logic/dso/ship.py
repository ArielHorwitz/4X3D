from collections import defaultdict
from logic.dso.cockpit import Cockpit
from logic.dso.dso import DeepSpaceObject


class Ship(DeepSpaceObject):
    def __init__(self):
        pass

    def setup(self, universe, oid, name, color=1, controller=None):
        super().setup(universe, oid, name, color)
        self.cockpit = Cockpit(ship=self, controller=controller)
        self.cockpit.follow(self.oid)
        self.stats = defaultdict(lambda: 0)
        if controller:
            self.register_commands(controller)

    def register_commands(self, controller):
        d = {
            'ship.burn': self.engine_burn,
            'ship.break': self.engine_break_burn,
        }
        for command, callback in d.items():
            controller.register_command(command, callback)

    def fly_at(self, point, dv):
        self.cockpit.camera.set_position(self.position)
        self.cockpit.camera.look_at_vector(point)
        self.engine_burn(dv)

    def engine_burn(self, dv, vector=None):
        if vector is None:
            self.cockpit.camera.update()
            vector = self.cockpit.camera.current_axes[0] * dv
        self.universe.velocities[self.oid] += vector

    def engine_break_burn(self):
        self.universe.velocities[self.oid] = 0

    def __repr__(self):
        return f'<Ship #{self.oid} {self.name}>'
