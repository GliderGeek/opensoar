import unittest
import os

from tests.task.helper_functions import get_aat


class TestAAT(unittest.TestCase):

    # https://www.soaringspot.com/en_gb/cae-nls-nederlandse-kampioenschappen-zweefvliegen-2012/results/club/task-10-on-2012-05-26/daily
    # competitor 3, SP
    aat = get_aat(os.path.join('tests', 'igc_files', 'aat_completed.igc'))

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
