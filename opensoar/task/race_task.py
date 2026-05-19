import datetime

from opensoar.task.task import Task
from opensoar.utilities.helper_functions import calculate_distance_bearing, double_iterator

class RaceTask(Task):
    """
    Race task.
    """

    def __init__(self, waypoints, timezone=None, start_opening=None, start_time_buffer=0, multistart=False):
        """
        :param waypoints:           see super()
        :param timezone:            see super()
        :param start_opening:       see super()
        :param start_time_buffer:   see super()
        :param multistart:          see super()
        """
        super().__init__(waypoints, timezone, start_opening, start_time_buffer, multistart)

        self.distances = self.calculate_task_distances()

    def __eq__(self, other):
        return super().__eq__(other)

    @property
    def total_distance(self):
        return sum(self.distances)

    def calculate_task_distances(self):

        distances = list()
        for leg in range(self.no_legs):

            begin = self.waypoints[leg]
            end = self.waypoints[leg+1]  # next is built in name
            distance, _ = calculate_distance_bearing(begin.fix, end.fix)

            if begin.distance_correction == "shorten_legs":
                if end.distance_correction == "shorten_legs":
                    distance = Task.distance_shortened_leg(distance, begin, end, "current")
                    distance = Task.distance_shortened_leg(distance, begin, end, "end")
                elif end.distance_correction == "move_tp":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "end")
                    distance = Task.distance_shortened_leg(distance, begin, end, "current")
                elif end.distance_correction is None:
                    distance = Task.distance_shortened_leg(distance, begin, end, "current")
                else:
                    raise ValueError("This distance correction does not exist: %s" % end.distance_correction)

            elif begin.distance_correction == "move_tp":
                if end.distance_correction == "shorten_legs":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "begin")
                    distance = Task.distance_shortened_leg(distance, begin, end, "end")
                elif end.distance_correction == "move_tp":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "begin")
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "both_end")
                elif end.distance_correction is None:
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "begin")
                else:
                    raise ValueError("This distance correction does not exist: %s" % end.distance_correction)

            elif begin.distance_correction is None:
                if end.distance_correction == "shorten_legs":
                    distance = Task.distance_shortened_leg(distance, begin, end, "end")
                elif end.distance_correction == "move_tp":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "end")
                elif end.distance_correction is None:
                    pass
                else:
                    raise ValueError("This distance correction does not exist: %s" % end.distance_correction)

            else:
                raise ValueError("This distance correction does not exist: %s" % self.waypoints[leg].distance_correction)

            distances.append(distance)

        return distances

    def apply_rules(self, trace):

        fixes, outlanding_fix = self.determine_trip_fixes(trace)
        distances = self.determine_trip_distances(fixes, outlanding_fix)
        refined_start = self.determine_refined_start(trace, fixes)
        finish_time = fixes[-1]['datetime']
        sector_fixes = []  # not applicable for race tasks
        return fixes, refined_start, outlanding_fix, distances, finish_time, sector_fixes

    def determine_trip_fixes(self, trace, _allow_late_restart=True):

        leg = -1
        enl_first_fix = None
        enl_registered = False

        fixes = list()
        start_fixes = list()
        restart_candidates = []  # trace indices where started() fired at leg > 0

        for pair_idx, (fix_minus1, fix) in enumerate(double_iterator(trace)):

            if not enl_registered and self.enl_value_exceeded(fix):
                if enl_first_fix is None:
                    enl_first_fix = fix_minus1

                enl_time = (fix['datetime'] - enl_first_fix['datetime']).total_seconds()
                enl_registered = enl_registered or self.enl_time_exceeded(enl_time)
            elif not enl_registered:
                enl_first_fix = None

            if self.start_opening is None:
                after_start_opening = True
            else:
                after_start_opening = self.start_opening + datetime.timedelta(seconds=self.start_time_buffer) < fix['datetime']

            if leg == -1 and after_start_opening:
                if self.started(fix_minus1, fix):
                    fixes.append(fix_minus1)
                    start_fixes.append(fix_minus1)
                    leg += 1
                    enl_first_fix = None
                    enl_registered = False
            elif leg == 0:
                if self.started(fix_minus1, fix):  # restart
                    fixes[0] = fix_minus1
                    start_fixes.append(fix_minus1)
                    enl_first_fix = None
                    enl_registered = False
                if self.finished_leg(leg, fix_minus1, fix) and not enl_registered:
                    fixes.append(fix)
                    leg += 1
            elif 0 < leg < self.no_legs:
                if _allow_late_restart and self.started(fix_minus1, fix):
                    # Collect as challenger candidate; do not reset current attempt.
                    # pair_idx == index of fix_minus1 in trace (double_iterator pair i → trace[i]).
                    restart_candidates.append(pair_idx)
                elif self.finished_leg(leg, fix_minus1, fix) and not enl_registered:
                    fixes.append(fix)
                    leg += 1

        enl_fix = enl_first_fix if enl_registered else None

        orig_outlanding = None
        if len(fixes) != len(self.waypoints):
            orig_outlanding = self.determine_outlanding_fix(trace, fixes, start_fixes, enl_fix)

        if not restart_candidates:
            return fixes, orig_outlanding

        # Compare original attempt with every challenger by total scored distance.
        orig_distance = sum(self.determine_trip_distances(fixes, orig_outlanding)) if fixes else 0
        best_fixes, best_outlanding, best_distance = fixes, orig_outlanding, orig_distance

        for restart_idx in restart_candidates:
            c_fixes, c_outlanding = self.determine_trip_fixes(
                trace[restart_idx:], _allow_late_restart=False
            )
            if not c_fixes:
                continue
            c_distance = sum(self.determine_trip_distances(c_fixes, c_outlanding))
            if c_distance >= best_distance:
                best_fixes, best_outlanding, best_distance = c_fixes, c_outlanding, c_distance

        return best_fixes, best_outlanding

    def determine_outlanding_fix(self, trace, fixes, start_fixes, enl_fix):

        outlanding_leg = len(fixes) - 1

        # check if there is an actual outlanding
        if len(fixes) == len(self.waypoints):
            return None

        # determine range within trace to be examined for outlanding fix
        last_tp_i = trace.index(fixes[-1]) if outlanding_leg != 0 else trace.index(start_fixes[0])
        if enl_fix is not None:
            last_index = trace.index(enl_fix)
        else:
            last_index = len(trace) - 1

        # find fix which maximizes the distance
        outlanding_fix = max(trace[last_tp_i:last_index + 1],
                             key=lambda x: self.determine_outlanding_distance(outlanding_leg, x))

        max_distance = self.determine_outlanding_distance(outlanding_leg, outlanding_fix)
        if max_distance < 0:  # no out-landing fix that improves the distance
            if enl_fix is not None:
                outlanding_fix = enl_fix
            else:
                outlanding_fix = trace[-1]

        return outlanding_fix

    def determine_outlanding_distance(self, outlanding_leg, fix):

        previous_waypoint = self.waypoints[outlanding_leg]
        next_waypoint = self.waypoints[outlanding_leg + 1]

        # outlanding distance = distance between tps minus distance from next tp to outlanding
        outlanding_dist, _ = calculate_distance_bearing(previous_waypoint.fix, next_waypoint.fix)
        outlanding_dist -= calculate_distance_bearing(next_waypoint.fix, fix)[0]

        return outlanding_dist if outlanding_dist > 0 else 0

    def determine_trip_distances(self, fixes, outlanding_fix):

        distances = list()
        for leg, fix in enumerate(fixes[1:]):
            distances.append(self.distances[leg])

        if outlanding_fix is not None:
            outlanding_leg = len(fixes) - 1
            distances.append(self.determine_outlanding_distance(outlanding_leg, outlanding_fix))

        return distances

    def finished_leg(self, leg, fix1, fix2):
        """Determines whether leg is finished."""

        next_waypoint = self.waypoints[leg + 1]
        if next_waypoint.is_line:
            return next_waypoint.crossed_line(fix1, fix2)
        else:
            return next_waypoint.outside_sector(fix1) and next_waypoint.inside_sector(fix2)
