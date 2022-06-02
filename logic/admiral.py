
from loguru import logger
import random
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
        self.ship_prefix = PREFIXES[self.fid]
        self.my_ships = []
        self._queue_poll(offset=self.fid+1)

    def setup(self):
        my_ship = Ship()
        new_oid = self.universe.add_object(my_ship)
        my_ship.setup(
            universe=self.universe, oid=new_oid,
            name=f'{self.ship_prefix}. {random.choice(CELESTIAL_NAMES)}',
            color=random.randint(0, len(OBJECT_COLORS)-1),
        )
        self.my_ships.append(new_oid)

    def _queue_poll(self, offset=0):
        self.universe.events.add(
            tick=self.universe.tick+ADMIRAL_POLL_INTERVAL+offset,
            callback=self._queue_poll,
        )
        self.poll()

    def poll(self):
        logger.debug(f'{self} polled @{self.universe.tick}')

    def __repr__(self):
        return f'<Admiral {self.name} FID #{self.fid}>'

    @property
    def ship_oid(self):
        return self.my_ships[0]


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
