from loguru import logger
from util.argparse import ArgSpec, ArgParseError


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
        try:
            parsed = argspec.parse(args)
        except ArgParseError as e:
            m = f'Command "{command}" failed: {e.args[0]}'
            logger.warning(m)
            self.__feedback(m)
            return
        args, kwargs = parsed
        r = callback(*args, **kwargs)
        return r

    def register_command(self, command, callback):
        if command in self.__commands:
            raise ValueError(f'Command "{command}" already registered in {self}')
        assert callable(callback)
        raw_argspec = callback.__doc__
        try:
            argspec = ArgSpec(raw_argspec if raw_argspec is not None else '')
        except ArgParseError as e:
            raise ValueError(f'Command "{command}" failed to resolve docstring as argspec:\n{e.args[0]}')
        self.__commands[command] = callback, argspec
        logger.info(f'{self} registered command "{command}" to {callback} with argspec: <{argspec.spec}>')

    def sorted_items(self):
        s = sorted(list(self.__commands.keys()))
        return ((name, *self.__commands[name]) for name in s)

    def __repr__(self):
        return f'<{self.name} Controller>'
