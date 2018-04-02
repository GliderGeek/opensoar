import unittest
import os
from copy import deepcopy

import datetime

from opensoar.task.aat import AAT
from tests.task.helper_functions import get_task


class TestAAT(unittest.TestCase):

    # https://www.soaringspot.com/en_gb/cae-nls-nederlandse-kampioenschappen-zweefvliegen-2012/results/club/task-10-on-2012-05-26/daily
    # competitor 3, SP

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'aat_completed.igc')
    aat = get_task(igc_path)

    def test_number_of_legs(self):
        self.assertEqual(self.aat.no_legs, 5)

    def test_nominal_distances(self):
        nominal_distances = self.aat._nominal_distances
        expected_distances = [45.20, 43.25, 73.26, 88.28, 9.62]

        # note: the final distance is different from the one in soaringspot.
        # soaringspot says the last distance should be 9.12km. they wrongfully subtract 0.5km from the finish line

        self.assertEqual(len(nominal_distances), len(expected_distances))

        for distance, expected_distance in zip(nominal_distances, expected_distances):
            self.assertAlmostEqual(distance / 1e3, expected_distance, places=2)

    def test_equal_aat(self):
        aat2 = get_task(self.igc_path)
        self.assertEqual(self.aat, aat2)

    def test_not_equal_aat(self):

        waypoints = self.aat.waypoints

        # test_unequal number_waypoints
        waypoints2 = deepcopy(waypoints)
        del waypoints2[2]
        aat2 = AAT(waypoints2, self.aat._t_min)
        self.assertNotEqual(self.aat, aat2)

        # test unequal t_min
        aat2 = AAT(waypoints, datetime.time(1, 0, 0))
        self.assertNotEqual(self.aat, aat2)
