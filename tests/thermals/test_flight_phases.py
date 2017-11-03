import os
import unittest

import datetime
from aerofiles.igc.reader import Reader

from OpenSoar.thermals.flight_phases import FlightPhases
from OpenSoar.utilities.helper_functions import double_iterator, seconds_time_difference


class TestFlightPhases(unittest.TestCase):

    def test_all_phases(self):

        reader = Reader()

        cwd = os.path.dirname(__file__)
        file_path = os.path.join(cwd, '..', 'example.igc')

        with open(file_path, 'r') as f:
            parsed_igc_file = reader.read(f)

        trace_errors, trace = parsed_igc_file['fix_records']

        start_index = 1168
        last_tp_index = 3240
        phases = FlightPhases('pysoar', trace[start_index:last_tp_index+1])

        all_phases = phases.all_phases()

        # Check if end fixes are the same as the start fixes of next phase
        for phase, next_phase in double_iterator(all_phases):
            self.assertEqual(phase['end_fix'], next_phase['start_fix'])

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

        # check same number of phases
        self.assertEqual(len(all_phases), len(pysoar_phase_start_times))

        # check if start times of phases are within 2 seconds
        for phase, pysoar_phase_start_time in zip(all_phases, pysoar_phase_start_times):
            time_diff = seconds_time_difference(phase['start_fix']['time'], pysoar_phase_start_time)
            self.assertLessEqual(abs(time_diff), 2)
