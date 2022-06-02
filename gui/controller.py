from loguru import logger


class Controller:
    def __init__(self, name=None):
        self.name = 'Unnamed' if name is None else name
        self.__commands = {}
        logger.info(f'Created {self.name} Controller.')

    def do_command(self, command, *args, **kwargs):
        if command not in self.__commands:
            raise KeyError(f'Command {command} not found in {self}')
        callback = self.__commands[command]
        # logger.debug(f'{self} do_command: {command} resolved to: {callback.__name__} ({callback})')
        r = callback(*args, **kwargs)
        return r

    def register_command(self, command, callback):
        if command in self.__commands:
            raise ValueError(f'Command {command} already registered in {self}')
        assert callable(callback)
        self.__commands[command] = callback
        logger.info(f'{self} register_command: {command} to: {callback.__name__} ({callback})')

    @property
    def commands(self):
        return tuple(self.__commands.keys())

    def __repr__(self):
        return f'<{self.name} Controller: {len(self.__commands)} commands>'
