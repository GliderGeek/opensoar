import datetime
import os
import unittest
from copy import deepcopy

from opensoar.task.trip import Trip
from opensoar.thermals.flight_phases import FlightPhases
from opensoar.utilities.helper_functions import double_iterator
from tests.task.helper_functions import get_task, get_trace


class TestFlightPhases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cwd = os.path.dirname(__file__)
        cls.igc_path = os.path.join(
            cls.cwd, "..", "igc_files", "race_task_completed.igc"
        )
        cls.trace = get_trace(cls.igc_path)
        cls.race_task = get_task(cls.igc_path)
        cls.trip = Trip(cls.race_task, cls.trace)
        cls.phases = FlightPhases("pysoar", cls.trace, cls.trip)

        # Reference start times for each phase detected by PySoar
        cls.pysoar_phase_start_times = [
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

    def test_all_phases(self):

        all_phases = self.phases.all_phases(leg="all")

        # Check if end fixes are the same as the start fixes of next phase
        for phase, next_phase in double_iterator(all_phases):
            self.assertEqual(phase.fixes[-1], next_phase.fixes[0])

        # check same number of phases
        self.assertEqual(len(all_phases), len(self.pysoar_phase_start_times))

        # check if start times of phases are within 2 seconds
        for phase, pysoar_phase_start_time in zip(
            all_phases, self.pysoar_phase_start_times
        ):
            time_diff = (
                pysoar_phase_start_time - phase.fixes[0]["datetime"]
            ).total_seconds()
            self.assertLessEqual(abs(time_diff), 2)

    def test_thermals(self):

        thermals = self.phases.thermals(leg="all")

        # check if indeed only thermals
        for thermal in thermals:
            self.assertFalse(thermal.is_cruise)

        # check if correct phases are classified as thermals
        for thermal, pysoar_start_time in zip(
            thermals, self.pysoar_phase_start_times[1::2]
        ):
            time_diff = (
                pysoar_start_time - thermal.fixes[0]["datetime"]
            ).total_seconds()
            self.assertLessEqual(abs(time_diff), 2)

    def test_cruises(self):

        cruises = self.phases.cruises(leg="all")

        # check if indeed only cruises
        for cruise in cruises:
            self.assertTrue(cruise.is_cruise)

        # check if correct phases are classified as cruises
        for cruise, pysoar_start_time in zip(
            cruises, self.pysoar_phase_start_times[0::2]
        ):
            time_diff = (
                pysoar_start_time - cruise.fixes[0]["datetime"]
            ).total_seconds()
            self.assertLessEqual(abs(time_diff), 2)

    def test_thermals_on_leg(self):

        thermals_leg2 = self.phases.thermals(leg=1)

        # check indeed subset of all thermals
        self.assertTrue(len(thermals_leg2) < len(self.phases.thermals()))

        # check all thermals
        for thermal in thermals_leg2:
            self.assertFalse(thermal.is_cruise)

        leg_start_time = self.trip.fixes[1]["datetime"]
        leg_end_time = self.trip.fixes[2]["datetime"]

        # check start-time of first thermal
        start_time = thermals_leg2[0].fixes[0]["datetime"]
        self.assertEqual((leg_start_time - start_time).total_seconds(), 0)

        # check end-time of last thermal
        end_time = thermals_leg2[-1].fixes[-1]["datetime"]
        self.assertEqual((leg_end_time - end_time).total_seconds(), 0)

    def test_cruises_on_leg(self):

        cruises_leg2 = self.phases.cruises(leg=1)

        # check indeed subset of all cruises
        self.assertTrue(len(cruises_leg2) < len(self.phases.cruises()))

        # check all cruises
        for cruise in cruises_leg2:
            self.assertTrue(cruise.is_cruise)

    def test_phases_on_leg_spanning_complete_leg(self):
        """This test covers the case when the phase starts before the start of the leg and ends after
        the end of the leg."""

        trace = [
            {
                "datetime": datetime.datetime(
                    2012, 5, 26, 11, 33, 26, tzinfo=datetime.timezone.utc
                ),
                "lat": 52.468183333333336,
                "lon": 6.3402,
                "validity": "A",
                "pressure_alt": -37,
                "gps_alt": 47,
                "FXA": 2,
                "SIU": 1,
            },
            {
                "datetime": datetime.datetime(
                    2012, 5, 26, 11, 33, 34, tzinfo=datetime.timezone.utc
                ),
                "lat": 52.468183333333336,
                "lon": 6.3402,
                "validity": "A",
                "pressure_alt": -37,
                "gps_alt": 47,
                "FXA": 2,
                "SIU": 1,
            },
            {
                "datetime": datetime.datetime(
                    2012, 5, 26, 11, 33, 42, tzinfo=datetime.timezone.utc
                ),
                "lat": 52.468183333333336,
                "lon": 6.3402,
                "validity": "A",
                "pressure_alt": -37,
                "gps_alt": 47,
                "FXA": 2,
                "SIU": 1,
            },
            {
                "datetime": datetime.datetime(
                    2012, 5, 26, 11, 33, 50, tzinfo=datetime.timezone.utc
                ),
                "lat": 52.468183333333336,
                "lon": 6.3402,
                "validity": "A",
                "pressure_alt": -37,
                "gps_alt": 48,
                "FXA": 1,
                "SIU": 1,
            },
            {
                "datetime": datetime.datetime(
                    2012, 5, 26, 11, 33, 58, tzinfo=datetime.timezone.utc
                ),
                "lat": 52.468183333333336,
                "lon": 6.340216666666667,
                "validity": "A",
                "pressure_alt": -37,
                "gps_alt": 48,
                "FXA": 1,
                "SIU": 1,
            },
            {
                "datetime": datetime.datetime(
                    2012, 5, 26, 11, 34, 6, tzinfo=datetime.timezone.utc
                ),
                "lat": 52.46816666666667,
                "lon": 6.339666666666667,
                "validity": "A",
                "pressure_alt": -38,
                "gps_alt": 49,
                "FXA": 1,
                "SIU": 1,
            },
        ]

        # originally this did trip = deepcopy(self._trip)
        # but this is broken with current aerofiles version
        _trace = get_trace(self.igc_path)
        race_task = get_task(self.igc_path)
        trip = Trip(race_task, _trace)

        trip.fixes = [trace[1], trace[4]]

        phases = FlightPhases("pysoar", trace, trip)

        # There should only be one phase: starting at first fix and ending at last fix of trace
        self.assertEqual(len(phases._phases), 1)
        self.assertEqual(phases._phases[0].fixes[0]["datetime"], trace[0]["datetime"])
        self.assertEqual(phases._phases[0].fixes[-1]["datetime"], trace[-1]["datetime"])

        all_phases_leg0 = phases.all_phases(leg=0)

        # check 1 phase found
        self.assertEqual(len(all_phases_leg0), 1)

        # check if phase correctly starts and ends at the trip fixes and not the trace fixes
        first_phase_fix = all_phases_leg0[0].fixes[0]
        last_phase_fix = all_phases_leg0[0].fixes[-1]
        self.assertEqual(first_phase_fix["datetime"], trip.fixes[0]["datetime"])
        self.assertEqual(last_phase_fix["datetime"], trip.fixes[-1]["datetime"])

    def test_invalid_leg_index(self):
        with self.assertRaises(ValueError):
            self.phases.thermals(leg=99)

    def test_leg_filter_without_trip(self):
        phases_no_trip = FlightPhases("pysoar", self.trace)
        with self.assertRaises(ValueError):
            phases_no_trip.thermals(leg=0)

    def test_invalid_classification_method(self):
        with self.assertRaises(ValueError):
            FlightPhases("unsupported_method", self.trace, self.trip)

    def test_all_phases_no_leg(self):
        all_phases = self.phases.all_phases(leg="all")
        self.assertEqual(len(all_phases), len(self.pysoar_phase_start_times))

    def test_phase_boundaries_are_continuous(self):
        all_phases = self.phases.all_phases(leg="all")
        for phase, next_phase in double_iterator(all_phases):
            self.assertEqual(
                phase.fixes[-1]["datetime"], next_phase.fixes[0]["datetime"]
            )

    def test_phase_metadata_fields(self):
        phase = self.phases.all_phases(leg="all")[0]

        self.assertIsNotNone(phase.duration)
        self.assertIsInstance(phase.duration, float)

        self.assertIsNotNone(phase.gps_altitude_gain)
        self.assertIsInstance(phase.gps_altitude_gain, (int, float))

        self.assertIsNotNone(phase.pressure_altitude_gain)
        self.assertIsInstance(phase.pressure_altitude_gain, (int, float))

        self.assertIsNotNone(phase.average_climb_rate_gps)
        self.assertIsInstance(phase.average_climb_rate_gps, float)

        self.assertIsNotNone(phase.start_time)
        self.assertIsInstance(phase.start_time, datetime.datetime)

        self.assertIsNotNone(phase.end_time)
        self.assertIsInstance(phase.end_time, datetime.datetime)

    def test_filter_by_time_range(self):
        start = datetime.datetime(2014, 6, 21, 12, 20, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2014, 6, 21, 12, 40, 0, tzinfo=datetime.timezone.utc)

        filtered = self.phases.filter_by_time_range(start, end)

        for phase in filtered:
            self.assertLessEqual(phase.start_time, end)
            self.assertGreaterEqual(phase.end_time, start)

    def test_filter_by_location(self):
        center_lat = 52.33
        center_lon = 6.24
        radius_km = 5

        filtered = self.phases.filter_by_location(center_lat, center_lon, radius_km)

        self.assertGreater(len(filtered), 0)
        for phase in filtered:
            self.assertTrue(
                any(
                    abs(fix["lat"] - center_lat) < 0.1
                    and abs(fix["lon"] - center_lon) < 0.1
                    for fix in phase.fixes
                )
            )

    def test_summary_stats(self):
        stats = self.phases.summary_stats()

        self.assertIn("total_thermals", stats)
        self.assertIn("total_cruises", stats)
        self.assertIn("average_thermal_duration_sec", stats)
        self.assertIn("total_cruise_distance_m", stats)

        self.assertIsInstance(stats["total_thermals"], int)
        self.assertIsInstance(stats["total_cruises"], int)
        self.assertTrue(
            stats["average_thermal_duration_sec"] is None
            or isinstance(stats["average_thermal_duration_sec"], float)
        )
        self.assertIsInstance(stats["total_cruise_distance_m"], (int, float))
