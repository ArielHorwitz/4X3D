
from loguru import logger
import math
import random
import numpy as np
from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.dso.ship import Ship, Tug, Fighter, Escort, Port
from logic.dso.celestial import CelestialObject


PREFIXES = ['XSS', 'KRS', 'ISS', 'JTS', 'VSS']
ADMIRAL_POLL_INTERVAL = 1000
SHIP_CLASSES = [Tug, Fighter, Escort, Port]
SHIP_WEIGHTS = [10, 2, 1, 1]


class Admiral:
    def __init__(self, universe, fid, name):
        self.universe = universe
        self.fid = fid
        self.name = name
        self.ship_prefix = random.choice(PREFIXES)
        self.my_ships = []

    def setup(self):
        pass

    def __repr__(self):
        return f'<Admiral {self.name} FID #{self.fid}>'

    @property
    def my_ship(self):
        return self.my_ships[0]


class Player(Admiral):
    def setup(self):
        assert self.fid == 0
        name = f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}'
        controller = self.universe.controller
        my_ship = self.universe.add_object(Escort, name=name, controller=controller)
        self.my_ships.append(my_ship)


class Agent(Admiral):
    def setup(self, *a, **k):
        # Make ship
        ship_cls = random.choices(SHIP_CLASSES, weights=SHIP_WEIGHTS)[0]
        name = f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}'
        my_ship = self.universe.add_object(ship_cls, name=name)
        self.my_ships.append(my_ship)
        self.universe.add_event(0, tick=self.universe.tick+1, callback=self.new_order)

    def get_new_destination(self):
        oid = random.randint(0, self.universe.object_count-1)
        while not isinstance(self.universe.ds_objects[oid], CelestialObject):
            oid = random.randint(0, self.universe.object_count-1)
        return oid

    def new_order(self, uid):
        if self.my_ship.thrust == 0:
            logger.debug(f'{self} ending orders since my ship has no thrust: {self.my_ship}')
            return
        dest_oid = self.get_new_destination()
        speed = (1 + 9 * random.random())*10**random.randint(2, 3)
        dock_time = random.randint(2000, 4000)
        plan = self.my_ship.fly_to(dest_oid, cruise_speed=speed)
        next_order = plan.arrival + dock_time
        self.universe.add_event(0, tick=next_order, callback=self.new_order)
