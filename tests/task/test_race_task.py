import os
import unittest
from copy import deepcopy

import datetime
from aerofiles.igc import Reader

from opensoar.competition.soaringspot import get_waypoints_from_parsed_file
from opensoar.task.race_task import RaceTask
from tests.task.helper_functions import get_race_task


class TestRaceTask(unittest.TestCase):

    igc_path = os.path.join('tests', 'igc_files', 'race_task_completed.igc')
    race_task = get_race_task(igc_path)

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

    def test_equal_tasks(self):
        race_task2 = get_race_task(self.igc_path)
        self.assertEqual(self.race_task, race_task2)

    def test_not_equal_tasks(self):
        with open(self.igc_path, 'r') as f:
            parsed_igc_file = Reader().read(f)

        waypoints = get_waypoints_from_parsed_file(parsed_igc_file)

        # test_unequal number_waypoints
        waypoints2 = deepcopy(waypoints)
        del waypoints2[2]
        race_task2 = RaceTask(waypoints2)
        self.assertNotEqual(self.race_task, race_task2)

        # test different waypoint
        waypoints3 = deepcopy(waypoints)
        waypoints3[2].r_max = 1000
        race_task2 = RaceTask(waypoints3)
        self.assertNotEqual(self.race_task, race_task2)

        # test different start_time
        race_task2 = RaceTask(waypoints, start_opening=datetime.time(0, 0, 0))
        self.assertNotEqual(race_task2, self.race_task)

        # test different start buffer
        race_task2 = RaceTask(waypoints, start_time_buffer=5)
        self.assertNotEqual(self.race_task, race_task2)
