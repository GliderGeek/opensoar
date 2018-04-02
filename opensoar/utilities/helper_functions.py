from copy import copy
from math import isclose, pi, sin, cos, atan2

import datetime
from typing import List

from pygeodesy.ellipsoidalVincenty import LatLon


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


def height_difference_fixes(fix1, fix2, gps_altitude=True):
    if gps_altitude:
        return fix2['gps_alt'] - fix1['gps_alt']
    else:
        return fix2['pressure_alt'] - fix1['pressure_alt']


def altitude_gain_and_loss(fixes: List[dict], gps_altitude=True):
    if gps_altitude:
        altitude_key = 'gps_alt'
    else:
        altitude_key = 'pressure_alt'

    gain, loss = 0, 0
    for fix, next_fix in double_iterator(fixes):
        delta_h = next_fix[altitude_key] - fix[altitude_key]

        if delta_h >= 0:
            gain += delta_h
        else:
            loss += (-delta_h)

    return gain, loss


def seconds_time_difference_fixes(fix1, fix2):
    return seconds_time_difference(fix1['time'], fix2['time'])


def total_distance_travelled(fixes: List[dict]):
    """Calculates the total distance, summing over the inter fix distances"""
    distance = 0
    for fix, next_fix in double_iterator(fixes):
        distance += calculate_distance(fix, next_fix)

    return distance


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


def add_times(start_time: datetime.time, delta_time: datetime.timedelta):
    """
    Helper to circumvent problem that normal datetime.time instances can not be added.
    :param start_time:
    :param delta_time:
    :return:
    """
    full_datetime_start = datetime.datetime.combine(datetime.date.today(), start_time)

    full_datetime_result = full_datetime_start + delta_time
    return full_datetime_result.time()


def subtract_times(start_time: datetime.time, delta_time: datetime.time):
    full_datetime_start = datetime.datetime.combine(datetime.date.today(), start_time)

    full_datetime_result = full_datetime_start - datetime.timedelta(
        hours=delta_time.hour, minutes=delta_time.minute, seconds=delta_time.second)

    return full_datetime_result.time()


def add_seconds(time: datetime.time, seconds: int) -> datetime.time:
    """
    Add seconds to datetime.time object and return resulting datetime.time object.

    :param time:
    :param seconds: not limited to 0-59.
    :return:
    """

    additional_seconds = seconds

    additional_hours = additional_seconds // 3600
    additional_seconds -= additional_hours * 3600

    additional_minutes = additional_seconds // 60
    additional_seconds -= additional_minutes * 60

    return add_times(time, datetime.timedelta(hours=additional_hours,
                                              minutes=additional_minutes,
                                              seconds=additional_seconds))


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


def calculate_destination(start_fix, distance, bearing):
    destination_latlon = LatLon(start_fix['lat'], start_fix['lon']).destination(distance, bearing)
    return dict(lat=destination_latlon.lat, lon=destination_latlon.lon)


def dms2dd(degrees, minutes, seconds, cardinal):
    """convert coordinate format with degrees, minutes and second to degrees"""
    dd = degrees + minutes / 60.0 + seconds / 3600.0
    if cardinal in ('S', 'W'):
        dd *= -1
    return dd


def dm2dd(degrees, minutes, cardinal):
    """convert coordinate format with degrees and minutes to degrees"""
    dd = degrees + minutes / 60.0
    if cardinal in ('S', 'W'):
        dd *= -1
    return dd


def both_none_or_same_float(var1, var2):
    """Determine wheter both vars are the same. Either None or float"""
    if var1 is None:
        return var2 is None
    else:
        return var2 is not None and isclose(var1, var2)


def both_none_or_same_str(var1, var2):
    """Determine wheter both vars are the same. Either None or float"""
    if var1 is None:
        return var2 is None
    else:
        return var2 is not None and var1 == var2
