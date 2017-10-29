import unittest

import datetime

from OpenSoar.utilities.helper_functions import seconds_time_difference


class TestHelperFunctions(unittest.TestCase):

    def test_seconds_time_difference(self):

        time1 = datetime.time(0, 0, 10)
        time2 = datetime.time(0, 0, 15)

        result = seconds_time_difference(time1, time2)
        expected_result = 5

        self.assertEqual(result, expected_result)
