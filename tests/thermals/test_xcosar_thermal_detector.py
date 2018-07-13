import unittest
import os

import datetime

from opensoar.thermals.xcsoar_thermal_detector import XCSoarThermalDetector
from opensoar.utilities.helper_functions import double_iterator
from tests.task.helper_functions import get_trace


class TestXCSoarThermalDetector(unittest.TestCase):

    file_dir = os.path.dirname(__file__)
    igc_path = os.path.join(file_dir, '..', 'igc_files', 'race_task_completed.igc')

    trace = get_trace(igc_path)

    xcsoar_detector = XCSoarThermalDetector()
    phases = xcsoar_detector.analyse(trace)

    def test_continuous_phases(self):
        # Check if end fixes are the same as the start fixes of next phase
        for phase, next_phase in double_iterator(self.phases):
            self.assertEqual(phase.fixes[-1], next_phase.fixes[0])

        # check every even phase is cruise, every odd fase is not cruise
        for i, phase in enumerate(self.phases):
            if i % 2 == 0:
                self.assertTrue(phase.is_cruise)
            else:
                self.assertFalse(phase.is_cruise)

    def test_phase_start_times(self):

        for phase in self.phases:
            print(phase.fixes[0]['time'])
        #
        # expected_phase_start_times = [
        #     datetime.time(11, 34, 52),
        #     datetime.time(11, 36, 32),
        #     datetime.time(11, 45, 14),
        #     datetime.time(11, 48, 18),
        #     datetime.time(11, 55, 54),
        #     datetime.time(11, 57, 6),
        # ]
        #
        # for phase, expected_phase_start in zip(self.phases[1:7], expected_phase_start_times):
        #     self.assertEqual(expected_phase_start, phase.fixes[0]['time'])
