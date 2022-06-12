from loguru import logger
import arrow
import numpy as np

from util import adjustable_sigmoid
from util._3d import latlong_single, latlong, Quaternion as Quat


class Camera:
    def __init__(self):
        self.pos = np.asarray([0,0,0], dtype=np.float64)
        self.reset_zoom()
        self.reset_rotation()
        self.following = None
        self.tracking = None
        self.commands = [
            ('move', self.move),
            ('strafe', self.strafe),
            ('reset_rotation', self.reset_rotation),
            ('reset_zoom', self.reset_zoom),
            ('flip', self.flip),
            ('zoom', self.adjust_zoom),
            ('rotate', self.rotate),
            ('yaw', self.yaw),
            ('pitch', self.pitch),
            ('roll', self.roll),
        ]

    @property
    def state(self):
        self.update()
        return f'{self.pos}{self.rotation}{self.__zoom_level}'

    def follow(self, callback=None):
        if callback is not None:
            assert callable(callback)
        self.following = callback

    def track(self, callback=None):
        if callback is not None:
            assert callable(callback)
        self.tracking = callback

    def update(self):
        if self.following is not None:
            self.pos = np.copy(self.following())
        if self.tracking is not None:
            self.look_at_point(self.tracking(), keep_tracking=True)

    def set_position(self, point):
        self.pos = np.asarray(point, dtype=np.float64)

    def move(self, d=1, disable_follow=True):
        """Move camera
        D Distance to move forward
        """
        self.pos += self.current_axes[0] * d
        if disable_follow:
            self.follow(None)

    def strafe(self, d=1, disable_follow=True):
        """Move camera
        D Distance to move right
        """
        self.pos += self.current_axes[1] * d
        if disable_follow:
            self.follow(None)

    @property
    def zoom(self):
        return self.__zoom_level

    @property
    def current_axes(self):
        return Quat.get_rotated_axes(self.rotation)

    def reset_zoom(self):
        """Reset camera zoom"""
        self.__zoom_level = 1

    def reset_rotation(self, keep_tracking=False):
        """Reset camera rotation"""
        self.rotation = np.asarray([1,0,0,0], dtype=np.float64)
        if not keep_tracking:
            self.track(None)

    def rotate(self, yaw=0, pitch=0, roll=0, zoom_scale=False, keep_tracking=False):
        """Rotate camera
        --y YAW Number of degrees to yaw right
        --p PITCH Number of degrees to pitch up
        --r ROLL Number of degrees to roll clockwise
        --scale ZOOM_SCALE Rotate less when zoomed in and more when zoomed out
        """
        if zoom_scale:
            yaw /= self.__zoom_level
            pitch /= self.__zoom_level
        if yaw:
            yaw_qrot = Quat.from_vector_angle(self.current_axes[2], yaw)
            self.rotation = Quat.multi(self.rotation, yaw_qrot)
        if pitch:
            pitch_qrot = Quat.from_vector_angle(self.current_axes[1], pitch)
            self.rotation = Quat.multi(self.rotation, pitch_qrot)
        if roll:
            roll_qrot = Quat.from_vector_angle(self.current_axes[0], roll)
            self.rotation = Quat.multi(self.rotation, roll_qrot)
        if not keep_tracking:
            self.track(None)

    def yaw(self, yaw):
        """Yaw camera
        YAW Number of degrees to yaw right
        """
        self.rotate(yaw=yaw)

    def pitch(self, pitch):
        """Pitch camera
        PITCH Number of degrees to pitch up
        """
        self.rotate(pitch=pitch)

    def roll(self, roll):
        """Roll camera
        ROLL Number of degrees to roll clockwise
        """
        self.rotate(roll=roll)

    def flip(self):
        """Flip camera"""
        self.rotate(yaw=180)
        self.track(None)

    def adjust_zoom(self, zoom_multiplier):
        """Adjust camera zoom
        ZOOM_MULTIPLIER Fraction of current zoom (0.8 = %80 of current zoom)
        """
        self.__zoom_level = max(0.5, self.__zoom_level * zoom_multiplier)

    def look_at_point(self, point, reset_axes=True, keep_tracking=False):
        if reset_axes:
            self.reset_rotation(keep_tracking=keep_tracking)
        rotated = Quat.rotate_vector(point - self.pos, self.rotation)
        lat, long = latlong_single(rotated)
        self.rotate(yaw=lat, keep_tracking=keep_tracking)
        self.rotate(pitch=long, keep_tracking=keep_tracking)

    def swivel_to_point(self, point, total_time_ms, smooth=0):
        self.update()
        vector = Quat.normalize(point - self.pos)
        qrot = Quat.from_vector_vector(self.current_axes[0], vector)

        def swivel_tracking_callback(
            start_vector=self.current_axes[0], start_time=arrow.now()
        ):
            elapsed_ms = (arrow.now() - start_time).total_seconds() * 1000
            elapsed_ratio = elapsed_ms / total_time_ms
            if elapsed_ratio < 1:
                adjusted = adjustable_sigmoid(elapsed_ratio, smooth)
                current_qrot = Quat.pow(qrot, adjusted)
            else:
                current_qrot = qrot
                self.track(None)
            current_vector = Quat.rotate_vector(start_vector, current_qrot)
            return self.pos + current_vector

        self.track(swivel_tracking_callback)

    @property
    def lat_long(self):
        return latlong_single(self.current_axes[0])

    def get_projected_coords(self, points):
        rv = Quat.rotate_vectors(points - self.pos, self.rotation)
        ll_coords = latlong(rv)
        return ll_coords
