import os
import unittest
import datetime
from copy import deepcopy

from opensoar.task.trip import Trip
from opensoar.thermals.flight_phases import FlightPhases
from opensoar.utilities.helper_functions import double_iterator

from tests.task.helper_functions import get_trace, get_task


class TestFlightPhases(unittest.TestCase):

    pysoar_phase_start_times = [
        datetime.datetime(2014, 6, 21, 12, 12, 52, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 20, 22, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 24, 14, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 29, 22, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 33, 6, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 34, 50, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 37, 42, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 47, 14, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 12, 52, 42, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 13, 1, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2014, 6, 21, 13, 4, 52, tzinfo=datetime.timezone.utc),
    ]

    cwd = os.path.dirname(__file__)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'race_task_completed.igc')

    trace = get_trace(igc_path)
    race_task = get_task(igc_path)
    trip = Trip(race_task, trace)
    phases = FlightPhases('pysoar', trace, trip)

    def test_all_phases(self):

        all_phases = self.phases.all_phases(leg='all')

        # Check if end fixes are the same as the start fixes of next phase
        for phase, next_phase in double_iterator(all_phases):
            self.assertEqual(phase[1][-1], next_phase[1][0])

        # check same number of phases
        self.assertEqual(len(all_phases), len(self.pysoar_phase_start_times))

        # check if start times of phases are within 2 seconds
        for phase, pysoar_phase_start_time in zip(all_phases, self.pysoar_phase_start_times):
            time_diff = (pysoar_phase_start_time - phase.fixes[0]['datetime']).total_seconds()
            self.assertLessEqual(abs(time_diff), 2)

    def test_thermals(self):

        thermals = self.phases.thermals(leg='all')

        # check if indeed only thermals
        for thermal in thermals:
            self.assertFalse(thermal.is_cruise)

        # check if correct phases are classified as thermals
        for thermal, pysoar_start_time in zip(thermals, self.pysoar_phase_start_times[1::2]):
            time_diff = (pysoar_start_time - thermal.fixes[0]['datetime']).total_seconds()
            self.assertLessEqual(abs(time_diff), 2)

    def test_cruises(self):

        cruises = self.phases.cruises(leg='all')

        # check if indeed only cruises
        for cruise in cruises:
            self.assertTrue(cruise.is_cruise)

        # check if correct phases are classified as cruises
        for cruise, pysoar_start_time in zip(cruises, self.pysoar_phase_start_times[0::2]):
            time_diff = (pysoar_start_time - cruise.fixes[0]['datetime']).total_seconds()
            self.assertLessEqual(abs(time_diff), 2)

    def test_thermals_on_leg(self):

        thermals_leg2 = self.phases.thermals(leg=1)

        # check indeed subset of all thermals
        self.assertTrue(len(thermals_leg2) < len(self.phases.thermals()))

        # check all thermals
        for thermal in thermals_leg2:
            self.assertFalse(thermal.is_cruise)

        leg_start_time = self.trip.fixes[1]['datetime']
        leg_end_time = self.trip.fixes[2]['datetime']

        # check start-time of first thermal
        start_time = thermals_leg2[0].fixes[0]['datetime']
        diff = (leg_start_time - start_time).total_seconds()
        self.assertEqual(diff, 0)

        # check endtime of last thermal
        end_time = thermals_leg2[-1].fixes[-1]['datetime']
        diff = (leg_end_time - end_time).total_seconds()
        self.assertEqual(diff, 0)

    def test_cruises_on_leg(self):

        cruises_leg2 = self.phases.cruises(leg=1)

        # check indeed subset of all thermals
        self.assertTrue(len(cruises_leg2) < len(self.phases.cruises()))

        # check all cruises
        for cruise in cruises_leg2:
            self.assertTrue(cruise.is_cruise)

    def test_phases_on_leg_spanning_complete_leg(self):
        """This test covers the case when the phase starts before the start of the leg and ends after
        the end of the leg."""

        trace = [
            {'datetime': datetime.datetime(2012, 5, 26, 11, 33, 26, tzinfo=datetime.timezone.utc), 'lat': 52.468183333333336, 'lon': 6.3402, 'validity': 'A',
             'pressure_alt': -37, 'gps_alt': 47, 'FXA': 2, 'SIU': 1},
            {'datetime': datetime.datetime(2012, 5, 26, 11, 33, 34, tzinfo=datetime.timezone.utc), 'lat': 52.468183333333336, 'lon': 6.3402, 'validity': 'A',
             'pressure_alt': -37, 'gps_alt': 47, 'FXA': 2, 'SIU': 1},
            {'datetime': datetime.datetime(2012, 5, 26, 11, 33, 42, tzinfo=datetime.timezone.utc), 'lat': 52.468183333333336, 'lon': 6.3402, 'validity': 'A',
             'pressure_alt': -37, 'gps_alt': 47, 'FXA': 2, 'SIU': 1},
            {'datetime': datetime.datetime(2012, 5, 26, 11, 33, 50, tzinfo=datetime.timezone.utc), 'lat': 52.468183333333336, 'lon': 6.3402, 'validity': 'A',
             'pressure_alt': -37, 'gps_alt': 48, 'FXA': 1, 'SIU': 1},
            {'datetime': datetime.datetime(2012, 5, 26, 11, 33, 58, tzinfo=datetime.timezone.utc), 'lat': 52.468183333333336, 'lon': 6.340216666666667, 'validity': 'A',
             'pressure_alt': -37, 'gps_alt': 48, 'FXA': 1, 'SIU': 1},
            {'datetime': datetime.datetime(2012, 5, 26, 11, 34, 6, tzinfo=datetime.timezone.utc), 'lat': 52.46816666666667, 'lon': 6.339666666666667, 'validity': 'A',
             'pressure_alt': -38, 'gps_alt': 49, 'FXA': 1, 'SIU': 1},
        ]

        # originally this did trip = deepcopy(self._trip)
        # but this is broken with current aerofiles version
        _trace = get_trace(self.igc_path)
        race_task = get_task(self.igc_path)
        trip = Trip(race_task, _trace)

        trip.fixes = [
            trace[1],
            trace[4]
        ]

        phases = FlightPhases('pysoar', trace, trip)

        # there should only be one phase: starting at first fix and ending at last fix of trace
        # these are conditions to a correct test setup, therefore no actual tests
        assert len(phases._phases) == 1
        assert phases._phases[0].fixes[0]['datetime'] == trace[0]['datetime']
        assert phases._phases[0].fixes[-1]['datetime'] == trace[-1]['datetime']

        all_phases_leg0 = phases.all_phases(leg=0)

        # check 1 phase found
        self.assertEqual(len(all_phases_leg0), 1)

        # check if phase correctly starts and ends at the trip fixes and not the trace fixes
        first_phase_fix = all_phases_leg0[0].fixes[0]
        last_phase_fix = all_phases_leg0[0].fixes[-1]
        self.assertEqual(first_phase_fix['datetime'], trip.fixes[0]['datetime'])
        self.assertEqual(last_phase_fix['datetime'], trip.fixes[-1]['datetime'])
