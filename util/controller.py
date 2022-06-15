from loguru import logger
from util import escape_html
from util.argparse import ArgSpec, ArgParseError


class Controller:
    def __init__(self, name=None, feedback=None):
        self.name = 'Unnamed' if name is None else name
        self.__feedback = logger.warning
        if feedback is not None:
            self.set_feedback(feedback)
        self.__commands = {}
        self.__cache = {}
        logger.info(f'Created {self.name} Controller.')

    def set_feedback(self, callback):
        assert callable(callback)
        self.__feedback = callback

    def has(self, command):
        return self.has_command(command) or self.has_cached(command)

    def has_command(self, command):
        return command in self.__commands

    def has_cached(self, command):
        return command in self.__cache

    def do_command(self, command, arg_string=None, custom_args=(), custom_kwargs={}):
        if not self.has_command(command):
            if not self.has_cached(command):
                self.__feedback(f'Command "{command}" not found')
                return None
            else:
                return self.__cache[command]
        callback, argspec = self.__commands[command]
        if arg_string is None:
            arg_string = ''
        try:
            if custom_args or custom_kwargs:
                return callback(*custom_args, **custom_kwargs)
            r = argspec.parse_and_call(arg_string, callback)
        except ArgParseError as e:
            m = f'Command "{command}" failed: {e.args[0]}'
            logger.warning(m)
            self.__feedback(m)
            return m
        return r

    def cache(self, command, value):
        if self.has_command(command):
            raise ValueError(f'Command "{command}" already registered in {self}')
        self.__cache[command] = value
        logger.debug(f'{self} cached {command}')

    def register_command(self, command, callback, spec_name=None):
        if self.has_command(command):
            raise ValueError(f'Command "{command}" already registered in {self}')
        assert callable(callback)
        raw_argspec = callback.__doc__
        if raw_argspec is None:
            raw_argspec = ''
        if spec_name is None:
            spec_name = command
        try:
            argspec = ArgSpec(raw_argspec, name=spec_name)
        except ArgParseError as e:
            raise ValueError(f'Command "{command}" failed to resolve docstring as argspec:\n{e.args[0]}')
        self.__commands[command] = callback, argspec
        logger.info(f'{self} registered command "{command}" to {callback} with argspec: <{argspec.spec}>')

    def sorted_items(self):
        s = sorted(list(self.__commands.keys()))
        return ((name, *self.__commands[name]) for name in s)

    def get_command(self, command):
        assert self.has_command(command)
        return self.__commands[command]

    @property
    def commands(self):
        return tuple(self.__commands.keys())

    @property
    def cached(self):
        return tuple(self.__cache.keys())

    def __repr__(self):
        return f'<{self.name} Controller>'
