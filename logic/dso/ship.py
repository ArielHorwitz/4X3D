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


class Ship(DeepSpaceObject):
    type_name = 'ship'
    thrust = 1
    icon = '·'
    color = 'green'
    current_order_uid = None
    navigation = None
    patrol_look = False
    patrol_track = False

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
            ('break', self.order_break),
            ('fly', self.order_fly),
            ('patrol', self.order_patrol),
            ('burn', self.order_engine_burn),
            ('cut', self.order_engine_cut),
            ('cancel', self.order_cancel),
        ]

    # Orders
    def _cancel_orders(self):
        self.current_order_uid = None
        self.navigation = None

    def order_cancel(self, apply_breaks=True):
        """Cancel orders."""
        self._cancel_orders()
        if apply_breaks:
            self.order_break()

    def order_fly(self, oid, look=False, track=False):
        """ArgSpec
        Order flight to a deep space object.
        ___
        OID Target object ID
        -+look LOOK Turn camera to look at target
        -+track TRACK Turn camera to track the target
        """
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)
        # Look at the target
        if track:
            self.cockpit.track(oid)
        elif look:
            self.cockpit.look(oid)
        # Find target vector
        target = self.universe.ds_objects[oid]
        offset_normal = np.random.normal(size=3)
        offset = 100 * offset_normal / np.linalg.norm(offset_normal)
        target_vector = target.position + offset - self.position
        self.navigate(target_vector, description=f'Fly to {target.label}')

    def order_break(self, throttle=1):
        """ArgSpec
        Order ship to come to rest.
        ___
        +THROTTLE Engine power throttle (0 < throttle <= 1)
        """
        with arg_validation(f'Throttle must be a positive number between 0 and 1: {throttle}'):
            assert 0 < throttle <= 1
        self.navigate(
            target_vector=np.zeros(3),
            method='break_velocity',
            description=f'Breaking velocity'
        )

    def order_engine_burn(self, vector=None, throttle=1):
        """ArgSpec
        Order firing the engine.
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
        self.__apply_thrust(vector)

    def order_engine_cut(self):
        """Order cutting the engine."""
        self.__apply_thrust(np.zeros(3))

    def order_patrol(self, oids, auto_look=False, auto_track=False):
        """ArgSpec
        Order patrolling between random celestial objects.
        ___
        *OIDS list of object IDs to patrol between (leave empty for 20 random targets)
        -+look AUTO_LOOK Automatically turn camera to look at target
        -+track AUTO_TRACK Automatically turn camera to track target
        """
        if self.thrust == 0:
            logger.debug(f'{self} ignoring order_patrol since we have no thrust')
            return
        if not oids:
            oids = random.choices(np.flatnonzero(self.universe.ds_celestials), k=20)
        for check_oid in oids:
            with arg_validation(f'Invalid target ID: {check_oid}'):
                assert self.universe.is_oid(check_oid)
        self.patrol_look = auto_look
        self.patrol_track = auto_track
        self.patrol_cycle = itertools.cycle(oids)
        uid = self._new_order_uid()
        self._next_patrol(uid)

    def _next_patrol(self, uid):
        if uid != self.current_order_uid:
            logger.debug(f'next_patrol with obsolete uid: {uid}')
            return
        oid = next(self.patrol_cycle)
        self.order_fly(oid, look=self.patrol_look, track=self.patrol_track)
        assert self.navigation is not None
        next_patrol = self.universe.tick + self.navigation.total_ticks + 200
        self.universe.add_event(uid, next_patrol, self._next_patrol,
            f'{self.label} next patrol.')

    def _new_order_uid(self):
        self.current_order_uid = random.random()
        return self.current_order_uid

    # Navigation
    def navigate(self, target_vector, method=None, description=None):
        if self.thrust == 0:
            logger.debug(f'{self} ignoring fly_to since we have no thrust')
            return
        uid = random.random()
        if description is None:
            d = np.linalg.norm(target_vector)
            description = f'Navigating {d:.2e} distance to {target_vector}'
        self.navigation = Navigation(
            target_vector, self.thrust, self.velocity,
            method=method, uid=uid, starting_tick=self.universe.tick,
            description=description)
        self._do_next_navstage(uid)

    def _do_next_navstage(self, uid):
        if self.navigation is None:
            logger.debug(f'do_next_navstage with obsolete uid: {uid} (no navigation configured)')
            return
        if uid != self.navigation.uid:
            logger.debug(f'do_next_navstage with obsolete uid: {uid} != {self.navigation.uid}')
            return
        # Do next stage
        assert not self.navigation.is_last_stage
        self.navigation.increment_stage()
        assert self.navigation.in_progress
        self.__apply_thrust(self.navigation.stage.acceleration)
        # Check if another event is required
        if not self.navigation.is_last_stage:
            next_tick = self.universe.tick + self.navigation.stage.ticks
            description = self.navigation.next_stage.description
            self.universe.add_event(uid, next_tick, self._do_next_navstage,
                f'{self.label} {description}')
        else:
            # Increment to show the navigation has ended
            self.navigation.increment_stage()

    def __apply_thrust(self, vector):
        mag = np.linalg.norm(vector)
        if mag > self.thrust:
            vector *= self.thrust / mag
        self.universe.engine.get_derivative_second('position')[self.oid] = vector

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
