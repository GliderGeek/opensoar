import unittest

import datetime

from OpenSoar.utilities.helper_functions import seconds_time_difference, interpolate_fixes
from OpenSoar.utilities.helper_functions import double_iterator
from OpenSoar.utilities.helper_functions import triple_iterator
from OpenSoar.utilities.helper_functions import calculate_distance
from OpenSoar.utilities.helper_functions import add_seconds
from OpenSoar.utilities.helper_functions import range_with_bounds
from OpenSoar.utilities.helper_functions import calculate_time_differences


class TestHelperFunctions(unittest.TestCase):

    def test_double_iterator(self):
        lst = [1, 2, 3, 4]
        result = double_iterator(lst)
        self.assertListEqual(list(result), [(1, 2), (2, 3), (3, 4)])

    def test_triple_iterator(self):
        lst = [1, 2, 3, 4, 5]
        result = triple_iterator(lst)
        self.assertListEqual(list(result), [(1, 2, 3), (2, 3, 4), (3, 4, 5)])

    def test_calculate_distance_equal_fixes(self):

        fix1 = dict(lat=52.331783333333334, lon=6.249083333333333)
        fix2 = dict(lat=52.331783333333334, lon=6.249083333333333)

        self.assertEqual(calculate_distance(fix1, fix2), 0)

    def test_seconds_time_difference(self):

        time1 = datetime.time(0, 0, 10)
        time2 = datetime.time(0, 0, 15)

        result = seconds_time_difference(time1, time2)
        expected_result = 5

        self.assertEqual(result, expected_result)

    def test_add_seconds(self):

        time1 = datetime.time(12, 0, 0)
        time2 = datetime.time(12, 0, 55)

        self.assertEqual(add_seconds(time1, 20), datetime.time(12, 0, 20))
        self.assertEqual(add_seconds(time2, 20), datetime.time(12, 1, 15))

    def test_range_with_bounds(self):
        self.assertListEqual(range_with_bounds(start=2, stop=4, interval=2), [2, 4])
        self.assertListEqual(range_with_bounds(start=2, stop=6, interval=2), [2, 4, 6])
        self.assertListEqual(range_with_bounds(start=2, stop=6, interval=3), [2, 5, 6])
        self.assertListEqual(range_with_bounds(start=2, stop=6, interval=8), [2, 6])

    def test_calculate_time_differences(self):

        time1 = datetime.time(12, 0, 50)
        time2 = datetime.time(12, 0, 55)
        time3 = datetime.time(12, 1, 2)

        self.assertListEqual(calculate_time_differences(time1, time2, 2), [0, 2, 4, 5])
        self.assertListEqual(calculate_time_differences(time2, time3, 2), [0, 2, 4, 6, 7])

    def test_interpolate_fixes(self):
        fix1 = dict(time=datetime.time(12, 0, 10), lat=50, lon=6)
        fix2 = dict(time=datetime.time(12, 0, 14), lat=58, lon=8)

        interpolated_fixes = interpolate_fixes(fix1, fix2)

        # check length
        self.assertEqual(len(interpolated_fixes), 5)

        times = [
            datetime.time(12, 0, 10),
            datetime.time(12, 0, 11),
            datetime.time(12, 0, 12),
            datetime.time(12, 0, 13),
            datetime.time(12, 0, 14)
        ]
        lats = [50, 52, 54, 56, 58]
        lons = [6, 6.5, 7.0, 7.5, 8.0]

        # check individual entries
        for time, lat, lon, interpolated_fix in zip(times, lats, lons, interpolated_fixes):
            self.assertEqual(interpolated_fix['time'], time)
            self.assertEqual(interpolated_fix['lat'], lat)
            self.assertEqual(interpolated_fix['lon'], lon)