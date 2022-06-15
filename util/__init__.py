from loguru import logger
import os, sys, traceback
import numpy as np
from prompt_toolkit.formatted_text import HTML

RNG = np.random.default_rng()
EPSILON = 10**-10
RADIANS_IN_DEGREES = 57.29577951308
GOOGOL = 10**100

CELESTIAL_NAMES = ['Alkurhah', 'Alterf', 'Wezn', 'Aldhibah', 'Anser', 'Tyl', 'Caph', 'Alderamin', 'Cursa', 'Dubhe', 'Sirius', 'Baten kaitos', 'Ras elased australis', 'Atlas', 'Zavijah', 'Deneb kaitos shemali', 'Kitalpha', 'Mirphak', 'Asellus tertius', 'Menkar', 'Dschubba', 'Alnitak', 'Mebsuta', 'Ascella', 'Nash', 'Marfic', 'Naos', 'Graffias', 'Algenib', 'Algol', 'Canopus', 'Maasym', 'Phad', 'Asellus borealis', 'Asellus secondus', 'Saiph', 'Ain al rami', 'Alsuhail', 'Gorgonea quarta', 'Arkab prior', 'Sarin', 'Alzirr', 'Tania australis', 'Sadalsuud', 'Tabit', 'Murzim', 'Nair al saif', 'Polaris australis', 'Nodus secundus', 'Cor caroli', 'Brachium', 'Mesarthim', 'Sualocin', 'Polaris', 'Muliphen', 'Skat', 'Fum al samakah', 'Alphard', 'Alathfar', 'Alchiba', 'Wasat', 'Hyadum I', 'Capella', 'Alfecca meridiana', 'Gorgonea secunda', 'Cebalrai', 'Alsafi', 'Diadem', 'Rigel kentaurus', 'Menkalinan', 'Albaldah', 'Torcularis septentrionalis', 'Hamal', 'Nunki', 'Azmidiske', 'Miram', 'Alioth', 'Ruchba', 'Tania borealis', 'Acubens', 'Sol', 'Zibal', 'Gianfar', 'Turais', 'Muscida', 'Rastaban', 'Prima giedi', 'Merope', 'Deneb dulfim', 'Agena', 'Situla', 'Algorab', 'Hyadum II', 'Matar', 'Suhail al muhlif', 'Asellus australis', 'Kajam', 'Adhil', 'Pherkad', 'Maia', 'Zaniah', 'Sabik', 'Kaus australis', 'Minkar', 'Gienah ghurab', 'Keid', 'Etamin', 'Subra', 'Menkent', 'Altair', 'Alhena', 'Hadar', 'Menkib', 'Ed asich', 'Sharatan', 'Alfirk', 'Alcor', 'Arneb', 'Secunda giedi', 'Gienah cygni', 'Diphda', 'Zaurak', 'Kaus meridionalis', 'Rukbat', 'Mintaka', 'Dsiban', 'Alphekka', 'Betelgeuse', 'Yildun', 'Alnair', 'Marfik', 'Menkar', 'Furud', 'Syrma', 'Spica', 'Achird', 'Adhafera', 'Taygeta', 'Adara', 'Arcturus', 'Albireo', 'Porrima', 'Sceptrum', 'Almaak', 'Avior', 'Kaffaljidhma', 'Mira', 'Alcyone', 'Wezen', 'Tejat posterior', 'Metallah', 'Marfak', 'Sheliak', 'Alsciaukat', 'Acamar', 'Deneb', 'Alkaid', 'Arkab posterior', 'Auva', 'Alkalurops', 'Antares', 'Izar', 'Yed prior', 'Gomeisa', 'Pherkad minor', 'Ankaa', 'Deneb algedi', 'Aladfar', 'Asellus primus', 'Bellatrix', 'Achernar', 'Mekbuda', 'Rasalhague', 'Azelfafage', 'Beid', 'Mizar', 'Scheat', 'Sham', 'Aldebaran', 'Shedir', 'Sadalmelik', 'Alniyat', 'Ain', 'Chara', 'Celaeno', 'Castor', 'Alula borealis', 'Al anz', 'Botein', 'Propus', 'Lesath', 'Arrakis', 'Azha', 'Alrisha', 'Tegmen', 'Enif', 'Unukalhai', 'Thabit', 'Peacock', 'Haedi', 'Kraz', 'Trappist', 'Rigel', 'Hoedus II', 'Altarf', 'Kornephoros', 'Nashira', 'Nusakan', 'Merga', 'Becrux', 'Alnilam', 'Grafias', 'Pleione', 'Merak', 'Acrux', 'Marfak', 'Grumium', 'Alpheratz', 'Meissa', 'Talitha', 'Terebellum', 'Kuma', 'Alkes', 'Dabih', 'Kocab', 'Gorgonea tertia', 'Elnath', 'Homam', 'Atik', 'Miaplacidus', 'Nihal', 'Ruchbah', 'Denebola', 'Shaula', 'Fomalhaut', 'Heze', 'Markab', 'Sargas', 'Deneb el okab', 'Garnet', 'Fornacis', 'Ancha', 'Rijl al awwa', 'Procyon', 'Thuban', 'Rasalgethi', 'Sadr', 'Yed posterior', 'Megrez', 'Alshat', 'Kaus borealis', 'Sulafat', 'Alya', 'Zosma', 'Dheneb', 'Phaet', 'Pollux', 'Rotanev', 'Vindemiatrix', 'Hassaleh', 'Mirach', 'Salm', 'Angetenar', 'Jabbah', 'Chort', 'Sadalachbia', 'Alnath', 'Sterope II', 'Asterope', 'Aludra', 'Theemim', 'Rana', 'Algieba', 'Tarazed', 'Gacrux', 'Electra', 'Vega', 'Baham', 'Nekkar', 'Ras elased borealis', 'Regulus', 'Alula australis', 'Albali', 'Seginus', 'Praecipua', 'Mufrid', 'Alrai', 'Alshain']


