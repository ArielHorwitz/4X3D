from loguru import logger
import math
import numpy as np
from functools import partial

from util.config import CONFIG_DATA
from util import OBJECT_COLORS, CELESTIAL_NAMES, EPSILON
from util.argparse import arg_validation
from util.camera import Camera
from util.charmap import CharMap, TooSmallError



class Cockpit:
    def __init__(self, ship):
        self.ship = ship
        self.camera = Camera()
        self.show_labels = CONFIG_DATA['SHOW_LABELS']
        self.show_dbar = CONFIG_DATA['SHOW_DISTANCE_BARS']
        self._dbar_size = CONFIG_DATA['DISTANCE_BARS_SIZE']
        self._dbar_maxd = CONFIG_DATA['DISTANCE_BARS_MAXD']
        self._dbar_curve = CONFIG_DATA['DISTANCE_BARS_CURVE']
        self.camera_following = None
        self.camera_tracking = None
        self._last_charmap_state = bytes(1)

    @property
    def commands(self):
        cockpit_commands = [
            ('follow', self.follow),
            ('track', self.track),
            ('look', self.look),
            ('snaplook', self.snaplook),
            ('pro', self.look_prograde),
            ('retro', self.look_retrograde),
            ('labels', self.toggle_labels),
            ('dbar', self.toggle_dbar),
            ('dbar.size', self.set_dbar_size),
            ('dbar.maxd', self.set_dbar_maxd),
            ('dbar.curve', self.set_dbar_curve),
        ]
        return cockpit_commands + self.camera.commands

    @property
    def universe(self):
        return self.ship.universe

    def follow(self, oid=None):
        """ArgSpec
        Follow a deep space object
        ___
        +OID Object ID
        """
        if oid is None:
            oid = self.ship.oid
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)

        def get_pos(oid):
            return self.universe.positions[oid]
        self.camera.follow(partial(get_pos, oid))

    def track(self, oid=None):
        """ArgSpec
        Track a deep space object
        ___
        +OID Object ID
        """
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)

        def get_pos(oid):
            return self.universe.positions[oid]
        self.camera.track(partial(get_pos, oid) if oid is not None else None)

    def look(self, oid, ms=None, smooth=None):
        """ArgSpec
        Turn to look at a deep space object
        ___
        OID Object ID
        +MS How long to swivel for in ms
        -+s SMOOTH How smoothly to swivel between -1 and 1
        """
        if ms is None:
            ms = CONFIG_DATA['CAMERA_SMOOTH_TIME']
        if smooth is None:
            smooth = CONFIG_DATA['CAMERA_SMOOTH_CURVE']
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)
        with arg_validation(f'Duration in ms must be a positive number: {ms}'):
            assert ms > 0
        with arg_validation(f'Smoothness must be a number between -1 and 1: {smooth}'):
            assert -1 <= smooth <= 1

        self.camera.swivel_to_point(self.universe.ds_objects[oid].position, ms, smooth)

    def snaplook(self, oid):
        """ArgSpec
        Instantly turn to look at a deep space object
        ___
        OID Object ID
        """
        with arg_validation(f'Invalid object ID: {oid}'):
            assert self.universe.is_oid(oid)

        self.camera.look_at_point(self.universe.positions[oid])

    def look_prograde(self):
        """Turn to look at prograde vector"""
        self.camera.look_at_point(self.ship.velocity * 10 **10)

    def look_retrograde(self):
        """Turn to look at retrograde vector"""
        self.camera.look_at_point(-self.ship.velocity * 10 **10)

    def toggle_labels(self):
        """Toggle labels"""
        self.show_labels = (self.show_labels + 1) % 3

    def toggle_dbar(self):
        """Toggle distance bar"""
        self.show_dbar = (self.show_dbar + 1) % 4

    def set_dbar_size(self, size):
        """ArgSpec
        Set the maximum size of the distance bar.
        ___
        +SIZE An integer greater than 0
        """
        with arg_validation(f'Max distance must be an integer greater than 0'):
            size = int(size)
            assert size > 0
        self._dbar_size = size

    def set_dbar_maxd(self, maxd):
        """ArgSpec
        Set the maximum distance discernable by the distance bar.
        ___
        +MAXD A number greater than 0
        """
        with arg_validation(f'Max distance must be a number greater than 0'):
            maxd = float(maxd)
            assert maxd > 0
        self._dbar_maxd = float(maxd)

    def set_dbar_curve(self, curve):
        """ArgSpec
        Set the curve at which the distance bar shrinks with distance.
        ___
        +CURVE An integer bewteen 0 and 1
        """
        with arg_validation(f'Curve must be a number between 0 and 1'):
            curve = float(curve)
            assert 0 <= curve
        self._dbar_curve = curve

    # Display
    def draw_charmap(self, size):
        try:
            charmap = CharMap(self.camera, size)
        except TooSmallError as e:
            return f'{e}'
        # Collect labels
        # Since we are using add_objects (plural), we must pass a getter
        # (get_labels) for the labels, which in turn returns a sequence of
        # labels for a particular oid. We rely heavily on locals to remember
        # relevant information for this frame.
        local_label_getters = []
        if self.show_labels:
            # This is simple and doesn't not require any specific state
            local_label_getters.append(self.get_label)
        if self.show_dbar:
            # This is more complex and requires a new function def with its own
            # locals to refer to distances and their deltas for this particular
            # frame.
            local_label_getters.append(self.get_dist_label_getter())
        def get_labels(oid):
            # The actual labels getter for a particular oid. Simply get
            # a label from each getter in this frames label_getters list.
            return tuple(getter(oid) for getter in local_label_getters)
        # If we have labels to show, use the local get_labels
        get_labels = get_labels if local_label_getters else None
        # Finally, add the objects
        charmap.add_objects(
            points=self.universe.positions,
            icon=self.get_icon,
            tag=self.get_tag,
            labels=get_labels,
        )
        # Add other elements
        if self.show_labels:
            charmap.add_projection_axes()
        charmap.add_crosshair()
        charmap.add_prograde_retrograde(
            velocity=self.ship.velocity,
            show_labels=self.show_labels,
            show_speed=self.show_labels > 1,
        )
        final_string = charmap.draw()
        return final_string

    def get_charmap(self, size):
        state = ''.join([
            str(self.universe.tick),
            str(size),
            str(self.show_labels),
            str(self.show_dbar),
            str(self.camera.state),
        ])
        current_state = bytes(state, encoding='utf-8')
        if self._last_charmap_state == current_state:
            return None
        self._last_charmap_state = current_state
        return self.draw_charmap(size=size)

    def get_icon(self, oid):
        return self.universe.ds_objects[oid].icon

    def get_tag(self, oid):
        return self.universe.ds_objects[oid].color

    def get_label(self, oid):
        ob = self.universe.ds_objects[oid]
        lbl = ''
        lbl = f'{ob.oid}'
        if self.show_labels >= 2:
            lbl = f'{lbl}.{ob.name}'
        return lbl, None

    def get_dist_label_getter(self):
        rel_pos = self.universe.positions-self.ship.position
        rel_pos2 = self.universe.positions+self.universe.velocities-(self.ship.position+self.ship.velocity)
        distances = np.linalg.norm(rel_pos, axis=-1)
        distances_step = np.linalg.norm(rel_pos2, axis=-1)
        stationary = np.abs(distances - distances_step) < EPSILON
        redshift = distances < distances_step
        def get_dist_label(oid):
            dfactor = max(0, min(distances[oid] / self._dbar_maxd, 1))
            curve = math.log2(dfactor+1) ** self._dbar_curve
            bar_size = self._dbar_size - min(self._dbar_size-1, round(curve * self._dbar_size))
            bar = '─' * bar_size
            tag = None if stationary[oid] else 'red' if redshift[oid] else 'blue'
            if self.show_dbar == 1:
                bar = f'{bar}'
            elif self.show_dbar == 2:
                bar = f'{distances[oid]:.2e}'
            elif self.show_dbar == 3:
                bar = f'{bar} {distances[oid]:.2e}'
            return bar, tag
        return get_dist_label
