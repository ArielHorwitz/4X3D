from loguru import logger
import numpy as np
from logic._3d.quaternion import Quaternion as Quat
from logic._3d import latlong_single, latlong, unit_vectors


class Camera:
    def __init__(self):
        self.pos = np.asarray([0,0,0], dtype=np.float64)
        self.reset_zoom()
        self.reset_rotation()
        self.following = None
        self.tracking = None
        self.commands = {
            'move': self.move,
            'strafe': self.strafe,
            'reset_rotation': self.reset_rotation,
            'reset_zoom': self.reset_zoom,
            'flip': self.flip,
            'zoom': self.adjust_zoom,
            'rotate': self.rotate,
            'yaw': self.yaw,
            'pitch': self.pitch,
            'roll': self.roll,
        }

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
            self.look_at_vector(self.tracking(), disable_track=False)

    def set_position(self, point):
        self.pos = np.asarray(point, dtype=np.float64)

    def move(self, d=1, disable_follow=True):
        self.pos += self.current_axes[0] * d
        if disable_follow:
            self.follow(None)

    def strafe(self, d=1, disable_follow=True):
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
        self.__zoom_level = 1

    def reset_rotation(self, disable_track=True):
        self.rotation = np.asarray([1,0,0,0], dtype=np.float64)
        if disable_track:
            self.track(None)

    def rotate(self, yaw=0, pitch=0, roll=0, consider_zoom=True, disable_track=True):
        if consider_zoom:
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
        if disable_track:
            self.track(None)

    def yaw(self, yaw):
        self.rotate(yaw=yaw, consider_zoom=False)

    def pitch(self, pitch):
        self.rotate(pitch=pitch, consider_zoom=False)

    def roll(self, roll):
        self.rotate(roll=roll)

    def flip(self):
        self.rotate(yaw=180, consider_zoom=False)
        self.track(None)

    def adjust_zoom(self, zoom_multiplier):
        self.__zoom_level = max(0.5, self.__zoom_level * zoom_multiplier)

    def look_at_vector(self, vector, reset_axes=True, disable_track=True):
        if reset_axes:
            self.reset_rotation(disable_track=disable_track)
        rotated = Quat.rotate_vector(vector - self.pos, self.rotation)
        lat, long = latlong_single(rotated)
        self.rotate(yaw=lat, consider_zoom=False, disable_track=disable_track)
        self.rotate(pitch=long, consider_zoom=False, disable_track=disable_track)

    @property
    def lat_long(self):
        return latlong_single(self.current_axes[0])

    def get_projected_coords(self, points):
        rv = Quat.rotate_vectors(points - self.pos, self.rotation)
        ll_coords = latlong(rv)
        return ll_coords
