from copy import copy
from math import isclose

import datetime
from pygeodesy.ellipsoidalVincenty import LatLon


def triple_iterator(lst):
    """Create iterator with three values. E.g.: current, plus1, plus2 in a for loop"""

    a = iter(lst)
    b = copy(a)
    c = copy(a)

    next(b, None)
    next(c, None)
    next(c, None)
    return zip(a, b, c)


def calculate_distance(fix1, fix2):
    loc1_lat_lon = LatLon(fix1['lat'], fix1['lon'])
    loc2_lat_lon = LatLon(fix2['lat'], fix2['lon'])

    # pygeodesy raises exception when same locations are used
    if isclose(fix1['lat'], fix2['lat']) and isclose(fix1['lon'], fix2['lon']):
        return 0

    return loc1_lat_lon.distanceTo(loc2_lat_lon)


def calculate_bearing_change(fix_minus2, fix_minus1, fix):
    """
    Return bearing change in degrees between -180 and +180
    Return 0 when two of the of the fixes are the same.
    :param fix_minus2: 
    :param fix_minus1: 
    :param fix: 
    :return: 
    """

    # pygeodesy raises an exception when same locations are used
    if (isclose(fix_minus1['lat'], fix_minus2['lat']) and isclose(fix_minus1['lon'], fix_minus2['lon']) or
            isclose(fix_minus1['lat'], fix['lat']) and isclose(fix_minus1['lon'], fix['lon']) or
            isclose(fix_minus2['lat'], fix['lat']) and isclose(fix_minus2['lon'], fix['lon'])):
        return 0

    loc1_lat_lon = LatLon(fix_minus2['lat'], fix_minus2['lon'])
    loc2_lat_lon = LatLon(fix_minus1['lat'], fix_minus1['lon'])
    loc3_lat_lon = LatLon(fix['lat'], fix['lon'])

    bearing1 = loc1_lat_lon.initialBearingTo(loc2_lat_lon)
    bearing2 = loc2_lat_lon.initialBearingTo(loc3_lat_lon)

    # always return difference between -180 and +180 degrees
    difference = bearing2 - bearing1
    if -180 < difference < 180:
        return difference
    elif difference <= -180:
        return difference + 360
    elif difference >= 180:
        return difference - 360


def seconds_time_difference(time1: datetime.time, time2: datetime.time):
    """
    Determines the time difference between to datetime.time instances, mocking the operation time2 - time1
    It is assumed that both take place at the same day.
    :param time1: 
    :param time2: 
    :return: 
    """

    today = datetime.date.today()
    time_diff = datetime.datetime.combine(today, time2) - datetime.datetime.combine(today, time1)
    return time_diff.total_seconds()
