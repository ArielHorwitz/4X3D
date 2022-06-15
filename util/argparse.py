from loguru import logger
from collections import namedtuple
from contextlib import contextmanager
from util import format_exc


def _try_number(v):
    try:
        r = float(v)
        if r == int(r):
            return int(r)
        return r
    except ValueError as e:
        return v


SPEC_VERSION = 'ArgSpec'
ArgumentSpec = namedtuple('ArgumentSpec', ['flag', 'name', 'desc', 'required', 'sequence'])


class ArgSpecError(Exception):
    pass


class ArgParseError(Exception):
    pass


@contextmanager
def arg_validation(m, exceptions=(Exception,)):
    """A context manager to "replace" arbitrary exceptions with an ArgParseError."""
    try:
        yield
    except exceptions as e:
        logger.info(f'arg_validation caught:\n{format_exc(e)}\nReplaced with: ArgParseError(\'{m}\')')
        raise ArgParseError(m)


class ArgSpec:
    def __init__(self, spec_string, name='unnamed_command'):
        self.name = name
        self._resolve_spec(spec_string)

    def parse(self, args_string):
        astack = list(a for a in args_string.split(' ') if a != '')
        parsed_pos = []
        remaining_pos = []
        parsed_key = {}
        remaining_key = {}
        missing_keys = list(self.required_keys)
        pos_required_count = len(self.pos)
        pos_expected_count = pos_required_count + len(self.pos_optional)

        # Start parsing words
        while astack:
            a = astack.pop(0)
            # Handle new positional argument
            if not self.is_flag(a):
                # Ensure we expect this arg (and have not yet started to parse key arguments)
                expected = len(parsed_pos) < pos_expected_count
                allowed = expected or self.remaining_pos is not None
                if parsed_key or not allowed:
                    raise ArgParseError(f'Unexpected argument: {a} (expected: <{self.spec}>)')
                if expected:
                    parsed_pos.append(_try_number(a))
                else:
                    remaining_pos.append(_try_number(a))
            # Handle new key argument
            else:
                flag = name = self._get_flag_name(a)
                # Find details of this flag
                expected = flag in self.keys
                if expected:
                    spec = self.keys[flag]
                else:
                    is_sequence = self._get_flag_sequence(a)
                    required = False
                    spec = ArgumentSpec(flag, name, 'extra flag', required, is_sequence)
                if not expected and self.remaining_key is None:
                    raise ArgParseError(f'Unexpected flag: {flag} (expected: <{self.spec}>)')
                if spec.required:
                    missing_keys.remove(flag)
                # Find value for this key
                value = True
                if not spec.sequence:
                    if astack and not self.is_flag(astack[0]):
                        value = _try_number(astack.pop(0))
                else:
                    value = []
                    while astack:
                        if self.is_flag(astack[0]):
                            break
                        value.append(_try_number(astack.pop(0)))
                    value = tuple(value)
                if expected:
                    parsed_key[spec.name.lower()] = value
                else:
                    remaining_key[spec.name.lower()] = value

        # Check that required arguments parsed
        if len(parsed_pos) < pos_required_count:
            raise ArgParseError(f'Missing arguments: {", ".join(s.name.upper() for s in self.pos[len(parsed_pos):])}')
        if missing_keys:
            raise ArgParseError(f'Missing arguments: {", ".join(f"-{_} {self.keys[_].name.upper()}" for _ in missing_keys)}')
        return tuple(parsed_pos), tuple(remaining_pos), parsed_key, remaining_key

    def dict_from_parsed(self, pos, pos_rem, key, key_rem):
        pos = {self.all_pos[i].name.lower(): value for i, value in enumerate(pos)}
        if self.remaining_pos is not None:
            pos_rem = {self.remaining_pos.name.lower(): pos_rem}
        else:
            pos_rem = {}
        return {
            **pos,
            **pos_rem,
            **key,
            **key_rem,
        }

    def parse_and_call(self, args_string, func):
        parsed = self.parse(args_string)
        kwargs = self.dict_from_parsed(*parsed)
        return func(**kwargs)

    def _resolve_spec(self, spec_string):
        self.desc = '__MISSING DESCRIPTION__'
        self.desc_long = ''
        self.pos = []
        self.pos_optional = []
        self.remaining_pos = None
        self.keys = {}
        self.required_keys = []
        self.remaining_key = None
        current_stage_types = {'pos'}
        remaining_stages = [
            {'pos-opt'},
            {'pos-rem'},
            {'key', 'key-list', 'key-opt', 'key-opt-list'},
            {'key-rem'},
        ]
        current_stage = 0

        lines = [l.lstrip() for l in spec_string.split('\n')]
        if lines[0].startswith(SPEC_VERSION):
            lines.pop(0)

        # Find the description (while dicarding empty lines)
        while lines:
            line = lines.pop(0)
            if line == '':
                continue
            self.desc = line
            break
        # Discard empty lines until long description starts
        while lines:
            if lines[0] == '':
                lines.pop(0)
            break
        # Long description (all lines until "___")
        desc_long_lines = []
        while lines:
            line = lines.pop(0)
            if line == '___':
                break
            desc_long_lines.append(line)
        # Remove trailing empty lines
        while desc_long_lines:
            if desc_long_lines[-1] != '':
                break
            desc_long_lines.pop()
        self.desc_long = '\n'.join(desc_long_lines)
        # From now on we ignore all empty lines
        lines = [l for l in lines if l != '']
        # Parse argument specs
        while lines:
            raw_line = lines.pop(0)
            arg_type, spec_chars = self._resolve_line_type(raw_line)
            line = raw_line[spec_chars:]
            # Keep track of current stage, keeping order of argument types
            try:
                while arg_type not in current_stage_types:
                    current_stage_types = remaining_stages.pop(0)
                    current_stage = 4 - len(remaining_stages)
            except IndexError:
                raise ArgSpecError(f'Unknown (or wrong order of) argument type: {arg_type}')
            # Positionals
            if current_stage <= 2:
                try:
                    name, desc = line.split(' ', 1)
                    name = self._get_name(name)
                except ValueError:
                    raise ArgSpecError(f'ArgSpec expecting space-delimited name and description, got: "{line}"')
                if not self.legal_varname(name):
                    raise ArgSpecError(f'Variable name must start with alphabetic character or underscore')
                if current_stage == 0:
                    self.pos.append(ArgumentSpec('', name, desc, required=True, sequence=False))
                elif current_stage == 1:
                    self.pos_optional.append(ArgumentSpec('', name, desc, required=False, sequence=False))
                else:
                    self.remaining_pos = ArgumentSpec('', name, desc, required=False, sequence=True)
            # Keys
            elif current_stage == 3:
                try:
                    flag, name, desc = line.split(' ', 2)
                    flag = self._get_name(flag)
                    name = self._get_name(name)
                except ValueError:
                    raise ArgSpecError(f'ArgSpec expecting space-delimited flag, name, and description, got: "{line}"')
                if not self.legal_varname(flag):
                    raise ArgSpecError(f'Flag name must start with alphabetic character or underscore, got: {flag}')
                if not self.legal_varname(name):
                    raise ArgSpecError(f'Variable name must start with alphabetic character or underscore, got: {name}')
                required, sequence = self._resolve_key_type(arg_type)
                if required:
                    self.required_keys.append(flag)
                self.keys[flag] = ArgumentSpec(flag, name, desc, required, sequence)
            elif current_stage == 4:
                try:
                    name, desc = line.split(' ', 1)
                except ValueError:
                    raise ArgSpecError(f'ArgSpec expecting space-delimited name and description, got: "{line}"')
                self.remaining_key = ArgumentSpec('', name, desc, required=False, sequence=2)
        self.pos = tuple(self.pos)
        self.pos_optional = tuple(self.pos_optional)
        self.all_pos = self.pos + self.pos_optional
        self.spec = self.__format_spec()
        self.spec_verbose = self.__format_spec_verbose()
        self.help = self.__format_help()
        self.help_verbose = self.__format_help_verbose()

    def __format_spec(self):
        pos = ' '.join(a.name.upper() for a in self.pos)
        pos_opt = ' '.join(f'[{a.name.upper()}]' for a in self.pos_optional)
        pos_rem = ''
        if self.remaining_pos:
            pos_rem = f'*{self.remaining_pos.name.upper()}'
        keys = ' '.join(f'-{spec.flag} {"*" if spec.sequence else ""}{spec.name.upper()}' for spec in self.keys.values() if spec.required)
        keys_opt = ' '.join(f'[-{spec.flag} {"*" if spec.sequence else ""}{spec.name.upper()}]' for spec in self.keys.values() if not spec.required)
        key_rem = ''
        if self.remaining_key:
            key_rem = f'**{self.remaining_key.name.upper()}'
        return ' '.join(p for p in [
            pos, pos_opt, pos_rem, keys, keys_opt, key_rem
            ] if p)

    def __format_spec_verbose(self):
        def format_spec(s):
            flag = s.flag
            if flag:
                flag = f'-{s.flag}'
            many = '*' * s.sequence
            name = f'{many}{s.name.upper()}'
            if not s.required:
                name = f'[{name}]'
            return f'{flag:>15}{name:>15}  {s.desc}'

        pos = '\n'.join(format_spec(s) for s in self.pos)
        pos_opt = '\n'.join(f'{format_spec(s)}' for s in self.pos_optional)
        pos_rem = ''
        if self.remaining_pos:
            pos_rem = format_spec(self.remaining_pos)
        keys = '\n'.join(f'{format_spec(s)}' for s in self.keys.values() if s.required)
        keys_opt = '\n'.join(f'{format_spec(s)}' for s in self.keys.values() if not s.required)
        key_rem = ''
        if self.remaining_key:
            key_rem = format_spec(self.remaining_key)
        return '\n'.join(p for p in [
            pos, pos_opt, pos_rem, keys, keys_opt, key_rem
            ] if p)

    def __format_help(self):
        return '\n'.join([
            f'### {self.desc}',
            '',
            f'TO USE: {self.name} {self.__format_spec()}',
            '',
            f'{self.__format_spec_verbose()}',
        ])

    def __format_help_verbose(self):
        return '\n'.join([
            f'{self.__format_help()}',
            '',
            f'{self.desc_long}',
        ])

    @staticmethod
    def _get_name(name):
        return name.lower().replace('-', '_')

    @staticmethod
    def _resolve_key_type(key_type):
        return ('opt' not in key_type, 'list' in key_type)

    @staticmethod
    def _resolve_line_type(line):
        first = line[0]
        two = line[:2]
        if line[:3] == '-+*':
            return 'key-opt-list', 3
        if two == '-*':
            return 'key-list', 2
        if two == '-+':
            return 'key-opt', 2
        if two == '**':
            return 'key-rem', 2
        if first == '+':
            return 'pos-opt', 1
        if first == '*':
            return 'pos-rem', 1
        if first == '-':
            return 'key', 1
        return 'pos', 0

    @staticmethod
    def legal_varname(name):
        assert isinstance(name, str)
        if not name:
            return False
        if name != name.lower():
            return False
        fc = name[0]
        return fc.isalpha() or fc == '_'

    @classmethod
    def is_flag(cls, flag):
        return flag.startswith('-') and cls.legal_varname(cls._get_flag_name(flag))

    @classmethod
    def _get_flag_sequence(cls, flag):
        assert cls.is_flag(flag)
        if flag.startswith('--'):
            return True
        assert flag.startswith('-')
        return False

    @classmethod
    def _get_flag_name(cls, flag):
        if flag.startswith('--'):
            return cls._get_name(flag[2:])
        if flag.startswith('-'):
            return cls._get_name(flag[1:])

    def debug(self):
        return '\n'.join([
            f'<<desc>>: {self.desc}',
            f'<<desclong>>: {self.desc_long[:50]}...',
            f'<<spec>>: {self.spec}',
            f'<<pos>>:',
            *[f'  {s}' for s in self.pos],
            f'<<posopt>>:',
            *[f'  {s}' for s in self.pos_optional],
            f'<<posrem>>: {self.remaining_pos}',
            f'<<keys>>:',
            *[f'  {s}' for s in self.keys.values()],
            f'<<keysreq>>: {self.required_keys}',
            f'<<keysrem>>: {self.remaining_key}',
        ])

    def __repr__(self):
        return f'<ArgSpec <{self.spec}>>'

