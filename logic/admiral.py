
from loguru import logger
import math
import random
import numpy as np
from gui import OBJECT_COLORS
from logic import CELESTIAL_NAMES
from logic.dso.ship import Ship


PREFIXES = ['XSS'] + ['KRS', 'ISS', 'JTS', 'VSS'] * 5
ADMIRAL_POLL_INTERVAL = 1000


class Admiral:
    def __init__(self, universe, fid, name):
        self.universe = universe
        self.fid = fid
        self.name = name
        self.ship_prefix = PREFIXES[self.fid]
        self.my_ships = []

    def setup(self):
        my_ship = Ship()
        new_oid = self.universe.add_object(my_ship)
        my_ship.setup(
            universe=self.universe, oid=new_oid,
            name=f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}',
            color=random.randint(0, len(OBJECT_COLORS)-1),
        )
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
        controller = self.universe.controller
        my_ship = Ship()
        new_oid = self.universe.add_object(my_ship)
        my_ship.setup(
            universe=self.universe, oid=new_oid,
            name=f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}',
            color=random.randint(0, len(OBJECT_COLORS)-1),
            controller=controller,
        )
        self.my_ships.append(new_oid)


class Agent(Admiral):
    def setup(self, *a, **k):
        super().setup(*a, **k)
        self.universe.events.add(tick=self.universe.tick+1, callback=self.new_order)

    def get_new_destination(self):
        oid = random.randint(0, self.universe.object_count-1)
        while isinstance(self.universe.ds_objects[oid], Ship):
            oid = random.randint(0, self.universe.object_count-1)
        return oid

    def new_order(self):
        dest_oid = self.get_new_destination()
        arrival = self.fly_to(dest_oid)
        dock_time = random.randint(200, 2000)
        self.universe.events.add(tick=arrival, callback=self.arrival_break)
        self.universe.events.add(tick=arrival+dock_time, callback=self.new_order)

    def fly_to(self, oid, dv=1):
        target = self.universe.ds_objects[oid]
        travel_vector = target.position - self.my_ship.position
        travel_dist = np.linalg.norm(travel_vector)
        travel_time = math.ceil(travel_dist / dv)
        self.my_ship.fly_at(target.position, dv=1)
        return self.universe.tick + travel_time

    def arrival_break(self):
        self.my_ship.engine_break_burn()
