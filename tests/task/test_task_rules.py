import os
import datetime
import unittest
from unittest.mock import patch

from tests.task.helper_functions import get_task


class TestRestartAfterTurnpoint(unittest.TestCase):
    """
    FAI SC3A §7.4.3.6: multiple valid starts → scored using the start that yields the best score.
    A start made after a properly completed task is not valid.

    Tests call determine_trip_fixes directly with mocked started/finished_leg so that
    the control-flow scenarios can be driven without needing real IGC flight geometry.
    The side_effect lists are ordered by the exact call sequence produced by the implementation:
      - main evaluation calls first, then challenger sub-evaluation calls.
    """

    cwd = os.path.dirname(__file__)
    # 4-leg race task (no_legs=4, 5 waypoints)
    igc_path = os.path.join(cwd, '..', 'igc_files', 'race_task_completed.igc')

    def _make_fix(self, seconds):
        return {
            'datetime': datetime.datetime(2024, 1, 1, 12, 0, seconds,
                                          tzinfo=datetime.timezone.utc),
            'lat': 52.0,
            'lon': 6.0,
        }

    def _load_task(self):
        task = get_task(self.igc_path)
        task.start_opening = None  # disable time-of-day filtering
        return task

    def test_restart_after_tp_leads_to_task_completion(self):
        """
        Case 2: pilot starts, rounds TP1, turns back, restarts, then completes the task.
        The restart attempt scores because it achieves the full task distance.

        Main evaluation (9 pairs over 10 fixes):
          started calls:  T F F T F F F F F   (True at pair 0 = first start; True at pair 3 = candidate)
          finished_leg:   T F F F F F F        (True at pair 1 = TP1 in main; rest False → outlanding leg 1)

        Challenger sub-trace = trace[3:] (6 pairs, _allow_late_restart=False):
          started calls:  T F                  (True at pair 0 = challenger start; pair 1 = no leg-0 restart)
          finished_leg:   T T T T              (TP1 TP2 TP3 TP4 → task complete; pair 5 at leg=4 skipped)
        """
        task = self._load_task()
        trace = [self._make_fix(i) for i in range(10)]

        started_values = [True, False, False, True, False, False, False, False, False,
                          True, False]
        finished_leg_values = [True, False, False, False, False, False, False,
                               True, True, True, True]

        with patch.object(task, 'started', side_effect=started_values), \
             patch.object(task, 'finished_leg', side_effect=finished_leg_values):
            fixes, outlanding_fix = task.determine_trip_fixes(trace)

        self.assertEqual(fixes[0], trace[3], 'restart fix should be the start fix')
        self.assertIsNone(outlanding_fix)
        self.assertEqual(len(fixes), 5)
        self.assertGreater(
            sum(task.determine_trip_distances(fixes, None)),
            0,
        )

    def test_first_attempt_wins_when_further_along(self):
        """
        Case 3: pilot starts, rounds TP1 and TP2, restarts, but only reaches mid-leg-1.
        The first attempt scores because it achieved more distance.

        Main evaluation (9 pairs):
          started:      T F F T F F F F F   (pair 0 = start; pair 3 = candidate at leg 2)
          finished_leg: T T F F F F F        (pair 1 = TP1, pair 2 = TP2; rest False → outlanding leg 2)

        Challenger trace[3:] (6 pairs, _allow_late_restart=False):
          started:      T F F F F F          (pair 0 = challenger start; pairs 1-5 = no leg-0 restart)
          finished_leg: F F F F F            (challenger completes 0 legs → outlanding leg 0)
        """
        task = self._load_task()
        trace = [self._make_fix(i) for i in range(10)]

        started_values = [True, False, False, True, False, False, False, False, False,
                          True, False, False, False, False, False]
        finished_leg_values = [True, True, False, False, False, False, False,
                               False, False, False, False, False]

        with patch.object(task, 'started', side_effect=started_values), \
             patch.object(task, 'finished_leg', side_effect=finished_leg_values):
            fixes, outlanding_fix = task.determine_trip_fixes(trace)

        self.assertEqual(fixes[0], trace[0], 'original start fix should be used')
        self.assertEqual(len(fixes), 3,
                         'start + TP1 + TP2 should be in fixes (2 completed legs)')
        first_attempt_distance = sum(task.determine_trip_distances(fixes, outlanding_fix))
        self.assertGreater(first_attempt_distance, 0)

    def test_incidental_start_crossing_mid_task_does_not_interrupt_completion(self):
        """
        Case 6: pilot crosses the start area incidentally between TP2 and TP3 while flying
        the full task. The full task still completes; the incidental crossing is NOT a reset.

        Main evaluation (9 pairs):
          started:      T F F T F F             (pair 0 = start; pair 3 = incidental crossing at leg 2)
          finished_leg: T T T T                  (TP1 TP2 TP3 TP4 → task complete; pairs 6-8 at leg=4 skipped)

        Challenger trace[3:] (6 pairs, _allow_late_restart=False):
          started:      T F                      (pair 0 = challenger start)
          finished_leg: T T F F F                (challenger only completes TP1+TP2 → outlanding)
        """
        task = self._load_task()
        trace = [self._make_fix(i) for i in range(10)]

        started_values = [True, False, False, True, False, False,
                          True, False]
        finished_leg_values = [True, True, True, True,
                               True, True, False, False, False]

        with patch.object(task, 'started', side_effect=started_values), \
             patch.object(task, 'finished_leg', side_effect=finished_leg_values):
            fixes, outlanding_fix = task.determine_trip_fixes(trace)

        self.assertEqual(len(fixes), 5, 'task should be completed despite incidental crossing')
        self.assertIsNone(outlanding_fix)
        self.assertEqual(fixes[0], trace[0], 'original start should be used')

    def test_start_after_task_completion_is_ignored(self):
        """
        Cases 4 & 5: once the task is fully completed (leg == no_legs), the condition
        `0 < leg < no_legs` is False, so started() is never evaluated and no restart
        candidate is collected. The completed result is returned unchanged.

        Main evaluation: task completed in pairs 0-4 (legs 0-3 each done). Pairs 5-8
        are at leg=4=no_legs → no calls to started or finished_leg.
        """
        task = self._load_task()
        trace = [self._make_fix(i) for i in range(10)]

        started_values = [True, False, False, False, False]
        finished_leg_values = [True, True, True, True]

        with patch.object(task, 'started', side_effect=started_values), \
             patch.object(task, 'finished_leg', side_effect=finished_leg_values):
            fixes, outlanding_fix = task.determine_trip_fixes(trace)

        self.assertEqual(fixes[0], trace[0])
        self.assertEqual(len(fixes), 5)
        self.assertIsNone(outlanding_fix)
