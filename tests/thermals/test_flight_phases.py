import os
import unittest
import datetime

from opensoar.task.trip import Trip
from opensoar.thermals.flight_phases import FlightPhases
from opensoar.utilities.helper_functions import double_iterator, seconds_time_difference

from tests.task.helper_functions import get_trace, get_race_task


class TestFlightPhases(unittest.TestCase):

    pysoar_phase_start_times = [
        datetime.time(12, 12, 52),
        datetime.time(12, 20, 22),
        datetime.time(12, 24, 14),
        datetime.time(12, 29, 22),
        datetime.time(12, 33, 6),
        datetime.time(12, 34, 50),
        datetime.time(12, 37, 42),
        datetime.time(12, 47, 14),
        datetime.time(12, 52, 42),
        datetime.time(13, 1, 0),
        datetime.time(13, 4, 52),
    ]

    igc_path = os.path.join('tests', 'igc_files', 'race_task_completed.igc')
    trace = get_trace(igc_path)
    start_index = 1168
    last_tp_index = 3240
    race_task = get_race_task(igc_path)
    trip = Trip(race_task, trace)
    phases = FlightPhases('pysoar', trace[start_index:last_tp_index+1], trip)

    def test_all_phases(self):

        all_phases = self.phases.all_phases()

        # Check if end fixes are the same as the start fixes of next phase
        for phase, next_phase in double_iterator(all_phases):
            self.assertEqual(phase[1][-1], next_phase[1][0])

        # check same number of phases
        self.assertEqual(len(all_phases), len(self.pysoar_phase_start_times))

        # check if start times of phases are within 2 seconds
        for phase, pysoar_phase_start_time in zip(all_phases, self.pysoar_phase_start_times):
            time_diff = seconds_time_difference(phase.fixes[0]['time'], pysoar_phase_start_time)
            self.assertLessEqual(abs(time_diff), 2)

    def test_thermals(self):

        thermals = self.phases.thermals()

        # check if indeed only thermals
        for thermal in thermals:
            self.assertFalse(thermal.is_cruise)

        # check if correct phases are classified as thermals
        for thermal, pysoar_start_time in zip(thermals, self.pysoar_phase_start_times[1::2]):
            time_diff = seconds_time_difference(thermal.fixes[0]['time'], pysoar_start_time)
            self.assertLessEqual(abs(time_diff), 2)

    def test_cruises(self):

        cruises = self.phases.cruises()

        # check if indeed only cruises
        for cruise in cruises:
            self.assertTrue(cruise.is_cruise)

        # check if correct phases are classified as cruises
        for cruise, pysoar_start_time in zip(cruises, self.pysoar_phase_start_times[0::2]):
            time_diff = seconds_time_difference(cruise.fixes[0]['time'], pysoar_start_time)
            self.assertLessEqual(abs(time_diff), 2)

    def test_thermals_on_leg(self):

        thermals_leg2 = self.phases.thermals(leg=1)

        # check indeed subset of all thermals
        self.assertTrue(len(thermals_leg2) < len(self.phases.thermals()))

        # check all thermals
        for thermal in thermals_leg2:
            self.assertFalse(thermal.is_cruise)

        leg_start_time = self.trip.fixes[1]['time']
        leg_end_time = self.trip.fixes[2]['time']

        # check starttime of first thermal
        start_time = thermals_leg2[0].fixes[0]['time']
        self.assertEqual(seconds_time_difference(start_time, leg_start_time), 0)

        # check endtime of last thermal
        end_time = thermals_leg2[-1].fixes[-1]['time']
        self.assertEqual(seconds_time_difference(end_time, leg_end_time), 0)

    def test_cruises_on_leg(self):

        cruises_leg2 = self.phases.cruises(leg=1)

        # check indeed subset of all thermals
        self.assertTrue(len(cruises_leg2) < len(self.phases.cruises()))

        # check all cruises
        for cruise in cruises_leg2:
            self.assertTrue(cruise.is_cruise)
