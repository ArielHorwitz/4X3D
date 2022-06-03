from loguru import logger
import numpy as np

class Engine:
    def __init__(self, stats: dict[str, int]):
        self.stats = {}
        self.object_count = 0
        for stat_name, vector_size in stats.items():
            self.__add_stat(stat_name, vector_size)

    def get_stat(self, stat_name, index=slice(None)):
        return self.stats[stat_name][0, index, :]

    def get_derivative(self, stat_name, index=slice(None)):
        return self.stats[stat_name][1, index, :]

    def get_derivative_second(self, stat_name, index=slice(None)):
        return self.stats[stat_name][2, index, :]

    def __add_stat(self, stat_name: str, size: int, dtype=np.float64):
        assert stat_name not in self.stats
        self.stats[stat_name] = np.zeros((3, self.object_count, size), dtype=dtype)

    def tick(self, ticks):
        self.__apply_derivatives(ticks)

    def __apply_derivatives(self, ticks):
        for stat_table in self.stats.values():
            # First derivative (add velocity to position)
            stat_table[0] += stat_table[1] * ticks
            # Second derivative (add acceleration to velocity)
            stat_table[1] += stat_table[2] * ticks

    def add_objects(self, count=1):
        new_stats = {}
        self.object_count += count
        for stat_name, stat_table in self.stats.items():
            new_shape = list(stat_table.shape)
            new_shape[1] = 1
            new_entry = np.zeros(new_shape, dtype=stat_table.dtype)
            new_table = np.concatenate((stat_table, new_entry), dtype=stat_table.dtype, axis=1)
            logger.debug(f'add_objects {new_table.shape} ?= {self.object_count}')
            assert new_table.shape[1] == self.object_count
            new_stats[stat_name] = new_table
        self.stats = new_stats
