from loguru import logger
import math
import random
import numpy as np
import itertools
from functools import wraps
from collections import defaultdict, namedtuple

from util import EPSILON
from util.argparse import arg_validation
from logic.dso.cockpit import Cockpit
from logic.dso.dso import DeepSpaceObject


FlightPlan = namedtuple('FlightPlan', ['cutoff', 'break_burn', 'arrival', 'total'])


class Ship(DeepSpaceObject):
    type_name = 'ship'
    thrust = 1
    icon = '·'
    color = 'green'
    current_order_uid = None
    current_flight = None
    patrol_look = False

    def setup(self, fid, name, parent=None):
        self.fid = fid
        self.name = name
        self.my_admiral = self.universe.admirals[fid]
        if parent is None:
            parent_oid = random.choice(np.flatnonzero(self.universe.ds_celestials))
            parent = self.universe.ds_objects[parent_oid]
        self.offset_from_parent(parent, 10**2)
        self.label = f'{self.icon}{self.oid} {self.name}'
        self.cockpit = Cockpit(ship=self)
        self.cockpit.follow(self.oid)
        self.stats = defaultdict(lambda: 0)

    @property
    def commands(self):
        return [
            ('fly', self.fly_to),
            ('burn', self.engine_burn),
            ('break', self.engine_break_burn),
            ('cut', self.engine_cut_burn),
            ('patrol', self.command_order_patrol),
            ('cancel', self.order_cancel),
        ]

    # Orders
    def event_callback(f):
        @wraps(f)
        def event_callback_wrapper(self, uid):
            # Ignore event callback if uid is obsolete
            # uid of 0 means ignore uid check (force callback)
            if uid != 0 and self.check_obsolete_order(uid):
                logger.debug(f'event_callback with obsolete uid: {uid} {f}')
                return
            f(self, uid)
        return event_callback_wrapper

    def check_obsolete_order(self, uid):
        return uid != self.current_order_uid

    def order_cancel(self):
        """Cancel scheduled flight plan operations"""
        self.current_order_uid = None
        self.current_flight = None

    def order_patrol(self, oids):
        if self.thrust == 0:
            logger.debug(f'{self} ignoring order_patrol since we have no thrust')
            return
        self.current_order_uid = uid = random.random()
        self.patrol_cycle = itertools.cycle(oids)
        self.universe.add_event(uid, None, self.next_patrol,
            f'{self.label} start patrol.')

    def command_order_patrol(self, oids, auto_look=False):
        """ArgSpec
        Patrol between random celestial objects
        ___
        *OIDS list of object IDs to patrol between (leave empty for 5 random targets)
        -+look AUTO_LOOK Automatically turn camera to look at target before flying
        """
        if not oids:
            oids = random.choices(np.flatnonzero(self.universe.ds_celestials), k=20)
        for check_oid in oids:
            with arg_validation(f'Invalid target ID: {check_oid}'):
                assert self.universe.is_oid(check_oid)
        self.patrol_look = auto_look
        self.order_patrol(oids)

    @event_callback
    def next_patrol(self, uid):
        oid = next(self.patrol_cycle)
        logger.debug(f'{self} next_patrol oid: {oid}')
        self.current_flight = self.fly_to(oid, 10**8, self.patrol_look, uid)
        next_patrol = self.current_flight.arrival + 200
        self.universe.add_event(uid, next_patrol, self.next_patrol,
            f'{self.label} next patrol.')

    # Navigation
    def fly_to(self, oid, cruise_speed=10**10, look=False, uid=0):
        """ArgSpec
        Automatically schedule flight plan to a deep space object
        ___
        OID Target object ID
        +CRUISE_SPEED Maximum cruising speed
        -+LOOK Turn camera to look at target before flying
        """
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)
        with arg_validation(f'Cruise speed must be a positive number: {cruise_speed}'):
            assert cruise_speed > 0
        if self.thrust == 0:
            logger.debug(f'{self} ignoring fly_to since we have no thrust')
            return

        if look:
            self.cockpit.look(oid)
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
        self.universe.add_event(uid, plan.cutoff, self.fly_cruise_cutoff,
            f'{self.label}: Cruise burn cutoff')
        self.current_flight = plan
        return plan

    @event_callback
    def fly_cruise_cutoff(self, uid):
        self.engine_cut_burn()
        self.universe.add_event(uid, self.current_flight.break_burn, self.fly_break_burn,
        f'{self.label}: break burn ignition')

    @event_callback
    def fly_break_burn(self, uid):
        self.engine_break_burn()
        self.universe.add_event(uid, self.current_flight.arrival, self.fly_end,
            f'{self.label}: break burn cutoff, arrival.')

    @event_callback
    def fly_end(self, uid):
        self.engine_cut_burn()
        self.current_flight = None

    @staticmethod
    def _simple_flight_plan(travel_dist, cruise_speed, thrust, tick_offset=0):
        burn_time = cruise_speed / thrust
        burn_distance = burn_time * (burn_time + 1) // 2 * thrust
        while burn_distance >= travel_dist / 2:
            cruise_speed *= 0.95
            burn_time = cruise_speed / thrust
            burn_distance = burn_time * (burn_time + 1) // 2 * thrust
        cruise_dist = travel_dist - (burn_distance * 2)
        cruise_time = cruise_dist / cruise_speed
        total = burn_time * 2 + cruise_time
        cutoff = tick_offset + burn_time
        break_burn = cutoff + cruise_time
        arrival = break_burn + burn_time
        fp = FlightPlan(cutoff, break_burn, arrival, total)
        assert arrival / (tick_offset + total) - 1 < EPSILON
        return fp

    # Engine
    def engine_burn(self, vector=None, throttle=1):
        """ArgSpec
        Run the engine
        ___
        +THROTTLE Engine power throttle (0 < throttle <= 1)
        """
        if vector is None:
            self.cockpit.camera.update()
            vector = self.cockpit.camera.current_axes[0]
        with arg_validation(f'Throttle must be a positive number between 0 and 1: {throttle}'):
            assert 0 < throttle <= 1
        with arg_validation(f'Invalid vector: {vector}'):
            assert isinstance(vector, np.ndarray)
            assert vector.shape == (3, )

        mag = np.linalg.norm(vector)
        if mag == 0:
            m = f'{self} trying to engine burn without direction: {vector}'
            logger.warning(m)
            return
        vector *= self.thrust * throttle / mag
        self.universe.engine.get_derivative_second('position')[self.oid] = vector

    def engine_cut_burn(self):
        """Cut the engine"""
        self.universe.engine.get_derivative_second('position')[self.oid] = 0

    def engine_break_burn(self, throttle=1, auto_cutoff=False):
        """ArgSpec
        Engine burn to break velocity
        ___
        +THROTTLE Engine power throttle (0 < throttle <= 1)
        -+cut AUTO_CUTOFF Schedule automatic engine cut when breaking done
        """
        with arg_validation(f'Throttle must be a positive number between 0 and 1: {throttle}'):
            assert 0 < throttle <= 1

        v = self.universe.velocities[self.oid]
        mag = np.linalg.norm(v)
        if mag == 0:
            m = f'{self} trying to engine break burn without direction: {v}'
            logger.warning(m)
            return
        self.engine_burn(-v, throttle)
        if auto_cutoff:
            cutoff = self.universe.tick + mag / self.thrust
            self.universe.add_event(0, cutoff, lambda uid: self.engine_cut_burn(),
                f'Auto cutoff engine burn: {mag} v')

    # Properties
    def __repr__(self):
        return f'<Ship {self.label}>'

    @property
    def current_orders(self):
        if self.current_flight:
            return self.format_fp(self.current_flight)
        elif self.current_order_uid is not None:
            return 'Docked.'
        return 'Idle.'

    def format_fp(self, fp):
        remaining = self.universe.tick - fp.arrival
        if self.universe.tick < fp.cutoff:
            return f'Cruise burn: {self.universe.tick - fp.cutoff:.4f} ({remaining:.4f})'
        elif self.universe.tick < fp.break_burn:
            return f'Cruising: {self.universe.tick - fp.break_burn:.4f} ({remaining:.4f})'
        return f'Break burn: {self.universe.tick - fp.arrival:.4f}'


class Tug(Ship):
    type_name = 'tug'
    thrust = 0.01
    icon = '¬'
    color = 'yellow'


class Fighter(Ship):
    type_name = 'fighter'
    thrust = 3
    icon = '‡'
    color = 'red'


class Escort(Ship):
    type_name = 'escort'
    thrust = 1
    icon = '≡'
    color = 'green'


class Port(Ship):
    type_name = 'port'
    thrust = 0
    icon = 'þ'
    color = 'blue'
