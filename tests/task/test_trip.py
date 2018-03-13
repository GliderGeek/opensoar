import os
import unittest

import datetime

from opensoar.task.trip import Trip
from tests.task.helper_functions import get_trace, get_task


class TestTrip(unittest.TestCase):
    """
    This testcase covers a completed race task. number 2, comp id HS:
    https://www.soaringspot.com/en/sallandse-tweedaagse-2014/results/club/task-1-on-2014-06-21/daily
    """

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'race_task_completed.igc')
    race_task = get_task(igc_path)
    trace = get_trace(igc_path)
    trip = Trip(race_task, trace)

    def test_number_of_fixes(self):
        self.assertEqual(len(self.trip.fixes), 5)

    def test_distances(self):
        self.assertListEqual(self.trip.distances, self.race_task.distances)

    def test_outlanded(self):
        self.assertFalse(self.trip.outlanded())

    def test_start_time(self):
        start_fix = self.trip.fixes[0]
        refined_start_time = self.trip.refined_start_time
        self.assertEqual(start_fix['time'], datetime.time(12, 12, 54))
        self.assertEqual(refined_start_time, datetime.time(12, 12, 55))

    def test_finish_time(self):
        finish_fix = self.trip.fixes[-1]
        self.assertEqual(finish_fix['time'], datetime.time(13, 21, 58))


class TestOutlandingTrip(unittest.TestCase):
    """
    This testcase covers an outlanding on a race task. number 7, comp id SU:
    https://www.soaringspot.com/en/sallandse-tweedaagse-2014/results/club/task-1-on-2014-06-21/daily
    """

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'outlanding_race_task.igc')
    race_task = get_task(igc_path)
    trace = get_trace(igc_path)
    trip = Trip(race_task, trace)

    def test_total_distance(self):
        self.assertAlmostEqual(sum(self.trip.distances) / 1000, 89.99, places=2)

    def test_completed_legs(self):
        self.assertEqual(self.trip.completed_legs(), 2)

    def test_fix_after_leg_on_outlanding_leg(self):
        """A fix happening on the outlanding leg can never be after the leg, because that leg is never finished."""
        fix = {'time': datetime.time(14, 44, 45)}
        fix_after_leg = self.trip.fix_after_leg(fix, leg=2)
        self.assertFalse(fix_after_leg)


class TestEnlOutlandingTrip(unittest.TestCase):
    """
    This testcase covers an ENL outlanding on a race task. number 10, comp id 2C:
    https://www.soaringspot.com/en/nk-zweefvliegen-2017/results/18-meter-klasse/task-8-on-2017-05-31/daily
    """

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'outlanding_race_task_enl.igc')
    race_task = get_task(igc_path)
    trace = get_trace(igc_path)
    trip = Trip(race_task, trace)

    def test_total_distance(self):
        self.assertAlmostEqual(sum(self.trip.distances) / 1000, 378.13, places=2)

    def test_completed_legs(self):
        self.assertEqual(self.trip.completed_legs(), 4)
