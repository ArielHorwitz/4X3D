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
        callback, validator = self.__commands[command]
        fixed_args = fail = validator(args)
        if isinstance(fail, ValidationFail):
            self.__feedback(ValidationFail(f'Command "{command}" {fail}'))
            return None
        r = callback(*fixed_args)
        return r

    def register_command(self, command, callback, *parsers):
        if command in self.__commands:
            raise ValueError(f'Command "{command}" already registered in {self}')
        assert callable(callback)
        validator = Validator(*parsers)
        assert isinstance(validator, Validator)
        self.__commands[command] = callback, validator
        logger.info(f'{self} registered command "{command}" with validator: {validator} to: {callback.__name__} ({callback})')

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


class Validator:
    def __init__(self, *parsers):
        for parser in parsers:
            assert isinstance(parser, BaseParser)
        self.parsers = parsers

    def __call__(self, args):
        logger.debug(f'{self} received: {args}')
        args = tuple(args)
        return_args = []
        for i, parser in enumerate(self.parsers):
            try:
                parsed_args, consumed_args = parser(args)
            except Exception as e:
                logger.debug(f'{self} with remaining args {args} failed at #{i+1} ({parser}): {format_exc(e)}')
                return ValidationFail(f'failed at arg#{i+1} ({parser}): {format_exc_short(e)}')
            if isinstance(parsed_args, ValidationFail):
                return ValidationFail(f'failed at arg#{i+1}: {parsed_args}')
            return_args.extend(parsed_args)
            args = tuple(args[consumed_args:])
        if args:
            return ValidationFail(f'got unexpected arguments: {args}')
        logger.debug(f'{self} returning: {return_args}')
        return return_args

    @property
    def parsers_repr(self):
        return ", ".join(str(p.name) for p in self.parsers)

    def __repr__(self):
        if not self.parsers:
            return '<Validator: empty>'
        return f'<Validator: {", ".join(str(p) for p in self.parsers)}>'


class BaseParser:
    _default = None
    allow_default = True
    def __init__(self, name=None, default=None, allow_default=None):
        if name is not None:
            self.name = name
        if default is not None:
            self._default = default
        if allow_default is not None:
            self.allow_default = allow_default

    def __call__(self, args):
        assert isinstance(args, tuple)
        if len(args) == 0 and self.allow_default:
            parsed_args, consumed_args = (self.default, ), 0
        else:
            parsed_args, consumed_args = self.parse(args)
        assert isinstance(parsed_args, tuple) or isinstance(parsed_args, ValidationFail)
        assert isinstance(consumed_args, int)
        return parsed_args, consumed_args

    @property
    def default(self):
        if callable(self._default):
            return self._default()
        return self._default

    def __repr__(self):
        return f'<Parser {self.name}>'


class ParseConsume(BaseParser):
    name = 'consume all'
    def parse(self, args):
        return tuple(), len(args)


class ParseCollect(BaseParser):
    name = 'collect all'
    allow_default = False
    def __init__(self, convert=None, **kwargs):
        super().__init__(**kwargs)
        self.convert = convert

    def parse(self, args):
        return tuple(args), len(args)


class ParsePush(BaseParser):
    name = f'push'
    def parse(self, args):
        return (self.default, ), 0


class ParseStr(BaseParser):
    name = 'string'
    def parse(self, args):
        a = str(args[0])
        return (a, ), 1


class ParseFloat(BaseParser):
    name = 'float'
    cls = float
    def __init__(self, min=-float('inf'), max=float('inf'), **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def parse(self, args):
        a = self.cls(args[0])
        if a < self.min:
            return ValidationFail(f'Integer must be at least: {self.min}, got: {a}'), 0
        if a > self.max:
            return ValidationFail(f'Integer must be at most: {self.max}, got: {a}'), 0
        return (a, ), 1


class ParseInt(ParseFloat):
    name = 'int'
    cls = int


class ParseBool(ParseFloat):
    name = 'bool'
    cls = bool


class ParserCustom(BaseParser):
    name = 'custom'
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    def parse(self, args):
        arg = self.callback(args[0])
        if isinstance(arg, ValidationFail):
            return arg, 0
        return (arg, ), 1


class ValidationFail(str):
    pass