def __func(branch, refspec, signature, set_upstream, repository=None, force=False, tags=None, **options):
    print(',\n'.join([
        f'branch={repr(branch)}',
        f'repository={repr(repository)}',
        f'refspec={repr(refspec)}',
        f'signature={repr(signature)}',
        f'set_upstream={repr(set_upstream)}',
        f'force={repr(force)}',
        f'tags={repr(tags)}',
        *[f'{k}={repr(v)}' for k, v in options.items()],
    ]))


def interactive_test():
    argspec = ArgSpec(EXAMPLE_SPECSTRING, 'example_command')
    print(argspec.help)
    while True:
        uinput = input(f'\n{argspec.name} >> ')
        if uinput == 'q':
            quit()
        elif uinput == 'h':
            print(argspec.help)
        elif uinput == 'hv':
            print(argspec.help_verbose)
        else:
            try:
                print(f'\t\t{argspec.spec}')
                parsed = argspec.parse(uinput)
                print('\n___ parse() ___')
                for p in parsed:
                    print(p)
                print('\n___ dict_from_parsed() ___')
                d = argspec.dict_from_parsed(*parsed)
                print(',\n'.join(f'{k}={repr(v)}' for k, v in d.items()))
                print('\n___ parse_and_call() ___')
                argspec.parse_and_call(uinput, __func)
                print('___')
            except ArgParseError as e:
                print(e.args[0])
                print(argspec.spec)


