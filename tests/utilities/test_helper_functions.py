import unittest

import datetime

from opensoar.utilities.helper_functions import interpolate_fixes, dm2dd, dms2dd, \
    both_none_or_same_float, both_none_or_same_str
from opensoar.utilities.helper_functions import double_iterator
from opensoar.utilities.helper_functions import triple_iterator
from opensoar.utilities.helper_functions import calculate_distance_bearing
from opensoar.utilities.helper_functions import range_with_bounds
from opensoar.utilities.helper_functions import calculate_time_differences


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

        self.assertEqual(calculate_distance_bearing(fix1, fix2)[0], 0)

    def test_range_with_bounds(self):
        self.assertListEqual(range_with_bounds(start=2, stop=4, interval=2), [2, 4])
        self.assertListEqual(range_with_bounds(start=2, stop=6, interval=2), [2, 4, 6])
        self.assertListEqual(range_with_bounds(start=2, stop=6, interval=3), [2, 5, 6])
        self.assertListEqual(range_with_bounds(start=2, stop=6, interval=8), [2, 6])

    def test_calculate_time_differences(self):

        time1 = datetime.datetime(2012, 5, 26, 12, 0, 50, tzinfo=datetime.timezone.utc)
        time2 = datetime.datetime(2012, 5, 26, 12, 0, 55, tzinfo=datetime.timezone.utc)
        time3 = datetime.datetime(2012, 5, 26, 12, 1, 2, tzinfo=datetime.timezone.utc)

        self.assertListEqual(calculate_time_differences(time1, time2, 2), [0, 2, 4, 5])
        self.assertListEqual(calculate_time_differences(time2, time3, 2), [0, 2, 4, 6, 7])

    def test_interpolate_fixes(self):
        fix1 = dict(datetime=datetime.datetime(2012, 5, 26, 12, 0, 10, tzinfo=datetime.timezone.utc), lat=50, lon=6)
        fix2 = dict(datetime=datetime.datetime(2012, 5, 26, 12, 0, 14, tzinfo=datetime.timezone.utc), lat=58, lon=8)

        interpolated_fixes = interpolate_fixes(fix1, fix2)

        # check length
        self.assertEqual(len(interpolated_fixes), 5)

        times = [
            datetime.datetime(2012, 5, 26, 12, 0, 10, tzinfo=datetime.timezone.utc),
            datetime.datetime(2012, 5, 26, 12, 0, 11, tzinfo=datetime.timezone.utc),
            datetime.datetime(2012, 5, 26, 12, 0, 12, tzinfo=datetime.timezone.utc),
            datetime.datetime(2012, 5, 26, 12, 0, 13, tzinfo=datetime.timezone.utc),
            datetime.datetime(2012, 5, 26, 12, 0, 14, tzinfo=datetime.timezone.utc)
        ]
        lats = [50, 52, 54, 56, 58]
        lons = [6, 6.5, 7.0, 7.5, 8.0]

        # check individual entries
        for time, lat, lon, interpolated_fix in zip(times, lats, lons, interpolated_fixes):
            self.assertEqual(interpolated_fix['datetime'], time)
            self.assertEqual(interpolated_fix['lat'], lat)
            self.assertEqual(interpolated_fix['lon'], lon)

    def test_dm2dd(self):
        """Test conversion between coordinate units"""
        dd = dm2dd(degrees=49.0, minutes=59.700, cardinal='N')
        self.assertAlmostEqual(dd, 49.9950, places=4)

        dd = dm2dd(degrees=9.0, minutes=34.900, cardinal='E')
        self.assertAlmostEqual(dd, 9.5817, places=4)

    def test_dms2dd(self):
        """Test conversion between coordinate units"""
        dd = dms2dd(degrees=49.0, minutes=59, seconds=42, cardinal='N')
        self.assertAlmostEqual(dd, 49.9950, places=4)

        dd = dms2dd(degrees=9.0, minutes=34, seconds=54, cardinal='E')
        self.assertAlmostEqual(dd, 9.5817, places=4)

    def test_both_none_or_same_float(self):

        test_cases = [
            (None, None, True),
            (None, 0.3, False),
            (0.3, None, False),
            (0.3, 0.3, True),
            (0.3, 0.31, False),
        ]

        for var1, var2, expected_bool in test_cases:
            result = both_none_or_same_float(var1, var2)
            self.assertEqual(expected_bool, result)

    def test_both_none_or_same_str(self):

        test_cases = [
            (None, None, True),
            (None, 'test', False),
            ('test', None, False),
            ('test', 'test', True),
            ('test2', 'test', False),
        ]

        for var1, var2, expected_bool in test_cases:
            result = both_none_or_same_str(var1, var2)
            self.assertEqual(expected_bool, result)
