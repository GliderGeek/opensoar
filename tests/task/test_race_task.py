import os
import unittest

from tests.task.helper_functions import get_race_task


class TestRaceTask(unittest.TestCase):

    race_task = get_race_task(os.path.join('..', 'tests', 'igc_files', 'race_task_completed.igc'))

    def test_number_of_legs(self):
        self.assertEqual(self.race_task.no_legs, 4)

    def test_distances(self):
        distances = self.race_task.distances
        expected_distances = [25.15, 27.20, 43.65, 5.23]

        self.assertEqual(len(distances), len(expected_distances))

        for distance, expected_distance in zip(distances, expected_distances):
            self.assertAlmostEqual(distance/1000, expected_distance, places=2)

    def test_total_distance(self):
        self.assertAlmostEqual(self.race_task.total_distance / 1000, 101.24, places=2)