COLOR_HEXES = {
    'black': '#000000',
    'white': '#ffffff',
    'gray': '#aaaaaa',
    'red': '#ff0000',
    'green': '#00ff00',
    'blue': '#4444ff',
    'navy': '#0000ff',
    'yellow': '#ffff00',
    'orange': '#ffbb00',
    'brown': '#bb5500',
    'cyan': '#00ffff',
    'magenta': '#ff00ff',
    'pink': '#ff00aa',
    'purple': '#ff00ff',
}
COLORS = list(COLOR_HEXES.keys())
OBJECT_COLORS = COLORS[3:]
STYLE = {
    'code': '#44ff00 italic',
    'h1': '#0044ff bold underline bg:#ffffff',
    'h2': '#ffffff bold underline bg:#000055',
    'h3': f'#ffbb00 bold underline',
    'map': 'bg:#00001a',
    'bar': 'bg:#1a0000',
    'highlight': '#000000 bg:#ffffff',
    'darkbg': 'bg:#000055',
    **COLOR_HEXES,
}
__TEST_FOR_INDEXING = tuple()


def file_dump(file, d, clear=True):
    with open(file, 'w' if clear else 'a') as f:
        f.write(d)


def file_load(file):
    with open(file, 'r') as f:
        d = f.read()
    return d


def tag(tag, s):
    return f'<{tag}>{s}</{tag}>'


def escape_html(s):
    r = str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return r


def is_malformed_html(s):
    s = str(s)
    try:
        h = HTML(s)
    except Exception as e:
        return e.lineno, e.code
    return False


def escape_if_malformed(s, indicate_escaped=True):
    s = str(s)
    mal = is_malformed_html(s)
    if mal:
        if indicate_escaped:
            line, col = mal
            has_nl = '\n' in s
            nl = '\n' if has_nl else ''
            return escape_html(f'<MALFORMED @ line {line} col {col}>{nl}{s}{nl}</MALFORMED>')
        return escape_html(s)
    return s


def restart_script():
    os.execl(sys.executable, sys.executable, *sys.argv)


def window_size():
    return os.get_terminal_size()


def format_latlong(v, rounding=1):
    return ', '.join(f"{f'{round(_, rounding)}°':>7}" for _ in v)


def format_vector(v):
    return ','.join(f'{f"{_:.3e}":>10}' for _ in v)


def format_exc(e):
    return ''.join(str(_) for _ in traceback.format_exception(*sys.exc_info()))


def format_exc_short(e):
    return traceback.format_exception(*sys.exc_info())[-1]


def adjustable_sigmoid(x, k):
    assert 0 <= x <= 1
    assert -1 < k < 1
    if x <= 0.5:
        nom = 2*k*x - 2*x
        denom = 4*k*x - k - 1
        r = nom/denom * 0.5
        return min(0.5, r)
    else:
        nom = -2*k*x - 2*x + k + 1
        denom = -4*k*x + 3*k - 1
        r = nom/denom * 0.5 + 0.5
        return max(0.5, r)


def try_number(v):
    try:
        r = float(v)
        if r == int(r):
            return int(r)
        return r
    except ValueError as e:
        return v


def is_index(n):
    try:
        try:
            __TEST_FOR_INDEXING[n]
        except TypeError:
            return False
    except IndexError:
        return True
    raise RuntimeError(f'Unknown error with is_index for variable: {n} {type(n)} {repr(n)}')


def is_number(n):
    try:
        n < 0
        n == 0
        n + 1
    except:
        return False
    return True
