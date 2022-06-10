import numpy as np

RNG = np.random.default_rng()
EPSILON = 10**-10
CELESTIAL_NAMES = ['Alkurhah', 'Alterf', 'Wezn', 'Aldhibah', 'Anser', 'Tyl', 'Caph', 'Alderamin', 'Cursa', 'Dubhe', 'Sirius', 'Baten kaitos', 'Ras elased australis', 'Atlas', 'Zavijah', 'Deneb kaitos shemali', 'Kitalpha', 'Mirphak', 'Asellus tertius', 'Menkar', 'Dschubba', 'Alnitak', 'Mebsuta', 'Ascella', 'Nash', 'Marfic', 'Naos', 'Graffias', 'Algenib', 'Algol', 'Canopus', 'Maasym', 'Phad', 'Asellus borealis', 'Asellus secondus', 'Saiph', 'Ain al rami', 'Alsuhail', 'Gorgonea quarta', 'Arkab prior', 'Sarin', 'Alzirr', 'Tania australis', 'Sadalsuud', 'Tabit', 'Murzim', 'Nair al saif', 'Polaris australis', 'Nodus secundus', 'Cor caroli', 'Brachium', 'Mesarthim', 'Sualocin', 'Polaris', 'Muliphen', 'Skat', 'Fum al samakah', 'Alphard', 'Alathfar', 'Alchiba', 'Wasat', 'Hyadum I', 'Capella', 'Alfecca meridiana', 'Gorgonea secunda', 'Cebalrai', 'Alsafi', 'Diadem', 'Rigel kentaurus', 'Menkalinan', 'Albaldah', 'Torcularis septentrionalis', 'Hamal', 'Nunki', 'Azmidiske', 'Miram', 'Alioth', 'Ruchba', 'Tania borealis', 'Acubens', 'Sol', 'Zibal', 'Gianfar', 'Turais', 'Muscida', 'Rastaban', 'Prima giedi', 'Merope', 'Deneb dulfim', 'Agena', 'Situla', 'Algorab', 'Hyadum II', 'Matar', 'Suhail al muhlif', 'Asellus australis', 'Kajam', 'Adhil', 'Pherkad', 'Maia', 'Zaniah', 'Sabik', 'Kaus australis', 'Minkar', 'Gienah ghurab', 'Keid', 'Etamin', 'Subra', 'Menkent', 'Altair', 'Alhena', 'Hadar', 'Menkib', 'Ed asich', 'Sharatan', 'Alfirk', 'Alcor', 'Arneb', 'Secunda giedi', 'Gienah cygni', 'Diphda', 'Zaurak', 'Kaus meridionalis', 'Rukbat', 'Mintaka', 'Dsiban', 'Alphekka', 'Betelgeuse', 'Yildun', 'Alnair', 'Marfik', 'Menkar', 'Furud', 'Syrma', 'Spica', 'Achird', 'Adhafera', 'Taygeta', 'Adara', 'Arcturus', 'Albireo', 'Porrima', 'Sceptrum', 'Almaak', 'Avior', 'Kaffaljidhma', 'Mira', 'Alcyone', 'Wezen', 'Tejat posterior', 'Metallah', 'Marfak', 'Sheliak', 'Alsciaukat', 'Acamar', 'Deneb', 'Alkaid', 'Arkab posterior', 'Auva', 'Alkalurops', 'Antares', 'Izar', 'Yed prior', 'Gomeisa', 'Pherkad minor', 'Ankaa', 'Deneb algedi', 'Aladfar', 'Asellus primus', 'Bellatrix', 'Achernar', 'Mekbuda', 'Rasalhague', 'Azelfafage', 'Beid', 'Mizar', 'Scheat', 'Sham', 'Aldebaran', 'Shedir', 'Sadalmelik', 'Alniyat', 'Ain', 'Chara', 'Celaeno', 'Castor', 'Alula borealis', 'Al anz', 'Botein', 'Propus', 'Lesath', 'Arrakis', 'Azha', 'Alrisha', 'Tegmen', 'Enif', 'Unukalhai', 'Thabit', 'Peacock', 'Haedi', 'Kraz', 'Trappist', 'Rigel', 'Hoedus II', 'Altarf', 'Kornephoros', 'Nashira', 'Nusakan', 'Merga', 'Becrux', 'Alnilam', 'Grafias', 'Pleione', 'Merak', 'Acrux', 'Marfak', 'Grumium', 'Alpheratz', 'Meissa', 'Talitha', 'Terebellum', 'Kuma', 'Alkes', 'Dabih', 'Kocab', 'Gorgonea tertia', 'Elnath', 'Homam', 'Atik', 'Miaplacidus', 'Nihal', 'Ruchbah', 'Denebola', 'Shaula', 'Fomalhaut', 'Heze', 'Markab', 'Sargas', 'Deneb el okab', 'Garnet', 'Fornacis', 'Ancha', 'Rijl al awwa', 'Procyon', 'Thuban', 'Rasalgethi', 'Sadr', 'Yed posterior', 'Megrez', 'Alshat', 'Kaus borealis', 'Sulafat', 'Alya', 'Zosma', 'Dheneb', 'Phaet', 'Pollux', 'Rotanev', 'Vindemiatrix', 'Hassaleh', 'Mirach', 'Salm', 'Angetenar', 'Jabbah', 'Chort', 'Sadalachbia', 'Alnath', 'Sterope II', 'Asterope', 'Aludra', 'Theemim', 'Rana', 'Algieba', 'Tarazed', 'Gacrux', 'Electra', 'Vega', 'Baham', 'Nekkar', 'Ras elased borealis', 'Regulus', 'Alula australis', 'Albali', 'Seginus', 'Praecipua', 'Mufrid', 'Alrai', 'Alshain']


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

@staticmethod
def resolve_prompt_input(s):
    command, *args = s.split(' ')
    args = [try_number(a) for a in args]
    return command, args

@staticmethod
def try_number(v):
    try:
        r = float(v)
        if r == int(r):
            r = int(r)
        return r
    except ValueError as e:
        return v
