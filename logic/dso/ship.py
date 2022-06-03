from loguru import logger
import math
import numpy as np
from collections import defaultdict, namedtuple

from logic.dso.cockpit import Cockpit
from logic.dso.dso import DeepSpaceObject


class Ship(DeepSpaceObject):
    def __init__(self):
        self.thrust = 1

    def setup(self, universe, oid, name, color=1, controller=None):
        super().setup(universe, oid, name, color)
        self.cockpit = Cockpit(ship=self, controller=controller)
        self.cockpit.follow(self.oid)
        self.stats = defaultdict(lambda: 0)
        if controller:
            self.register_commands(controller)

    def register_commands(self, controller):
        d = {
            'ship.fly': self.fly_to,
            'ship.burn': self.engine_burn,
            'ship.break': self.engine_break_burn,
            'ship.cut': self.engine_cut_burn,
        }
        for command, callback in d.items():
            controller.register_command(command, callback)

    def engine_burn(self, vector=None, throttle=1):
        if vector is None:
            self.cockpit.camera.update()
            vector = self.cockpit.camera.current_axes[0]
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (3, )
        mag = np.linalg.norm(vector)
        if mag == 0:
            m = f'{self} trying to engine burn without direction: {vector}'
            logger.warning(m)
        vector *= self.thrust * throttle / mag
        self.universe.engine.get_derivative_second('position')[self.oid] += vector

    def engine_break_burn(self):
        self.engine_burn(-self.universe.velocities[self.oid])

    def engine_cut_burn(self):
        self.universe.engine.get_derivative_second('position')[self.oid] = 0

    def fly_to(self, oid, cruise_speed):
        target = self.universe.ds_objects[oid]
        travel_vector = target.position - self.position
        travel_dist = np.linalg.norm(travel_vector)
        plan = self._simple_flight_plan(
            travel_dist=travel_dist,
            cruise_speed=cruise_speed,
            thrust=self.thrust,
            tick_offset=self.universe.tick,
        )
        # Cruise burn, cruise cutoff, break burn, break cutoff
        self.engine_burn(travel_vector)
        self.universe.add_event(tick=plan.cutoff, callback=self.engine_cut_burn)
        self.universe.add_event(tick=plan.break_burn, callback=self.engine_break_burn)
        self.universe.add_event(tick=plan.arrival, callback=self.engine_cut_burn)
        return plan

    @staticmethod
    def _simple_flight_plan(travel_dist, cruise_speed, thrust, tick_offset=0):
        burn_time = round(cruise_speed / thrust)
        burn_distance = burn_time * (burn_time + 1) // 2 * thrust
        while burn_distance >= travel_dist / 2:
            cruise_speed *= 0.95
            burn_time = round(cruise_speed / thrust)
            burn_distance = burn_time * (burn_time + 1) // 2 * thrust
        cruise_dist = travel_dist - (burn_distance * 2)
        cruise_time = round(cruise_dist / cruise_speed)
        total = burn_time * 2 + cruise_time
        cutoff = tick_offset + burn_time
        break_burn = cutoff + cruise_time
        arrival = break_burn + burn_time
        assert arrival == tick_offset + total
        fp = FlightPlan(cutoff, break_burn, arrival, total)
        return fp

    def __repr__(self):
        return f'<Ship #{self.oid} {self.name}>'


FlightPlan = namedtuple('FlightPlan', ['cutoff', 'break_burn', 'arrival', 'total'])
