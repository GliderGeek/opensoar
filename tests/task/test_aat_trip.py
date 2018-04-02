import datetime
import unittest

import os

from opensoar.task.trip import Trip
from tests.task.helper_functions import get_trace, get_task


class TestAATTrip(unittest.TestCase):

    # https://www.soaringspot.com/en_gb/cae-nls-nederlandse-kampioenschappen-zweefvliegen-2012/results/club/task-10-on-2012-05-26/daily
    # competitor 3, SP

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'aat_completed.igc')
    aat = get_task(igc_path)
    trace = get_trace(igc_path)
    trip = Trip(aat, trace)

    def test_total_distance(self):
        total_distance = sum(self.trip.distances)
        self.assertAlmostEqual(total_distance / 1e3, 199.42, places=2)

    def test_start_time(self):
        start_time = self.trip.fixes[0]['time']
        expected_start_time = datetime.time(12, 22, 8)
        self.assertEqual(expected_start_time, start_time)

    def test_finish_time(self):
        finish_time = self.trip.finish_time
        expected_finish_time = datetime.time(15, 52, 8)
        self.assertEqual(expected_finish_time, finish_time)


class TestAATTripOutlandingOutside(unittest.TestCase):
    """
    Test AAT Trip in which an outlanding takes place outside the last rounded sector.
    """

    # https://www.soaringspot.com/en_gb/cae-nls-nederlandse-kampioenschappen-zweefvliegen-2012/results/club/task-10-on-2012-05-26/daily
    # competitor 5, CEO
    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'aat_outlanding_outside_sector.igc')
    aat = get_task(igc_path)
    trace = get_trace(igc_path)
    trip = Trip(aat, trace)

    def test_trip_fixes(self):

        # assert correct number of trip fixes
        self.assertEqual(len(self.trip.fixes), 3)

        # assert if opensoar finds same fixes as seeyou, based on time
        fix_times = [
            # tuple with (opensoar time, SeeYou time)
            (self.trip.refined_start_time, datetime.time(12, 14, 21)),
            (self.trip.fixes[1]['time'], datetime.time(12, 49, 22)),
            (self.trip.fixes[2]['time'], datetime.time(13, 26, 14)),
            (self.trip.outlanding_fix['time'], datetime.time(14, 8, 0)),
        ]

        for opensoar_time, seeyou_time in fix_times:
            self.assertEqual(seeyou_time, opensoar_time)

    # todo: fix total distance calculation. why is this different from seeyou?
    # def test_total_distance(self):
    #     total_distance = sum(self.trip.distances)
    #     self.assertAlmostEqual(total_distance / 1e3, 98.54, places=2)


class TestAATTripOutlandingInside(unittest.TestCase):
    """
    Test AAT Trip in which an outlanding takes place inside the last rounded sector.
    """

    # https://www.soaringspot.com/en_gb/cae-nls-nederlandse-kampioenschappen-zweefvliegen-2012/results/club/task-10-on-2012-05-26/daily
    # competitor 7, YES
    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'aat_outlanding_inside_sector.igc')
    aat = get_task(igc_path)
    trace = get_trace(igc_path)
    trip = Trip(aat, trace)

    def test_trip_fixes(self):

        # assert correct number of trip fixes
        self.assertEqual(len(self.trip.fixes), 4)

        # assert if opensoar finds same fixes as seeyou, based on time
        fix_times = [
            # tuple with (opensoar time, SeeYou time)
            (self.trip.refined_start_time, datetime.time(12, 24, 14)),
            (self.trip.fixes[1]['time'], datetime.time(12, 57, 53)),
            (self.trip.fixes[2]['time'], datetime.time(13, 42, 31)),
            (self.trip.fixes[3]['time'], datetime.time(14, 4, 5)),
            (self.trip.outlanding_fix['time'], datetime.time(14, 5, 49)),
        ]

        for opensoar_time, seeyou_time in fix_times:
            self.assertEqual(seeyou_time, opensoar_time)

    def test_total_distance(self):
        total_distance = sum(self.trip.distances)
        self.assertAlmostEqual(total_distance / 1e3, 86.07, places=2)

# todo: add ENL testcase
