from loguru import logger
from collections import namedtuple
from util import try_number


PositionalArg = namedtuple('PositionalArg', ['name', 'desc'])
OptionalArg = namedtuple('OptionalArg', ['flag', 'name', 'desc'])

FLAG_PREFIX = '--'

EXAMPLE_DOCSTRING = f"""
Description of the command.
VARNAME1 Description of first positional argument
VARNAME1 Description of second positional argument
--flag OPTIONAL1 Description of first optional argument
--foo OPTIONAL2 Description of second optional argument
"""


class ArgParseError(Exception):
    pass


class ArgSpec:
    def __init__(self, docstring):
        self.desc, self.pos, self.opt = self._resolve_spec(docstring)
        self.spec = self.__format_spec()
        self.help = self.__format_help_verbose()

    def parse(self, args):
        astack = list(args)
        pos = []
        opt = {}
        # Parse positionals first
        while astack:
            if astack[0].startswith(FLAG_PREFIX):
                break  # Move on to optionals
            value = try_number(astack.pop(0))
            pos.append(value)
        missing_args = len(self.pos) - len(pos)
        if missing_args > 0:
            list_pos = ', '.join(spec.name for spec in self.pos[-missing_args:])
            raise ArgParseError(f'missing positional arguments: {list_pos}')
        if missing_args < 0:
            extra_args = ', '.join(str(_) for _ in pos[missing_args:])
            raise ArgParseError(f'unexpected positional arguments: {extra_args} (only want: {self.spec})')
        # Parse optionals after positionals
        while astack:
            flag = astack.pop(0).lower()
            if not flag.startswith(FLAG_PREFIX):
                raise ArgParseError(f'unexpected argument: {flag}')
            if flag not in self.opt:
                raise ArgParseError(f'unexpected optional argument: {flag} (only want: {self.spec})')
            # Find the variable name for keyword argument
            key = self.opt[flag].name.lower()
            # If no value supplied to this flag supply True
            if not astack or astack[0].startswith(FLAG_PREFIX):
                value = True
            else:
                value = try_number(astack.pop(0))
            opt[key] = value
        return tuple(pos), opt

    @classmethod
    def _resolve_spec(cls, docstring):
        pos = []
        opt = {}
        lines = docstring.split('\n')
        lines = [l.lstrip() for l in lines]
        lines = [l for l in lines if l != '']
        # Description
        if not lines:
            desc = '__MISSING DESCRIPTION__'
        else:
            desc = lines.pop(0)
        # Arguments
        for i, line in enumerate(lines):
            # Positional arguments
            if not line.startswith(FLAG_PREFIX):
                # Ensure positional arguments are not defined after optional arguments
                if opt:
                    raise ArgParseError(f'found positional argument after optional arguments: line #{i} "{line}" in docstring:\n{docstring}')
                spec = cls._resolve_positional_argspec(line)
                pos.append(spec)
            # Optional arguments
            else:
                spec = cls._resolve_optional_argspec(line)
                opt[spec.flag] = spec
        return desc, tuple(pos), opt

    @staticmethod
    def _resolve_positional_argspec(line):
        assert not line.startswith(FLAG_PREFIX)
        split = line.split(' ', 1)
        if len(split) != 2:
            raise ArgParseError(f'positional argument requires varname and description, instead got: {split}')
        varname, desc = split
        return PositionalArg(varname.upper(), desc)

    @staticmethod
    def _resolve_optional_argspec(line):
        assert line.startswith(FLAG_PREFIX)
        flag, varname, desc = line.split(' ', 2)
        return OptionalArg(flag, varname.upper(), desc)

    def __format_spec(self):
        pos = ' '.join(a.name for a in self.pos)
        opt = ' '.join(f'{spec.flag} {spec.name}' for spec in self.opt.values())
        space = ' ' if opt else ''
        return f'{pos}{space}{opt}'

    def __format_help_verbose(self):
        s = [self.desc]
        s.extend([f'{pos.name}\t\t{pos.desc}' for pos in self.pos])
        for opt in self.opt.values():
            s.append(f'{opt.flag} {opt.name}\t\t{opt.desc}')
        return '\n'.join(s)
