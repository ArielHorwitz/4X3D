
from prompt_toolkit.key_binding import KeyBindings, ConditionalKeyBindings, merge_key_bindings
from prompt_toolkit.filters import Condition


MODS_DECODE = {'c': '^', 's': '+'}
MODS_ENCODE = {v: k for k, v in MODS_DECODE.items()}

KEYS_DECODE = {'c-@': 'space', 'c-m': 'enter', 'c-i': 'tab', 'c-h': 'backspace'}
KEYS_ENCODE = {v: k for k, v in KEYS_DECODE.items()}


def get_keybindings(global_keys, condition, handler):
    globals = KeyBindings()
    for key, callback in global_keys.items():
        @globals.add(encode_keyseq(key), eager=True)
        def handle_(event, callback=callback):
            callback()
    all_kb = KeyBindings()
    @all_kb.add('<any>', eager=True)
    def handle_(event):
        k = event.key_sequence[0].key
        k = 'space' if k == ' ' else k
        key_seq = decode_keyseq(k._value_) if hasattr(k, '_value_') else k
        handler(key_seq)
    all_kb = ConditionalKeyBindings(key_bindings=all_kb, filter=Condition(condition))
    return merge_key_bindings([globals, all_kb])


def decode_keyseq(ks):
    if ks in KEYS_DECODE:
        return KEYS_DECODE[ks]
    parts = ks.split('-')
    if len(parts) > 1:
        key = parts[-1]
        mods = parts[:-1]
        mods = [MODS_DECODE[m] for m in mods]
        return f'{"".join(mods)} {key}'
    return ks


def encode_keyseq(ks):
    if ks in KEYS_ENCODE:
        return KEYS_ENCODE[ks]
    parts = ks.split(' ')
    if len(parts) == 2:
        mods, key = parts
        mods = '-'.join(MODS_ENCODE[m] for m in mods)
        return f'{mods}-{key}'
    return ks
