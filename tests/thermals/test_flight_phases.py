import os
import unittest

from aerofiles.igc.reader import Reader

from OpenSoar.thermals.flight_phases import FlightPhases


class TestFlightPhases(unittest.TestCase):

    def test_all_phases(self):

        reader = Reader()

        cwd = os.path.dirname(__file__)
        file_path = os.path.join(cwd, '..', 'example.igc')

        with open(file_path, 'r') as f:
            parsed_igc_file = reader.read(f)

        trace_errors, trace = parsed_igc_file['fix_records']
        phases = FlightPhases('pysoar', trace)

        all_phases = phases.all_phases()

        # todo: finish this test
        # - check if end time is always equal to start time of next entry
        # - implement that only part of trace is used
        # - check with PySoar results -> number of phases
