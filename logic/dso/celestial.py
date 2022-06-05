
from logic.dso.dso import DeepSpaceObject


class CelestialObject(DeepSpaceObject):
    pass


class SMBH(CelestialObject):
    type_name = 'SMBH'
    icon = '■'
    color = 'grey'

class Star(CelestialObject):
    type_name = 'star'
    icon = '¤'
    color = 'white'

class Rock(CelestialObject):
    type_name = 'rock'
    icon = '•'
    color = 'brown'
