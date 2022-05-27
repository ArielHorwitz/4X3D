from loguru import logger
import numpy as np
from prompt_toolkit import print_formatted_text as print

rng = np.random.default_rng()
# CELESTIAL_NAMES = ['Acamar', 'Achernar', 'Achird', 'Acrux', 'Acubens', 'Adara', 'Adhafera', 'Adhil', 'Agena', 'Ain al rami', 'Ain', 'Al anz', 'Aladfar', 'Alathfar', 'Albaldah', 'Albali', 'Albireo', 'Alchiba', 'Alcor', 'Alcyone', 'Aldebaran', 'Alderamin', 'Aldhibah', 'Alfecca meridiana', 'Alfirk', 'Algenib', 'Algieba', 'Algol', 'Algorab', 'Alhena', 'Alioth', 'Alkaid', 'Alkalurops', 'Alkes', 'Alkurhah', 'Almaak', 'Alnair', 'Alnath', 'Alnilam', 'Alnitak', 'Alniyat', 'Alphard', 'Alphekka', 'Alpheratz', 'Alrai', 'Alrisha', 'Alsafi', 'Alsciaukat', 'Alshain', 'Alshat', 'Alsuhail', 'Altair', 'Altarf', 'Alterf', 'Aludra', 'Alula australis', 'Alula borealis', 'Alya', 'Alzirr', 'Ancha', 'Angetenar', 'Ankaa', 'Anser', 'Antares', 'Arcturus', 'Arkab posterior', 'Arkab prior', 'Arneb', 'Arrakis', 'Ascella', 'Asellus australis', 'Asellus borealis', 'Asellus primus', 'Asellus secondus', 'Asellus tertius', 'Asterope', 'Atik', 'Atlas', 'Auva', 'Avior', 'Azelfafage', 'Azha', 'Azmidiske', 'Baham', 'Baten kaitos', 'Becrux', 'Beid', 'Bellatrix', 'Betelgeuse', 'Botein', 'Brachium', 'Canopus', 'Capella', 'Caph', 'Castor', 'Cebalrai', 'Celaeno', 'Chara', 'Chort', 'Cor caroli', 'Cursa', 'Dabih', 'Deneb algedi', 'Deneb dulfim', 'Deneb el okab', 'Deneb kaitos shemali', 'Deneb', 'Denebola', 'Dheneb', 'Diadem', 'Diphda', 'Dschubba', 'Dsiban', 'Dubhe', 'Ed asich', 'Electra', 'Elnath', 'Enif', 'Etamin', 'Fomalhaut', 'Fornacis', 'Fum al samakah', 'Furud', 'Gacrux', 'Gianfar', 'Gienah cygni', 'Gienah ghurab', 'Gomeisa', 'Gorgonea quarta', 'Gorgonea secunda', 'Gorgonea tertia', 'Graffias', 'Grafias', 'Grumium', 'Hadar', 'Haedi', 'Hamal', 'Hassaleh', 'Garnet', 'Heze', 'Hoedus II', 'Homam', 'Hyadum I', 'Hyadum II', 'Izar', 'Jabbah', 'Kaffaljidhma', 'Kajam', 'Kaus australis', 'Kaus borealis', 'Kaus meridionalis', 'Keid', 'Kitalpha', 'Kocab', 'Kornephoros', 'Kraz', 'Kuma', 'Lesath', 'Maasym', 'Maia', 'Marfak', 'Marfak', 'Marfic', 'Marfik', 'Markab', 'Matar', 'Mebsuta', 'Megrez', 'Meissa', 'Mekbuda', 'Menkalinan', 'Menkar', 'Menkar', 'Menkent', 'Menkib', 'Merak', 'Merga', 'Merope', 'Mesarthim', 'Metallah', 'Miaplacidus', 'Minkar', 'Mintaka', 'Mira', 'Mirach', 'Miram', 'Mirphak', 'Mizar', 'Mufrid', 'Muliphen', 'Murzim', 'Muscida', 'Nair al saif', 'Naos', 'Nash', 'Nashira', 'Nekkar', 'Nihal', 'Nodus secundus', 'Nunki', 'Nusakan', 'Peacock', 'Phad', 'Phaet', 'Pherkad minor', 'Pherkad', 'Pleione', 'Polaris australis', 'Polaris', 'Pollux', 'Porrima', 'Praecipua', 'Prima giedi', 'Procyon', 'Propus', 'Rana', 'Ras elased australis', 'Ras elased borealis', 'Rasalgethi', 'Rasalhague', 'Rastaban', 'Regulus', 'Rigel kentaurus', 'Rigel', 'Rijl al awwa', 'Rotanev', 'Ruchba', 'Ruchbah', 'Rukbat', 'Sabik', 'Sadalachbia', 'Sadalmelik', 'Sadalsuud', 'Sadr', 'Saiph', 'Salm', 'Sargas', 'Sarin', 'Sceptrum', 'Scheat', 'Secunda giedi', 'Segin', 'Seginus', 'Sham', 'Sharatan', 'Shaula', 'Shedir', 'Sheliak', 'Sirius', 'Situla', 'Skat', 'Sol', 'Spica', 'Sterope II', 'Sualocin', 'Subra', 'Suhail al muhlif', 'Sulafat', 'Syrma', 'Tabit', 'Talitha', 'Tania australis', 'Tania borealis', 'Tarazed', 'Taygeta', 'Tegmen', 'Tejat posterior', 'Terebellum', 'Thabit', 'Theemim', 'Thuban', 'Torcularis septentrionalis', 'Trappist', 'Turais', 'Tyl', 'Unukalhai', 'Vega', 'Vindemiatrix', 'Wasat', 'Wezen', 'Wezn', 'Yed posterior', 'Yed prior', 'Yildun', 'Zaniah', 'Zaurak', 'Zavijah', 'Zibal', 'Zosma']
CELESTIAL_NAMES = ['Me', 'Alkurhah', 'Alterf', 'Wezn', 'Aldhibah', 'Anser', 'Tyl', 'Caph', 'Alderamin', 'Cursa', 'Dubhe', 'Sirius', 'Baten kaitos', 'Ras elased australis', 'Atlas', 'Zavijah', 'Deneb kaitos shemali', 'Kitalpha', 'Mirphak', 'Asellus tertius', 'Menkar', 'Dschubba', 'Alnitak', 'Mebsuta', 'Ascella', 'Nash', 'Marfic', 'Naos', 'Graffias', 'Algenib', 'Algol', 'Canopus', 'Maasym', 'Phad', 'Asellus borealis', 'Asellus secondus', 'Saiph', 'Ain al rami', 'Alsuhail', 'Gorgonea quarta', 'Arkab prior', 'Sarin', 'Alzirr', 'Tania australis', 'Sadalsuud', 'Tabit', 'Murzim', 'Nair al saif', 'Polaris australis', 'Nodus secundus', 'Cor caroli', 'Brachium', 'Mesarthim', 'Sualocin', 'Polaris', 'Muliphen', 'Skat', 'Fum al samakah', 'Alphard', 'Alathfar', 'Alchiba', 'Wasat', 'Hyadum I', 'Capella', 'Alfecca meridiana', 'Gorgonea secunda', 'Cebalrai', 'Alsafi', 'Diadem', 'Rigel kentaurus', 'Menkalinan', 'Albaldah', 'Torcularis septentrionalis', 'Hamal', 'Nunki', 'Azmidiske', 'Miram', 'Alioth', 'Ruchba', 'Tania borealis', 'Acubens', 'Sol', 'Zibal', 'Gianfar', 'Turais', 'Muscida', 'Rastaban', 'Prima giedi', 'Merope', 'Deneb dulfim', 'Agena', 'Situla', 'Algorab', 'Hyadum II', 'Matar', 'Suhail al muhlif', 'Asellus australis', 'Kajam', 'Adhil', 'Pherkad', 'Maia', 'Zaniah', 'Sabik', 'Kaus australis', 'Minkar', 'Gienah ghurab', 'Keid', 'Etamin', 'Subra', 'Menkent', 'Altair', 'Alhena', 'Hadar', 'Menkib', 'Ed asich', 'Sharatan', 'Alfirk', 'Alcor', 'Arneb', 'Secunda giedi', 'Gienah cygni', 'Diphda', 'Zaurak', 'Kaus meridionalis', 'Rukbat', 'Mintaka', 'Dsiban', 'Alphekka', 'Betelgeuse', 'Yildun', 'Alnair', 'Marfik', 'Menkar', 'Furud', 'Syrma', 'Spica', 'Achird', 'Adhafera', 'Taygeta', 'Adara', 'Arcturus', 'Albireo', 'Porrima', 'Sceptrum', 'Almaak', 'Avior', 'Kaffaljidhma', 'Mira', 'Alcyone', 'Wezen', 'Tejat posterior', 'Metallah', 'Marfak', 'Sheliak', 'Alsciaukat', 'Acamar', 'Deneb', 'Alkaid', 'Arkab posterior', 'Auva', 'Alkalurops', 'Antares', 'Izar', 'Yed prior', 'Gomeisa', 'Pherkad minor', 'Ankaa', 'Deneb algedi', 'Aladfar', 'Asellus primus', 'Bellatrix', 'Achernar', 'Mekbuda', 'Rasalhague', 'Azelfafage', 'Beid', 'Mizar', 'Scheat', 'Sham', 'Aldebaran', 'Shedir', 'Sadalmelik', 'Alniyat', 'Ain', 'Chara', 'Celaeno', 'Castor', 'Alula borealis', 'Al anz', 'Botein', 'Propus', 'Lesath', 'Arrakis', 'Azha', 'Alrisha', 'Tegmen', 'Enif', 'Unukalhai', 'Thabit', 'Peacock', 'Haedi', 'Kraz', 'Trappist', 'Rigel', 'Hoedus II', 'Altarf', 'Kornephoros', 'Nashira', 'Nusakan', 'Merga', 'Becrux', 'Alnilam', 'Grafias', 'Pleione', 'Merak', 'Acrux', 'Marfak', 'Grumium', 'Alpheratz', 'Meissa', 'Talitha', 'Terebellum', 'Kuma', 'Alkes', 'Dabih', 'Kocab', 'Gorgonea tertia', 'Elnath', 'Homam', 'Atik', 'Miaplacidus', 'Nihal', 'Ruchbah', 'Denebola', 'Shaula', 'Fomalhaut', 'Heze', 'Markab', 'Sargas', 'Deneb el okab', 'Garnet', 'Fornacis', 'Ancha', 'Rijl al awwa', 'Procyon', 'Thuban', 'Rasalgethi', 'Sadr', 'Yed posterior', 'Megrez', 'Alshat', 'Kaus borealis', 'Sulafat', 'Alya', 'Zosma', 'Dheneb', 'Phaet', 'Pollux', 'Rotanev', 'Vindemiatrix', 'Hassaleh', 'Mirach', 'Salm', 'Angetenar', 'Jabbah', 'Chort', 'Sadalachbia', 'Alnath', 'Sterope II', 'Asterope', 'Aludra', 'Theemim', 'Rana', 'Algieba', 'Tarazed', 'Gacrux', 'Electra', 'Vega', 'Baham', 'Nekkar', 'Ras elased borealis', 'Regulus', 'Alula australis', 'Albali', 'Seginus', 'Praecipua', 'Mufrid', 'Alrai', 'Alshain']


