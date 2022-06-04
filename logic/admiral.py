
from loguru import logger
import math
import random
import numpy as np
from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.dso.ship import Ship


PREFIXES = ['XSS', 'KRS', 'ISS', 'JTS', 'VSS']
ADMIRAL_POLL_INTERVAL = 1000


class Admiral:
    def __init__(self, universe, fid, name):
        self.universe = universe
        self.fid = fid
        self.name = name
        self.ship_prefix = random.choice(PREFIXES)
        self.my_ships = []

    def setup(self):
        name = f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}'
        new_oid = self.universe.add_object(Ship, name=name)
        self.my_ships.append(new_oid)

    def __repr__(self):
        return f'<Admiral {self.name} FID #{self.fid}>'

    @property
    def ship_oid(self):
        return self.my_ships[0]

    @property
    def my_ship(self):
        return self.universe.ds_objects[self.ship_oid]


class Player(Admiral):
    def setup(self):
        assert self.fid == 0
        name = f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}'
        controller = self.universe.controller
        new_oid = self.universe.add_object(Ship, name=name, controller=controller)
        self.my_ships.append(new_oid)


class Agent(Admiral):
    def setup(self, *a, **k):
        super().setup(*a, **k)
        self.universe.add_event(tick=self.universe.tick+1, callback=self.new_order)

    def get_new_destination(self):
        oid = random.randint(0, self.universe.object_count-1)
        while isinstance(self.universe.ds_objects[oid], Ship):
            oid = random.randint(0, self.universe.object_count-1)
        return oid

    def new_order(self):
        dest_oid = self.get_new_destination()
        speed = (1 + 9 * random.random())**random.randint(2, 4)
        dock_time = random.randint(2000, 4000)
        plan = self.my_ship.fly_to(dest_oid, cruise_speed=speed)
        next_order = plan.arrival + dock_time
        self.universe.add_event(tick=next_order, callback=self.new_order)
