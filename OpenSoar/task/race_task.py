from datetime import timedelta

from OpenSoar.task.task import Task
from OpenSoar.utilities.helper_functions import calculate_distance, seconds_time_difference, double_iterator


class RaceTask(Task):

    def __init__(self, waypoints, start_opening=None, start_time_buffer=0):
        super().__init__(waypoints, start_opening, start_time_buffer)

        self.distances = self.calculate_task_distances()

    @property
    def total_distance(self):
        return sum(self.distances)

    def calculate_task_distances(self):

        distances = list()
        for leg in range(self.no_legs):

            begin = self.waypoints[leg]
            end = self.waypoints[leg+1]  # next is built in name
            distance = calculate_distance(begin.fix, end.fix)

            if begin.distance_correction is "shorten_legs":
                if end.distance_correction is "shorten_legs":
                    distance = Task.distance_shortened_leg(distance, begin, end, "begin")
                    distance = Task.distance_shortened_leg(distance, begin, end, "end")
                elif end.distance_correction is "move_tp":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "end")
                    distance = Task.distance_shortened_leg(distance, begin, end, "begin")
                elif end.distance_correction is None:
                    distance = Task.distance_shortened_leg(distance, begin, end, "begin")
                else:
                    raise ValueError("This distance correction does not exist: %s" % end.distance_correction)

            elif begin.distance_correction is "move_tp":
                if end.distance_correction is "shorten_legs":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "begin")
                    distance = Task.distance_shortened_leg(distance, begin, end, "end")
                elif end.distance_correction is "move_tp":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "begin")
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "both_end")
                elif end.distance_correction is None:
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "begin")
                else:
                    raise ValueError("This distance correction does not exist: %s" % end.distance_correction)

            elif begin.distance_correction is None:
                if end.distance_correction is "shorten_legs":
                    distance = Task.distance_shortened_leg(distance, begin, end, "end")
                elif end.distance_correction is "move_tp":
                    distance = Task.distance_moved_turnpoint(distance, begin, end, "end")
                elif end.distance_correction is None:
                    pass
                else:
                    raise ValueError("This distance correction does not exist: %s" % end.distance_correction)

            else:
                raise ValueError("This distance correction does not exist: %s" % self.waypoints[leg].distance_correction)

            distances.append(distance)

        return distances

    def apply_rules(self, trace, trip, enl_indices):

        fixes, start_fixes, outlanding_fix = self.determine_trip_fixes(trace, enl_indices)
        distances = self.determine_trip_distances(fixes, outlanding_fix)
        refined_start = self.determine_refined_start(trace, fixes)

        trip.fixes = fixes
        trip.start_fixes = start_fixes
        trip.outlanding_fix = outlanding_fix
        trip.distances = distances
        trip.refined_start_time = refined_start

    def determine_trip_fixes(self, trace, enl_indices):

        leg = -1
        enl_first_fix = None
        enl_registered = False

        fixes = list()
        start_fixes = list()
        for fix_minus1, fix in double_iterator(trace):

            t = fix['time']

            if enl_indices is not None \
                    and not enl_registered \
                    and self.enl_value_exceeded(fix, enl_indices):

                if enl_first_fix is None:
                    enl_first_fix = fix_minus1
                enl_time = seconds_time_difference(enl_first_fix, fix)
                enl_registered = enl_registered or self.enl_time_exceeded(enl_time)
            elif not enl_registered:
                enl_first_fix = None

            if self.start_opening is None:
                after_start_opening = True
            else:
                after_start_opening = t + timedelta(seconds=self.start_time_buffer) > self.start_opening

            if leg == -1 and after_start_opening:
                if self.started(fix_minus1, fix):
                    start_fix = fix
                    fixes.append(start_fix)
                    start_fixes.append(start_fix)
                    leg += 1
                    enl_first_fix = None
                    enl_registered = False
            elif leg == 0:
                if self.started(fix_minus1, fix):  # restart
                    start_fix = fix
                    fixes[0] = start_fix
                    start_fixes.append(start_fix)
                    enl_first_fix = None
                    enl_registered = False
                if self.finished_leg(leg, fix_minus1, fix) and not enl_registered:
                    fixes.append(fix)
                    leg += 1
            elif 0 < leg < self.no_legs:
                if self.finished_leg(leg, fix_minus1, fix) and not enl_registered:
                    fixes.append(fix)
                    leg += 1

        enl_fix = enl_first_fix if enl_registered else None

        outlanding_fix = None
        if len(fixes) is not len(self.waypoints):
            outlanding_fix = self.determine_outlanding_fix(trace, fixes, start_fixes, enl_fix)

        return fixes, start_fixes, outlanding_fix

    def determine_outlanding_fix(self, trace, fixes, start_fixes, enl_fix):

        if len(fixes) == len(self.waypoints):
            raise None

        outlanding_leg = len(fixes) - 1
        last_tp_i = trace.index(fixes[-1]) if outlanding_leg != 0 else trace.index(start_fixes[0])
        if enl_fix is not None:
            enl_i = trace.index(enl_fix)
            last_index = enl_i
        else:
            last_index = len(trace) - 1

        # todo: is it possible to simplify these max function? with lambda?
        max_dist = 0
        outlanding_fix = None

        for fix in trace[last_tp_i:last_index + 1]:
            outlanding_dist = self.determine_outlanding_distance(outlanding_leg, fix)

            if outlanding_dist > max_dist:
                max_dist = outlanding_dist
                outlanding_fix = fix

        if outlanding_fix is None:  # no out-landing fix that improves the distance
            if enl_fix is not None:
                outlanding_fix = enl_fix
            else:
                outlanding_fix = trace[-1]

        return outlanding_fix

    def determine_outlanding_distance(self, outlanding_leg, fix):

        previous_waypoint = self.waypoints[outlanding_leg]
        next_waypoint = self.waypoints[outlanding_leg + 1]

        # outlanding distance = distance between tps minus distance from next tp to outlanding
        outlanding_dist = calculate_distance(previous_waypoint.fix, next_waypoint.fix)
        outlanding_dist -= calculate_distance(next_waypoint.fix, fix)

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
