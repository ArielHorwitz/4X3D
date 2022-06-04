import math
import numpy as np

RADIANS_IN_DEGREES = 57.296
GOOGOL = 10**100


def latlong_single(vector):
    """
    Given an observer at the origin, gives the longitude and latitude
    of a vector projected onto a sphere around the origin/observer,
    such that the 0°, 0° corresponds to a vector at (1, 0, 0) and 45°, 45°
    corresponds to a vector at (1, -1, 1).

    A simpler way of conceptualizing this is considering the observer at
    the origin and using the right hand rule, looking straight at the x+
    axis with the y+ axis to their left and the z+ axis atop them. We
    find the angles to rotate clockwise and pitch up in order to look at
    the vector.
    """
    def pad_plank_length(scalar):
        if scalar < 0:
            return min(scalar, 10**-20)
        return max(scalar, 10**-20)

    magnitude = np.linalg.norm(vector)
    if magnitude == 0:
        return 0, 0

    theta = math.atan(vector[1] / pad_plank_length(vector[0]))
    if vector[0] < 0:
        theta += math.pi
    long = (theta * RADIANS_IN_DEGREES) * -1

    phi = math.asin(vector[2] / pad_plank_length(magnitude))
    lat = (phi * RADIANS_IN_DEGREES)
    return long, lat


def latlong(vectors):
    """
    Given an observer at the origin, gives the longitude and latitude
    of vectors projected onto a sphere around the origin/observer,
    such that the 0°, 0° corresponds to a vector at (1, 0, 0) and 45°, 45°
    corresponds to a vector at (1, -1, 1).

    A simpler way of conceptualizing this is considering the observer at
    the origin and using the right hand rule, looking straight at the x+
    axis with the y+ axis to their left and the z+ axis atop them. We
    find the angles to rotate clockwise and pitch up in order to look at
    the vector.
    """
    magnitude = np.linalg.norm(vectors, axis=-1)
    has_mag = magnitude > 0
    has_x = vectors[:, 0] != 0  # Avoid dividing by zero
    has_y = vectors[:, 1] != 0
    fix_theta = ~has_x & has_y  # Compensate for vectors with y component but no x

    long = np.zeros(len(vectors), dtype=np.float64)
    theta = np.arctan(vectors[has_x, 1] / vectors[has_x, 0])
    theta[vectors[has_x, 0] < 0] += math.pi
    long[has_x] = theta * RADIANS_IN_DEGREES * -1
    long[fix_theta] = vectors[fix_theta, 1] / np.abs(vectors[fix_theta, 1]) * 90

    lat = np.zeros(len(vectors), dtype=np.float64)
    phi = np.arcsin(vectors[has_mag, 2] / magnitude[has_mag])
    lat[has_mag] = phi * RADIANS_IN_DEGREES

    r = np.stack((long, lat), axis=1)
    return r


def unit_vectors():
    return np.asarray([
        [GOOGOL, 0, 0],
        [-GOOGOL, 0, 0],
        [0, GOOGOL, 0],
        [0, -GOOGOL, 0],
        [0, 0, GOOGOL],
        [0, 0, -GOOGOL],
    ], dtype=np.float64)
