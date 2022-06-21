from loguru import logger
import math
from collections import namedtuple
import numpy as np

from util import EPSILON


Stage = namedtuple('NavigationStage', ['acceleration', 'ticks', 'description'])


class Navigation:
    NAV_METHODS = ['naive_fastest']

    def __init__(self, target_vector, thrust, initial_velocity,
            method=None, uid=None, starting_tick=0, description=None):
        self.uid = uid
        self.description = 'Unspecified navigation' if description is None else description
        self.starting_tick = starting_tick
        self.target_vector = target_vector
        self.thrust = thrust
        self.initial_velocity = initial_velocity
        self.nav_method = self.NAV_METHODS[0] if method is None else method
        nav_method = getattr(self, self.nav_method)
        self.stages = nav_method(target_vector, thrust, initial_velocity)
        self.stage_count = len(self.stages)
        assert self.stage_count > 0
        self.total_ticks = sum(s.ticks for s in self.stages)
        self.current_index = -1

    def increment_stage(self):
        if self.ended:
            return
        self.current_index += 1

    # Navigation methods
    @staticmethod
    def naive_fastest(target_vector, thrust, initial_velocity):
        stages = []
        rest_displacement = 0
        # If we are not at rest, our first stage will bring us to rest
        initial_velocity_size = magnitude(initial_velocity)
        if initial_velocity_size > EPSILON:
            burn_vector = normalize(-initial_velocity) * thrust
            burn_duration = initial_velocity_size / thrust
            stages.append(Stage(
                acceleration=burn_vector, ticks=burn_duration,
                description=f'Rest burn ({burn_duration:.2f} t)',
            ))
            # Consider displacement during this burn, subtract from target vector
            rest_displacement = get_displacement(
                burn_duration, burn_vector, initial_velocity)
            target_vector -= rest_displacement

        # At rest, on to cruise burn
        burn_vector = normalize(target_vector) * thrust

        resting_target_dist = magnitude(target_vector)
        _root_component = 4 * thrust * resting_target_dist
        burn_duration = math.sqrt(_root_component) / (2 * thrust)

        stages.extend([
            Stage(
                acceleration=burn_vector, ticks=burn_duration,
                description=f'Departure burn ({burn_duration:.2f} t)'),
            Stage(
                acceleration=-burn_vector, ticks=burn_duration,
                description=f'Break burn ({burn_duration:.2f} t)'),
            Stage(
                acceleration=0, ticks=0,
                description=f'Arrival, cut engine'),
        ])
        return tuple(stages)

    # Properties
    def __repr__(self):
        return f'<Navigation {self.description} {self.uid} ({self.current_description})>'

    @property
    def started(self):
        return self.current_index >= 0

    @property
    def ended(self):
        return self.current_index >= self.stage_count

    @property
    def in_progress(self):
        return self.started and not self.ended

    @property
    def is_last_stage(self):
        return self.current_index == (self.stage_count - 1)

    @property
    def next_stage(self):
        assert not self.ended and not self.is_last_stage
        return self.stages[self.current_index + 1]

    @property
    def stage(self):
        assert self.in_progress
        return self.stages[self.current_index]

    @property
    def current_description(self):
        if not self.started:
            return f'Prepared {self.stage_count} stages'
        elif self.ended:
            return f'Completed {self.stage_count} stages'
        assert self.in_progress
        return f'{self.stage.description} (stage {self.current_index+1}/{self.stage_count})'


def get_displacement(ticks, acc, vel):
    return acc * (ticks ** 2) / 2 + (ticks * vel)


def magnitude(v):
    return np.linalg.norm(v)


def normalize(v):
    return v / np.linalg.norm(v)


def test_method_names():
    for m in Navigation.NAV_METHODS:
        nav = Navigation(
            target_vector=np.asarray([1, 1, 1], dtype=np.float64),
            thrust=1,
            initial_velocity=np.asarray([-1, -1, -1], dtype=np.float64),
            description=f'Test', method=m)
        for stage in nav.stages:
            assert isinstance(stage, Stage)


test_method_names()
