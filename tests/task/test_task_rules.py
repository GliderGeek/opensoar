import os
import datetime
import unittest
from unittest.mock import patch

from tests.task.helper_functions import get_task


class TestRestartAfterTurnpoint(unittest.TestCase):
    """
    FAI SC3A §7.4.3.6: multiple valid starts → scored using the start that yields the best score.
    A start after a properly completed task is not valid.

    Tests call determine_trip_fixes directly with mocked started/finished_leg so that
    the control-flow scenarios can be driven without needing real IGC flight geometry.

    Mock call convention
    --------------------
    started(f1, f2) is called once per pair when:
      - leg == -1: every pair, waiting for the first start
      - leg == 0:  every pair, checking for a leg-0 restart (unconditional `if`)
      - 0 < leg < no_legs AND _allow_late_restart=True: checking for a late restart candidate

    finished_leg(leg, f1, f2) is called once per pair when:
      - leg == 0: always, in a separate `if` block that runs regardless of whether started() fired
      - 0 < leg < no_legs AND started() returned False: in the `elif` branch, so NOT called
        when started() returned True on the same pair
      - Never at leg == -1 (before start) or leg == no_legs (task complete)

    When _allow_late_restart=False (challenger sub-evaluations): started() is not called at
    leg > 0, so finished_leg() fires at every pair in that range.

    The side_effect lists are ordered by the exact call sequence: main evaluation first,
    then challenger sub-evaluation (if any).
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

        Main evaluation — trace[0:] (9 pairs):
          pair  leg  started  finished_leg  note
             0   -1    True        —        first start → fixes=[trace[0]], leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1   False      False
             3    1    True        —        late start → candidate at pair_idx=3
             4    1   False      False
             5    1   False      False
             6    1   False      False
             7    1   False      False
             8    1   False      False
          Original result: outlanding on leg 1

        Challenger — trace[3:] (6 pairs, _allow_late_restart=False):
          pair  leg  started  finished_leg  note
             0   -1    True        —        start → leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1     —        True       TP2 → leg=2  (started not called: _allow_late_restart=False)
             3    2     —        True       TP3 → leg=3
             4    3     —        True       TP4 → leg=4=no_legs, task complete
             5    4     —          —        task done, no branch matches
          Challenger result: task complete → wins

        → started_values (11): main 9 + challenger 2
        → finished_leg   (11): main 7 (pairs 0 and 3 skipped) + challenger 4 (pairs 0 and 5 skipped)
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

        Main evaluation — trace[0:] (9 pairs):
          pair  leg  started  finished_leg  note
             0   -1    True        —        first start → leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1   False      True       TP2 → leg=2
             3    2    True        —        late start → candidate at pair_idx=3
             4    2   False      False
             5    2   False      False
             6    2   False      False
             7    2   False      False
             8    2   False      False
          Original result: outlanding on leg 2 (TP1 + TP2 rounded)

        Challenger — trace[3:] (6 pairs, _allow_late_restart=False):
          pair  leg  started  finished_leg  note
             0   -1    True        —        start → leg=0
             1    0   False      False      no restart; no TP1
             2    0   False      False
             3    0   False      False
             4    0   False      False
             5    0   False      False
          Challenger result: outlanding on leg 0 (~0 km; all fixes share same lat/lon)

        → started_values (15): main 9 + challenger 6
        → finished_leg   (12): main 7 (pairs 0 and 3 skipped) + challenger 5 (pair 0 skipped)
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

        Main evaluation — trace[0:] (9 pairs):
          pair  leg  started  finished_leg  note
             0   -1    True        —        first start → leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1   False      True       TP2 → leg=2
             3    2    True        —        incidental crossing → candidate at pair_idx=3
             4    2   False      True       TP3 → leg=3
             5    3   False      True       TP4 → leg=4=no_legs, task complete
             6    4     —          —        task done
             7    4     —          —
             8    4     —          —
          Original result: task complete (outlanding_fix=None)

        Challenger — trace[3:] (6 pairs, _allow_late_restart=False):
          pair  leg  started  finished_leg  note
             0   -1    True        —        start → leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1     —        True       TP2 → leg=2
             3    2     —        False
             4    2     —        False
             5    2     —        False
          Challenger result: outlanding on leg 2 → original (full task) wins

        → started_values (8): main 6 (pairs 6-8 at leg=no_legs skipped) + challenger 2
        → finished_leg   (9): main 4 (pairs 0, 3, 6, 7, 8 skipped) + challenger 5 (pair 0 skipped)
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

        Main evaluation — trace[0:] (9 pairs):
          pair  leg  started  finished_leg  note
             0   -1    True        —        first start → leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1   False      True       TP2 → leg=2
             3    2   False      True       TP3 → leg=3
             4    3   False      True       TP4 → leg=4=no_legs, task complete
             5    4     —          —        0<4<4 is False → started() never called; no candidates
             6    4     —          —
             7    4     —          —
             8    4     —          —
          No restart candidates → no challengers.

        → started_values (5): pairs 5-8 at leg=no_legs generate no calls
        → finished_leg   (4): pair 0 (leg=-1) skipped
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

    def test_both_complete_later_start_wins(self):
        """
        Both the original start and the restart complete all legs with the same total
        distance (race-task legs are fixed). The later restart must be selected — it
        achieves the same distance in less time, giving a higher race speed.

        Main evaluation — trace[0:] (9 pairs):
          pair  leg  started  finished_leg  note
             0   -1    True        —        first start → fixes=[trace[0]], leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1    True        —        late start → candidate at pair_idx=2
             3    1   False      True       TP2 → leg=2
             4    2   False      True       TP3 → leg=3
             5    3   False      True       TP4 → leg=4=no_legs, task complete
             6-8  4     —          —        0<4<4 False → no calls
          Original result: task complete, distance=D

        Challenger — trace[2:] (8 fixes, 7 pairs, _allow_late_restart=False):
          pair  leg  started  finished_leg  note
             0   -1    True        —        start → fixes=[trace[2]], leg=0
             1    0   False      True       no restart; TP1 → leg=1
             2    1     —        True       TP2 → leg=2  (started not called)
             3    2     —        True       TP3 → leg=3
             4    3     —        True       TP4 → leg=4=no_legs, task complete
             5-6  4     —          —        no calls
          Challenger result: task complete, distance=D (same fixed legs)

        c_distance == best_distance → >= picks challenger; > would keep original (bug).

        → started_values (8):   main 6 (pairs 0-5) + challenger 2 (pairs 0-1)
        → finished_leg   (8):   main 4 (pairs 1,3,4,5) + challenger 4 (pairs 1-4)
        """
        task = self._load_task()
        trace = [self._make_fix(i) for i in range(10)]

        started_values = [True, False, True, False, False, False,
                          True, False]
        finished_leg_values = [True, True, True, True,
                               True, True, True, True]

        with patch.object(task, 'started', side_effect=started_values), \
             patch.object(task, 'finished_leg', side_effect=finished_leg_values):
            fixes, outlanding_fix = task.determine_trip_fixes(trace)

        self.assertEqual(fixes[0], trace[2], 'later restart should be used when both complete')
        self.assertIsNone(outlanding_fix)
        self.assertEqual(len(fixes), 5)
