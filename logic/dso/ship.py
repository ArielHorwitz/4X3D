from loguru import logger
import math
import random
import numpy as np
import itertools
from collections import defaultdict

from util import EPSILON
from util.argparse import arg_validation
from util.navigation import Navigation
from logic.dso.cockpit import Cockpit
from logic.dso.dso import DeepSpaceObject
from logic.universe import events


class Ship(DeepSpaceObject):
    type_name = 'ship'
    thrust = 1
    icon = '·'
    color = 'green'
    current_order_uid = None
    navigation = None
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
            ('patrol', self.order_patrol),
            ('cancel', self.order_cancel),
        ]

    # Orders
    def order_cancel(self):
        """Cancel scheduled flight plan operations"""
        self.current_order_uid = None
        self.navigation = None

    def order_patrol(self, oids, auto_look=False):
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
        self._do_order_patrol(oids)

    def _do_order_patrol(self, oids):
        if self.thrust == 0:
            logger.debug(f'{self} ignoring order_patrol since we have no thrust')
            return
        self.current_order_uid = uid = events.get_event_uid() 
        self.patrol_cycle = itertools.cycle(oids)
        self.universe.add_event(None, self._next_patrol,
            f'{self.label} start patrol.', uid)

    def _next_patrol(self, uid):
        if 0 != uid != self.current_order_uid:
            logger.debug(f'next_patrol with obsolete uid: {uid} {f}')
            return
        oid = next(self.patrol_cycle)
        self.fly_to(oid, self.patrol_look, uid)
        assert self.navigation is not None
        next_patrol = self.universe.tick + self.navigation.total_ticks + 200
        self.universe.add_event(next_patrol, self._next_patrol,
            f'{self.label} next patrol.', uid)

    # Navigation
    def fly_to(self, oid, look=False, uid=0):
        """ArgSpec
        Automatically schedule flight plan to a deep space object
        ___
        OID Target object ID
        -+look LOOK Turn camera to look at target before flying
        """
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)
        if self.thrust == 0:
            logger.debug(f'{self} ignoring fly_to since we have no thrust')
            return
        # Look at the target
        if look:
            self.cockpit.look(oid)
        # Plan navigation
        target = self.universe.ds_objects[oid]
        target_vector = target.position - self.position
        self.navigation = Navigation(
            target_vector, self.thrust, self.velocity,
            uid=uid, starting_tick=self.universe.tick,
            description=f'Flying to {oid}')
        self.universe.add_event(None, self._start_navigation,
            f'{self.label} start flight to: {oid}.', uid)

    def _start_navigation(self, uid):
        assert not self.navigation.started
        self._do_next_navstage(uid)

    def _do_next_navstage(self, uid):
        if self.navigation is None:
            logger.debug(f'do_next_navstage with obsolete uid: {uid} (no navigation configured)')
            return
        if 0 != uid != self.navigation.uid:
            logger.debug(f'do_next_navstage with obsolete uid: {uid} != {self.navigation.uid}')
            return
        # Do next stage
        assert not self.navigation.is_last_stage
        self.navigation.increment_stage()
        assert self.navigation.in_progress
        self.__apply_thrust(self.navigation.stage.acceleration)
        if not self.navigation.is_last_stage:
            # Queue up next event
            next_tick = self.universe.tick + self.navigation.stage.ticks
            next_desc = self.navigation.next_stage.description
            self.universe.add_event(next_tick, self._do_next_navstage,
                f'{self.label} {next_desc}', uid)
        else:
            # Increment to show the navigation has ended
            self.navigation.increment_stage()

    def __apply_thrust(self, vector):
        mag = np.linalg.norm(vector)
        if mag > self.thrust:
            vector *= self.thrust / mag
        self.universe.engine.get_derivative_second('position')[self.oid] = vector

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
            self.universe.add_event(cutoff, lambda uid: self.engine_cut_burn(),
                f'Auto cutoff engine burn: {mag} v', 0)

    # Properties
    def __repr__(self):
        return f'<Ship {self.label}>'

    @property
    def current_orders(self):
        if self.navigation is not None:
            stage = self.navigation.current_description
            nav = self.navigation.description
            if not self.navigation.ended:
                elapsed = self.universe.tick - self.navigation.starting_tick
                ticks = f'{round(elapsed)}/{round(self.navigation.total_ticks)} t'
            else:
                ticks = 'arrived'
            return f'{nav} ({ticks}): {stage}'
        return 'Docked.'


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