EXAMPLE_SPECSTRING = """ArgSpec v.__
Description of the example command in one line.

This is the long-form description of the command, a more verbose description that can have multiple, interspersed lines. Only the first line is used for the one-line description and all others until the "___" line are part of the verbose description.


### Defining the argspec

A command can specify as many arguments of any type except for * and ** arguments, which must have at most one of each. This example command specifically takes one of each type of argument.

The requirements for an argspec are as follows:
1. Arguments are ordered by type, such that you have in order: positionals, optional positionals, remaining positionals, keys, remaining keys
2. There is no more than one of each: remaining positionals and remaining keys
3. There is a line with nothing but "___" (three underscores) between the descriptions and the argument specs
4. Argument names start with alphabetic characters
5. Positional arguments are specified with a space-delimited (" ") name and description
6. Key arguments are specified with a space-delimited (" ") flag, name, and description

The very first line of the spec string may start with "ArgSpec", if so it the first line will be ignored.

Note that although variable names are printed in caps, they are handled in lower case using str.lower() method, dashes replaced with underscores using str.replace().


### Parsing with the argspec with Argspec.parse(args_string)

An ArgParseError will be raised during parsing if any of the following occurs:
- We receive too few positionals
- We receive too many positionals (if *NAME not specified)
- We lack non-optional key arguments
- We receive unexpected key arguments (if **NAME not specified)

Any key argument parsed without a corresponding value will be simply given a value of True. Otherwise, values are parsed as numbers (if possible) otherwise as strings. Only in the case of specifying **NAME, unexpected key arguments will take a single value if the flag is used with "-" and will take a sequence of values if the flag is used with "--".

When parsing, we will resolve the following:
1. tuple of positional arguments (at least as long as required)
2. tuple of extra positional arguments (empty if *NAME not specified)
3. dictionary of key arguments (with keys corresponding to the NAME)
4. dictionary of extra key arguments with keys corresponding to the NAME (empty if **NAME not specified)

The following example input passed to the parse() method:
`test test2 test3 test4 -sign foobar --force -u 42 69 -random_key --fizzbuzz -1 -2 negative-fizz -3 negative-buzz`

Returns a tuple with the following values:
('test', 'test2')
('test3', 'test4')
{'signature': 'foobar', 'force': True, 'set_upstream': (42, 69)}
{'random_key': (), 'fizzbuzz': (-1, -2, 'negative-fizz', -3, 'negative-buzz')}

### Using the parsed arguments with Argspec.parse_and_call(args_string, func)

The method parse_and_call() will first parse the arguments using parse(), convert the result to using dict_from_parsed(), and then call the func with using the dictionary as keyword arguments.

Each value will be assigned a keyword argument name, based on the NAME.

It should be expected in this example that these arguments will be passed to a signature that looks like this:
`func(branch, refspec, signature, set_upstream, repository=None, force=False, tags=None, **options)`

Note that the required parameters come before the optional parameters regardless of order in the spec, since optional parameters must have a default value and must be specified last as per by python's function definitions (https://docs.python.org/3/reference/compound_stmts.html#function-definitions).

Using the same example input from above, the final call will look like this:
func(
branch='test',
repository='test2',
refspec=('test3', 'test4'),
signature='foobar',
force=True,
set_upstream=(42, 69),
random_key=(),
fizzbuzz=(-1, -2, 'negative-fizz', -3, 'negative-buzz'),
)

There is no further type checking, so a function using this argspec is expected to do any further required checks and raise an ArgParseError if they fail.

___

BRANCH Description of first positional argument
+REPOSITORY Description of optional second positional argument
*REFSPEC Description of remaining optional positional arguments
-sign SIGNATURE Description of key argument
-*u SET-UPSTREAM Description of key argument taking a list of values
-+force FORCE Description of optional key argument
-+*tags TAGS Description of optional key argument taking a list of values
**OPTIONS Description of remaining optional key arguments
"""


if __name__ == '__main__':
    interactive_test()
