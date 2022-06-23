
from loguru import logger
import math
import random
import numpy as np
from util import OBJECT_COLORS, CELESTIAL_NAMES
from util.argparse import arg_validation
from logic.dso.ship import Ship, Tug, Fighter, Escort, Port
from logic.dso.celestial import CelestialObject


PREFIXES = ['XSS', 'KRS', 'ISS', 'JTS', 'VSS']
ADMIRAL_POLL_INTERVAL = 1000
SHIP_CLASSES = [Tug, Fighter, Escort, Port]
SHIP_WEIGHTS = [10, 2, 1, 1]


class Admiral:
    flagship_name = 'Flagship'

    def __init__(self, universe, fid, name):
        self.universe = universe
        self.fid = fid
        self.name = name
        self.ship_prefix = random.choice(PREFIXES)
        self.fleet = []
        self.fleet_oids = set()

    def setup(self):
        self.add_flagship()

    def add_flagship(self):
        ship_name = f'{self.ship_prefix}. {self.flagship_name}'
        self.my_ship = self.universe.add_object(Escort, fid=self.fid, name=ship_name)

    def add_ship(self, cls, name, parent):
        ship_name = f'{self.ship_prefix}. {name}'
        new_ship = self.universe.add_object(cls, fid=self.fid, name=ship_name, parent=parent)
        self.fleet.append(new_ship)
        self.fleet_oids.add(new_ship.oid)

    def __repr__(self):
        return f'<Admiral {self.name} FID #{self.fid}>'

    @property
    def fleet_str(self):
        return '\n'.join(f'{s.label}' for s in self.fleet)

    @property
    def position(self):
        return self.my_ship.position


class Player(Admiral):
    flagship_name = 'Devship'
    def setup(self, controller):
        assert self.fid == 0
        super().setup()
        self.register_commands(controller)
        self.make_fleet(20)

    def register_commands(self, controller):
        d = {
            ('order.fly', self.order_fly),
            ('order.patrol', self.order_patrol),
            *[(f'ship.{n}', *a) for n, *a in self.my_ship.commands],
            *[(f'cockpit.{n}', *a) for n, *a in self.my_ship.cockpit.commands],
        }
        for command in d:
            controller.register_command(*command)

    def get_charmap(self, size):
        return self.my_ship.cockpit.get_charmap(size)

    def make_fleet(self, count=20):
        for i in range(count):
            batch_idx = i % 10
            cls = Tug
            if batch_idx == 0:
                cls = Port
            elif batch_idx < 3:
                cls = Fighter
            ship_name = random.choice(CELESTIAL_NAMES)
            self.add_ship(cls, name=ship_name, parent=self.my_ship)

    def order_patrol(self, oid, target_oids, auto_look=False):
        """ArgSpec
        Order a ship to patrol between celestial objects
        ___
        OID Ship ID to order
        *TARGET_OIDS Objects to patrol between
        -+look AUTO_LOOK Automatically turn camera to look at target before flying
        """
        with arg_validation(f'Ordered ship must be in fleet, instead ordered ID: {oid}'):
            assert oid in self.fleet_oids
        for check_oid in target_oids:
            with arg_validation(f'Invalid target ID: {check_oid}'):
                assert self.universe.is_oid(check_oid)

        ship = self.universe.ds_objects[oid]
        ship.command_order_patrol(target_oids, auto_look)

    def order_fly(self, oid, target_oid, cruise_speed=10**10):
        """ArgSpec
        Order a ship to fly to a deep space object
        ___
        OID Ship ID to order
        TARGET_OID Target ID to fly to
        -+s CRUISE_SPEED Maximum cruising speed
        """
        with arg_validation(f'Ordered ship must be in fleet, instead ordered ID: {oid}'):
            assert oid in self.fleet_oids
        with arg_validation(f'Invalid target ID: {target_oid}'):
            assert self.universe.is_oid(target_oid)
        with arg_validation(f'Cruise speed must be a positive number'):
            assert cruise_speed > 0

        ship = self.universe.ds_objects[oid]
        ship.fly_to(target_oid)


class Agent(Admiral):
    def setup(self, *a, **k):
        super().setup()
        self.universe.add_event(None, self.first_order, 'Start first order', 0)

    def get_new_destination(self):
        oid = random.randint(0, self.universe.object_count-1)
        while not isinstance(self.universe.ds_objects[oid], CelestialObject):
            oid = random.randint(0, self.universe.object_count-1)
        return oid

    def first_order(self, uid):
        oids = random.choices(np.flatnonzero(self.universe.ds_celestials), k=5)
        self.my_ship.order_patrol(oids)
