from OpenSoar.task.task import Task
from OpenSoar.utilities.helper_functions import calculate_distance, seconds_time_difference, double_iterator


class RaceTask(Task):

    def __init__(self, waypoints, multi_start, start_opening, utc_diff):
        super().__init__(waypoints, multi_start, start_opening, utc_diff)

        self.distances = self.calculate_task_distances()

    @property
    def total_distance(self):
        return sum(self.distances)

    def calculate_task_distances(self):

        distances = []

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

    def apply_rules(self, trace, trip, trace_settings):

        self.determine_trip_fixes(trip, trace, trace_settings)
        self.determine_trip_distances(trip)
        self.refine_start(trip, trace)

    def determine_trip_fixes(self, trip, trace, trace_settings):

        leg = -1
        enl_time = 0
        enl_first_fix = None
        enl_registered = False

        for fix_minus1, fix in double_iterator(trace):

            t = fix['time']

            if trace_settings['enl_indices'] is not None \
                    and not enl_registered \
                    and self.enl_value_exceeded(fix, trace_settings['enl_indices']):

                if enl_time == 0:
                    enl_first_fix = fix_minus1
                enl_time += seconds_time_difference(fix_minus1, fix)
                enl_registered = enl_registered or self.enl_time_exceeded(enl_time)
            elif not enl_registered:
                enl_time = 0
                enl_first_fix = None

            start_time_buffer = 15
            if leg == -1 and t + start_time_buffer > self.start_opening:
                if self.started(fix_minus1, fix):
                    start_fix = fix
                    trip.fixes.append(start_fix)
                    trip.start_fixes.append(start_fix)
                    leg += 1
                    enl_time = 0
                    enl_first_fix = None
                    enl_registered = False
            elif leg == 0:
                if self.started(fix_minus1, fix):  # restart
                    start_fix = fix
                    trip.fixes[0] = start_fix
                    trip.start_fixes.append(start_fix)
                    enl_time = 0
                    enl_first_fix = None
                    enl_registered = False
                if self.finished_leg(leg, fix_minus1, fix) and not enl_registered:
                    trip.fixes.append(fix)
                    leg += 1
            elif 0 < leg < self.no_legs:
                if self.finished_leg(leg, fix_minus1, fix) and not enl_registered:
                    trip.fixes.append(fix)
                    leg += 1

        if enl_registered:
            trip.enl_fix = enl_first_fix

        if len(trip.fixes) is not len(self.waypoints):
            self.determine_outlanding_fix(trip, trace)

    def determine_outlanding_fix(self, trip, trace):

        last_tp_i = trace.index(trip.fixes[-1]) if trip.outlanding_leg() != 0 else trace.index(trip.start_fixes[0])
        if trip.enl_fix is not None:
            enl_i = trace.index(trip.enl_fix)

        max_dist = 0
        outlanding_fix = None
        for i, fix in enumerate(trace):

            if (trip.enl_fix is None and last_tp_i < i) or (trip.enl_fix is not None and last_tp_i < i < enl_i):

                outlanding_dist = self.determine_outlanding_distance(trip.outlanding_leg(), fix)

                if outlanding_dist > max_dist:
                    max_dist = outlanding_dist
                    outlanding_fix = fix

        if outlanding_fix is None:  # no out-landing fix that improves the distance
            if trip.enl_fix is not None:
                trip.outlanding_fix = trip.enl_fix
            else:
                trip.outlanding_fix = trace[-1]
        else:
            trip.outlanding_fix = outlanding_fix

    def determine_outlanding_distance(self, outlanding_leg, fix):

        task_pointM1 = self.waypoints[outlanding_leg]
        task_point = self.waypoints[outlanding_leg + 1]

        # outlanding distance = distance between tps minus distance from next tp to outlanding
        outlanding_dist = calculate_distance(task_pointM1.fix, task_point.fix)
        outlanding_dist -= calculate_distance(task_point.fix, fix)

        return outlanding_dist if outlanding_dist > 0 else 0

    def determine_trip_distances(self, trip):

        for leg, fix in enumerate(trip.fixes[1:]):
            trip.distances.append(self.distances[leg])

        if trip.outlanding_fix is not None:
            trip.distances.append(self.determine_outlanding_distance(trip.outlanding_leg(), trip.outlanding_fix))

    def finished_leg(self, leg, fix1, fix2):
        """Determines whether leg is finished."""

        next_waypoint = self.waypoints[leg + 1]
        if next_waypoint.line:
            return next_waypoint.crossed_line(fix1, fix2)
        else:
            return next_waypoint.outside_sector(fix1) and next_waypoint.inside_sector(fix2)
