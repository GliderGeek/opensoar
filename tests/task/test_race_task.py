import os
import unittest
from copy import deepcopy

import datetime

from opensoar.competition.soaringspot import get_waypoints
from opensoar.task.race_task import RaceTask
from tests.task.helper_functions import get_task


class TestRaceTask(unittest.TestCase):

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'race_task_completed.igc')
    race_task = get_task(igc_path)

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
        race_task2 = get_task(self.igc_path)
        self.assertEqual(self.race_task, race_task2)

    def test_not_equal_tasks(self):
        waypoints = self.race_task.waypoints

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

    def test_race_reduced_legs(self):
        """
        Race task with reduced legs, should produce correct distance

        https://www.soaringspot.com/en_gb/pribina-cup-2018-nitra-2018/results/15-meter/task-1-on-2018-04-02/daily
        """

        lcu_lines = [
            'LCU::C020418195435301299000202',
            'LCU::C0000000N00000000E',
            'LCU::C4819183N01759550E158LEHOTA',
            'LCU::C4907167N01819400E235PUCHOV',
            'LCU::C4748117N01842983E271STUROVO',
            'LCU::C4816767N01807967E001NITRA',
            'LCU::C0000000N00000000E',
        ]

        lseeyou_lines = [
            'LSEEYOU OZ=-1,Style=2,SpeedStyle=0,R1=5000m,A1=180,Line=1',
            'LSEEYOU OZ=0,Style=1,SpeedStyle=3,R1=500m,A1=180,Reduce=1',
            'LSEEYOU OZ=1,Style=1,SpeedStyle=3,R1=500m,A1=180,Reduce=1',
            'LSEEYOU OZ=2,Style=3,SpeedStyle=2,R1=3000m,A1=180,Reduce=1',
        ]

        waypoints = get_waypoints(lcu_lines, lseeyou_lines)
        race_task = RaceTask(waypoints)

        self.assertAlmostEqual(race_task.total_distance / 1000, 305.21, places=2)

    def test_race_moved_leg(self):
        """
        Race task with moved waypoint, should not crash. somehow distances are not completely equal.

        https://www.soaringspot.com/en_gb/35th-world-gliding-championships-hosin-2018/results/18-meter/task-1-on-2018-07-29/daily
        """

        lcu_lines = [
            'LCU::C290718193533301299000203',
            'LCU::C0000000N00000000E',
            'LCU::C4908600N01432867E011SP07RADONICE',
            'LCU::C4936150N01352917E477ROZMITAL',
            'LCU::C4940950N01240067E442PRIMDA',
            'LCU::C4915633N01308733E385NYRSKO',
            'LCU::C4902383N01429650E001SP01HOSIN',
            'LCU::C0000000N00000000E',
        ]

        lseeyou_lines = [
            'LSEEYOU OZ=-1,Style=2,SpeedStyle=0,R1=5000m,A1=180,Line=1',
            'LSEEYOU OZ=0,Style=1,SpeedStyle=3,R1=500m,A1=180',
            'LSEEYOU OZ=1,Style=1,SpeedStyle=3,R1=500m,A1=180',
            'LSEEYOU OZ=2,Style=1,SpeedStyle=3,R1=500m,A1=180',
            'LSEEYOU OZ=3,Style=3,SpeedStyle=2,R1=5000m,A1=180,Move=1',
        ]

        waypoints = get_waypoints(lcu_lines, lseeyou_lines)

        try:
            race_task = RaceTask(waypoints)
        except Exception:
            self.fail()
