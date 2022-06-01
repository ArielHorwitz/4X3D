from collections import defaultdict
from logic.ship.cockpit import Cockpit


class Ship:
    def __init__(self, universe, oid, name, controller=None):
        self.universe = universe
        self.oid = oid
        self.name = name
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

    def engine_burn(self, dv):
        vector = self.cockpit.camera.current_axes[0] * dv
        self.universe.velocities[self.oid] += vector

    def engine_break_burn(self):
        self.universe.velocities[self.oid] = 0