class Universe:
    def __init__(self, entity_count=20):
        self.tick = 0
        self.entity_count = entity_count
        self.gravity_constant = 10**-8
        self.positions = np.zeros((entity_count, 3), dtype=np.float64)
        self.velocities = np.zeros((entity_count, 3), dtype=np.float64)
        graviton_count = np.round(entity_count*0.1)
        graviton_count = 2
        self.gravitons = np.asarray(np.arange(graviton_count) + 1, dtype=np.int32)
        self.graviton_mass = np.arange(len(self.gravitons)) * 10 + 100
        self.randomize_pos()
        self.randomize_vel()

    @property
    def my_pos(self):
        return self.positions[0]

    @property
    def my_vel(self):
        return self.velocities[0]

    def move(self, d):
        self.positions[0] += d

    def fly(self, dv):
        self.velocities[0] += dv

    def break_move(self):
        self.velocities[0] = 0

    def match_velocities(self, a, b):
        self.velocities[a] = self.velocities[b]

    def match_positions(self, a, b):
        self.positions[a] = self.positions[b]

    def simulate(self, ticks=1):
        assert self.positions.dtype == self.velocities.dtype == np.float64
        self.tick += int(ticks)
        self.apply_gravity(ticks)
        self.positions += self.velocities * ticks / 1000

    def apply_gravity(self, ticks):
        # Find gravity vectors (between objects and gravity sources)
        graviton_pos = self.positions[self.gravitons]
        grav_vectors = graviton_pos - self.positions[:, None, :]
        # Consider the square root of their distance
        grav_vector_dist = np.linalg.norm(grav_vectors, axis=-1)[:, :, None]
        inverse_square_dist = np.sqrt(grav_vector_dist)
        # Get the unit vector of the gravity vectors
        grav_vectors_normalized = grav_vectors / grav_vector_dist
        np.nan_to_num(grav_vectors_normalized, copy=False)
        # The delta V should consider the inverse square law and the mass of the gravitation source
        force_vectors = grav_vectors_normalized * inverse_square_dist * self.graviton_mass[None, :, None]
        # Combine forces from all gravity sources to one vector per object
        force_vectors = force_vectors.sum(axis=1)
        # Multiply by the gravity constant and number of ticks to simulate
        force_vectors *= self.gravity_constant * ticks
        # Apply the gravitational force
        self.velocities[1:] += force_vectors[1:]

    def randomize_pos(self):
        self.positions += (rng.random((self.entity_count, 3)) * 20 - 10)
        self.positions[0] = 0

    def randomize_vel(self):
        self.velocities += (rng.random((self.entity_count, 3)) * 2 - 1)
        self.break_move()

    def center_vel(self):
        v = np.linalg.norm(self.positions, axis=-1)
        mask = v != 0
        d = -self.positions[mask] / v[mask, None]
        self.velocities[mask] = d

    def flip_vel(self):
        self.velocities = -self.velocities

    def reset(self):
        self.positions = np.zeros((self.entity_count, 3), dtype=np.float64)
        self.velocities = np.zeros((self.entity_count, 3), dtype=np.float64)
