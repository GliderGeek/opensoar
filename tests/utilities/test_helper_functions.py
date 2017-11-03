import unittest

import datetime

from OpenSoar.utilities.helper_functions import seconds_time_difference, double_iterator, triple_iterator, \
    calculate_distance


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
