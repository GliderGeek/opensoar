from copy import copy
from math import isclose, pi, sin, cos, atan2

import datetime
from typing import List

from io import BytesIO
from pygeodesy.ellipsoidalVincenty import LatLon
from aerofiles.igc.writer import Writer


def double_iterator(lst):
    """Create iterator with two values. E.g.: current, plus1 in a for loop"""
    a = iter(lst)
    b = copy(a)

    next(b, None)
    return zip(a, b)


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
    """
    Calculate distance between fix1 and fix2 using WGS84
    :param fix1: b-record from IGC file (dict with keys 'lat' and 'lon')
    :param fix2: b-record from IGC file (dict with keys 'lat' and 'lon')
    :return: distance in m
    """
    loc1_lat_lon = LatLon(fix1['lat'], fix1['lon'])
    loc2_lat_lon = LatLon(fix2['lat'], fix2['lon'])

    # pygeodesy raises exception when same locations are used
    if isclose(fix1['lat'], fix2['lat']) and isclose(fix1['lon'], fix2['lon']):
        return 0

    return loc1_lat_lon.distanceTo(loc2_lat_lon)


def calculate_bearing(fix1, fix2, final_bearing=False):
    """
    Calculate bearing between fix1 and fix. By default the bearing is taking tangent to the great circle at fix1.
    :param final_bearing: switch to True results in taking the tangent at fix2.
    :param fix1: b-record from IGC file (dict with keys 'lat' and 'lon')
    :param fix2: b-record from IGC file (dict with keys 'lat' and 'lon')
    :return: bearing in degrees
    """
    loc1_lat_lon = LatLon(fix1['lat'], fix1['lon'])
    loc2_lat_lon = LatLon(fix2['lat'], fix2['lon'])

    if not final_bearing:
        return loc1_lat_lon.initialBearingTo(loc2_lat_lon)
    else:
        return loc1_lat_lon.finalBearingTo(loc2_lat_lon)


def calculate_bearing_difference(bearing1, bearing2):
    """
    Calculate smallest difference from bearing 1 -> bearing2.
    :param bearing1: start bearing in degrees (0-360)
    :param bearing2: end bearing in degrees (0-360)
    :return: angle between -180 and +180 degrees.
    """
    # always return difference between -180 and +180 degrees
    difference = bearing2 - bearing1
    if -180 < difference < 180:
        return difference
    elif difference <= -180:
        return difference + 360
    elif difference >= 180:
        return difference - 360


def calculate_bearing_change(fix_minus2, fix_minus1, fix):
    """
    Calculate bearing change between three fixes.
    :param fix_minus2: b-record from IGC file (dict with keys 'lat' and 'lon')
    :param fix_minus1: b-record from IGC file (dict with keys 'lat' and 'lon')
    :param fix: fix1: b-record from IGC file (dict with keys 'lat' and 'lon')
    :return: bearing change in degrees between -180 and +180 degrees.
    Return 0 when two of the of the fixes are the same.
    """

    # pygeodesy raises an exception when same locations are used
    if (isclose(fix_minus1['lat'], fix_minus2['lat']) and isclose(fix_minus1['lon'], fix_minus2['lon']) or
            isclose(fix_minus1['lat'], fix['lat']) and isclose(fix_minus1['lon'], fix['lon']) or
            isclose(fix_minus2['lat'], fix['lat']) and isclose(fix_minus2['lon'], fix['lon'])):
        return 0

    bearing1 = calculate_bearing(fix_minus2, fix_minus1)
    bearing2 = calculate_bearing(fix_minus1, fix)

    return calculate_bearing_difference(bearing1, bearing2)


def calculate_average_bearing(bearing1, bearing2):
    """
    Calculate the average bearing
    :param bearing1: bearing in degrees
    :param bearing2: bearing in degrees
    :return: average bearing in degrees
    """
    sin_a = sin(bearing1 * pi / 180)
    sin_b = sin(bearing2 * pi / 180)
    cos_a = cos(bearing1 * pi / 180)
    cos_b = cos(bearing2 * pi / 180)

    avg_bearing = atan2(sin_a + sin_b, cos_a + cos_b) * 180 / pi
    return (avg_bearing + 360) % 360


def seconds_time_difference(time1: datetime.time, time2: datetime.time):
    """
    Determines the time difference between to datetime.time instances, mocking the operation time2 - time1
    It is assumed that both take place at the same day.
    :param time1: 
    :param time2: 
    :return: time difference in seconds
    """
    today = datetime.date.today()
    time_diff = datetime.datetime.combine(today, time2) - datetime.datetime.combine(today, time1)
    return time_diff.total_seconds()


def add_seconds(time, seconds):
    full_date = datetime.datetime(100, 1, 1, time.hour, time.minute, time.second)
    full_date = full_date + datetime.timedelta(seconds=seconds)
    return full_date.time()


def range_with_bounds(start: int, stop: int, interval: int) -> List[int]:
    """Return list"""
    result = [int(val) for val in range(start, stop, interval)]
    if not isclose(result[-1], stop):
        result.append(stop)
    return result


def calculate_time_differences(time1, time2, interval):
    total_difference = int(seconds_time_difference(time1, time2))
    differences = range_with_bounds(0, total_difference, interval)
    return differences


def interpolate_fixes(fix1, fix2, interval=1):
    """
    Create list of fixes between fix1 and fix2. Split is defined at time interval.
    Only time, latitude and longitude are interpolated.
    :param fix1: b-record from IGC file (dict with keys 'lat' and 'lon')
    :param fix2: b-record from IGC file (dict with keys 'lat' and 'lon')
    :param interval: interval between fixes in seconds
    :return: list of fixes between fix1 and fix2 with given interval
    """

    time_differences = calculate_time_differences(fix1['time'], fix2['time'], interval)

    fixes = list()
    for difference in time_differences:
        fraction = difference / time_differences[-1]

        lat = fix1['lat'] + fraction * (fix2['lat'] - fix1['lat'])
        lon = fix1['lon'] + fraction * (fix2['lon'] - fix1['lon'])
        time = add_seconds(fix1['time'], difference)

        fixes.append(dict(time=time, lat=lat, lon=lon))

    return fixes
