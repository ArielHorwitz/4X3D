from loguru import logger
from util import format_exc, format_exc_short


class Controller:
    def __init__(self, name=None, feedback=None):
        self.name = 'Unnamed' if name is None else name
        self.__feedback = logger.warning
        if feedback is not None:
            self.set_feedback(feedback)
        self.__commands = {}
        logger.info(f'Created {self.name} Controller.')

    @property
    def feedback(self):
        return self.__feedback

    def set_feedback(self, callback):
        assert callable(callback)
        self.__feedback = callback

    def has_command(self, command):
        return command in self.__commands

    def do_command(self, command, args):
        if not self.has_command(command):
            self.__feedback(f'Command "{command}" not found in {self}')
            return None
        callback, argspec = self.__commands[command]
        r = callback(*args)
        return r

    def register_command(self, command, callback):
        if command in self.__commands:
            raise ValueError(f'Command "{command}" already registered in {self}')
        assert callable(callback)
        argspec = callback.__doc__
        self.__commands[command] = callback, argspec
        logger.info(f'{self} registered command "{command}" to: {callback.__name__} ({callback})')

    @property
    def sorted_commands(self):
        return sorted(list(self.__commands.keys()))

    def items(self):
        return ((n, *self.__commands[n]) for n in self.sorted_commands)

    @property
    def commands(self):
        return self.__commands

    def __repr__(self):
        return f'<{self.name} Controller: {len(self.__commands)} commands>'
