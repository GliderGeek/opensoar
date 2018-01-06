import datetime

from OpenSoar.task.task import Task
from OpenSoar.utilities.helper_functions import double_iterator, calculate_distance, seconds_time_difference, \
    calculate_bearing, calculate_destination, seconds_time_difference_fixes, add_times


class AAT(Task):

    def __init__(self, waypoints, t_min: datetime.time, start_opening=None, start_time_buffer=0):
        super().__init__(waypoints, start_opening, start_time_buffer)

        self._t_min = t_min
        self._nominal_distances = self._calculate_nominal_distances()

    def _calculate_nominal_distances(self):
        distances = list()
        for start_waypoint, end_waypoint in double_iterator(self.waypoints):
            distance = calculate_distance(start_waypoint.fix, end_waypoint.fix)
            distances.append(distance)
        return distances

    def apply_rules(self, trace):
        fixes, outlanding_fix = self._calculate_trip_fixes(trace)
        start_time = self.determine_refined_start(trace, fixes)
        distances = self._determine_trip_distances(fixes, outlanding_fix)
        finish_time = self._determine_finish_time(fixes, outlanding_fix)
        return fixes, start_time, outlanding_fix, distances, finish_time

    def _determine_finish_time(self, fixes, outlanding_fix):
        total_trip_time = seconds_time_difference_fixes(fixes[0], fixes[-1])
        minimum_trip_time = seconds_time_difference(datetime.time(0, 0), self._t_min)
        if outlanding_fix is None and total_trip_time < minimum_trip_time:
            finish_time = add_times(fixes[0]['time'], self._t_min)
        else:
            finish_time = fixes[-1]['time']
        return finish_time

    def _calculate_trip_fixes(self, trace):

        sector_fixes, enl_outlanding_fix = self._get_sector_fixes(trace)
        reduced_sector_fixes = self._reduce_sector_fixes(sector_fixes, max_fixes_sector=300)

        outlanded = len(sector_fixes) != self.no_legs+1

        if outlanded:
            outside_sector_fixes = self._get_outside_sector_fixes(trace, sector_fixes, enl_outlanding_fix)
            reduced_outside_sector_fixes = self._reduce_fixes(outside_sector_fixes, max_fixes=300)

            max_distance_fixes = self._compute_max_distance_fixes(reduced_sector_fixes, outlanded, reduced_outside_sector_fixes)

            refined_sector_fixes, refined_outside_sector_fixes = self._refine_max_distance_fixes(sector_fixes, max_distance_fixes, outlanded, outside_sector_fixes)
            max_distance_fixes = self._compute_max_distance_fixes(refined_sector_fixes, outlanded, refined_outside_sector_fixes)

            fixes = max_distance_fixes[:-1]
            outlanding_fix = max_distance_fixes[-1]
        else:
            max_distance_fixes = self._compute_max_distance_fixes(reduced_sector_fixes, outlanded)
            refined_sector_fixes, _ = self._refine_max_distance_fixes(sector_fixes, max_distance_fixes, outlanded)

            max_distance_fixes = self._compute_max_distance_fixes(refined_sector_fixes, outlanded)

            fixes = max_distance_fixes
            outlanding_fix = None

        return fixes, outlanding_fix

    def _determine_trip_distances(self, fixes, outlanding_fix):

        distances = list()
        for leg, (fix1, fix2) in enumerate(double_iterator(fixes)):
            distance = self._calculate_distance_completed_leg(leg, fix1, fix2)
            distances.append(distance)

        if outlanding_fix is not None:
            outlanding_leg = len(fixes) - 1
            distance = self._calculate_distance_outlanding_leg(outlanding_leg, fixes[-1], outlanding_fix)
            distances.append(distance)

        return distances

    def _get_sector_fixes(self, trace):

        # following assumptions are currently in place
        # - outlanding inside sector leads to wrong distance
        # todo: fix this

        current_leg = -1  # not yet started
        sector_fixes = list()
        enl_first_fix = None
        enl_registered = False

        for fix_minus1, fix in double_iterator(trace):

            # check ENL when aircraft logs ENL and no ENL outlanding has taken place
            if not enl_registered and self.enl_value_exceeded(fix):
                if enl_first_fix is None:
                    enl_first_fix = fix

                enl_time = seconds_time_difference_fixes(enl_first_fix, fix)
                if self.enl_time_exceeded(enl_time):
                    enl_registered = True
                    if current_leg > 0:
                        break
            elif not enl_registered:
                enl_first_fix = None

            if current_leg == -1:  # before start
                if self.started(fix_minus1, fix):
                    self._add_aat_sector_fix(sector_fixes, 0, fix_minus1)  # at task start point
                    current_leg = 0
                    enl_registered = False
                    enl_first_fix = None
            elif current_leg == 0:  # first leg, re-start still possible
                if self.started(fix_minus1, fix):  # restart
                    sector_fixes[0] = [fix_minus1]  # at task start point
                    current_leg = 0
                    enl_registered = False
                    enl_first_fix = None
                elif self.waypoints[1].inside_sector(fix_minus1):  # first sector
                    if enl_registered:
                        break  # break when ENL is used and not restarted
                    self._add_aat_sector_fix(sector_fixes, 1, fix_minus1)
                    current_leg += 1
            elif 0 < current_leg < self.no_legs - 1:  # at least second leg, no re-start possible
                if self.waypoints[current_leg].inside_sector(fix_minus1):  # previous waypoint
                    self._add_aat_sector_fix(sector_fixes, current_leg, fix_minus1)
                elif self.waypoints[current_leg + 1].inside_sector(fix_minus1):  # next waypoint
                    self._add_aat_sector_fix(sector_fixes, current_leg + 1, fix_minus1)
                    current_leg += 1
            elif current_leg == self.no_legs - 1:  # last leg
                if self.waypoints[current_leg].inside_sector(fix_minus1):
                    self._add_aat_sector_fix(sector_fixes, current_leg, fix_minus1)
                elif self.finished(fix_minus1, fix):
                    sector_fixes.append([fix])  # at task finish point
                    break

        if enl_registered:
            return sector_fixes, enl_first_fix
        else:
            return sector_fixes, None

    def _reduce_fixes(self, fixes, max_fixes):
        reduction_factor = len(fixes) // max_fixes + 1
        return fixes[0::reduction_factor]

    def _reduce_sector_fixes(self, sector_fixes, max_fixes_sector):
        reduced_sector_fixes = list()
        for sector, fixes in enumerate(sector_fixes):
            reduced_fixes = self._reduce_fixes(fixes, max_fixes_sector)
            reduced_sector_fixes.append(reduced_fixes)

        return reduced_sector_fixes

    def _get_outside_sector_fixes(self, trace, sector_fixes, enl_outlanding_fix):
        # todo: review whether this correctly returns empty list when outlanding inside aat sector
        last_sector_fix = sector_fixes[-1][-1]
        last_sector_index = trace.index(last_sector_fix)

        outside_sector_fixes = list()
        if enl_outlanding_fix is not None:
            enl_outlanding_index = trace.index(enl_outlanding_fix)

            if enl_outlanding_index > last_sector_index:
                outside_sector_fixes = trace[last_sector_index + 1: enl_outlanding_index + 1]
        else:
            outside_sector_fixes = trace[last_sector_index+1:]

        return outside_sector_fixes

    def _add_aat_sector_fix(self, sector_fixes, taskpoint_index, fix):
        if len(sector_fixes) < (taskpoint_index + 1):
            sector_fixes.append([fix])
        else:
            sector_fixes[taskpoint_index].append(fix)

    def _compute_max_distance_fixes(self, sector_fixes, outlanded, outside_sector_fixes=None):

        # to prevent problems with mutable default argument
        if outside_sector_fixes is None:
            outside_sector_fixes = []

        completed_legs = len(sector_fixes) - 1
        distances = self._calculate_distances_between_sector_fixes(completed_legs, outlanded, outside_sector_fixes,
                                                                   sector_fixes)

        # determine index on last sector/outlanding-group with maximum distance
        max_dist = 0
        maximized_dist_index = None
        for index, distance in enumerate(distances[-1]):
            if distance[0] > max_dist:
                max_dist = distance[0]
                maximized_dist_index = index

        if not outlanded:
            last_fix = sector_fixes[-1][maximized_dist_index]
        elif outlanded and outside_sector_fixes:  # outlanding outside aat sector
            last_fix = outside_sector_fixes[maximized_dist_index]
        else:  # outlanding inside aat sector
            last_fix = sector_fixes[-1][maximized_dist_index]
        max_distance_fixes = [last_fix]

        index = maximized_dist_index

        legs = completed_legs if not outlanded else completed_legs + 1
        for leg in list(reversed(range(legs))):
            index = distances[leg + 1][index][1]
            max_distance_fixes.insert(0, sector_fixes[leg][index])

        return max_distance_fixes

    def _calculate_distances_between_sector_fixes(self, completed_legs, outlanded, outside_sector_fixes, sector_fixes):
        distances = [[]] * len(sector_fixes) if not outlanded else [[]] * (len(sector_fixes) + 1)
        distances[0] = [[0, 0]] * len(sector_fixes[0])
        for leg in range(completed_legs):  # successful legs

            distances[leg + 1] = [[0, 0] for _ in range(len(sector_fixes[leg + 1]))]

            for fix2_index, fix2 in enumerate(sector_fixes[leg + 1]):
                for fix1_index, fix1 in enumerate(sector_fixes[leg]):
                    distance = self._calculate_distance_completed_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index] = [total_distance, fix1_index]
        if outlanded and outside_sector_fixes:  # outlanding outside AAT sector

            leg = completed_legs
            distances[leg + 1] = [[0, 0] for _ in range(len(outside_sector_fixes))]
            for fix2_index, fix2 in enumerate(outside_sector_fixes):
                for fix1_index, fix1 in enumerate(sector_fixes[leg]):
                    distance = self._calculate_distance_outlanding_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index] = [total_distance, fix1_index]

        elif outlanded and not outside_sector_fixes:  # outlanding inside AAT sector
            leg = completed_legs
            distances[leg + 1] = [[0, 0] for _ in range(len(sector_fixes[leg]))]
            for fix2_index, fix2 in enumerate(sector_fixes[leg]):
                for fix1_index, fix1 in enumerate(sector_fixes[leg][0:fix2_index]):
                    distance = self._calculate_distance_outlanding_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index] = [total_distance, fix1_index]

        return distances

    def _refine_max_distance_fixes(self, sector_fixes, max_distance_fixes, outlanded, outside_sector_fixes=None):
        """look around fixes whether more precise fixes can be found, increasing the distance"""

        if outside_sector_fixes is None:
            outside_sector_fixes = []

        refinement_fixes = 10
        refined_sector_fixes = [[max_distance_fixes[0]]]  # already include start fix
        refined_outside_sector_fixes = []
        successfull_legs = len(sector_fixes) - 1

        for leg in range(len(max_distance_fixes) - 1):

            on_outlanding_leg = outlanded and leg > successfull_legs - 1

            if on_outlanding_leg:
                if outside_sector_fixes:
                    fix = max_distance_fixes[leg+1]
                    fixes = outside_sector_fixes
                else:
                    fix = max_distance_fixes[leg]
                    fixes = sector_fixes[leg]

                refinement_end, refinement_start = self._get_refinement_bounds(fix, fixes, refinement_fixes)
                refined_outside_sector_fixes = outside_sector_fixes[refinement_start:refinement_end]

            else:
                fixes = sector_fixes[leg+1]
                fix = max_distance_fixes[leg + 1]

                refinement_end, refinement_start = self._get_refinement_bounds(fix, fixes, refinement_fixes)
                refined_sector_fixes.append(fixes[refinement_start:refinement_end])

        return refined_sector_fixes, refined_outside_sector_fixes

    def _get_refinement_bounds(self, fix, fixes, refinement_fixes):
        """
        :param fix:
        :param fixes:
        :param refinement_fixes: this number of fixes before and after each fix
        :return:
        """
        max_distance_index = fixes.index(fix)
        refinement_start = max_distance_index - refinement_fixes if max_distance_index >= refinement_fixes else 0
        if max_distance_index + refinement_fixes + 1 <= len(fixes):
            refinement_end = max_distance_index + refinement_fixes + 1
        else:
            refinement_end = len(fixes) + 1
        return refinement_end, refinement_start

    def _calculate_distance_outlanding_leg(self, leg, start_tp_fix, outlanding_fix):
        if leg == 0:
            tp1 = self.waypoints[leg + 1]

            bearing = calculate_bearing(start_tp_fix, outlanding_fix)
            closest_area_fix = calculate_destination(start_tp_fix, tp1.r_max, bearing)

            distance = calculate_distance(self.start.fix, closest_area_fix)
            distance -= calculate_distance(outlanding_fix, closest_area_fix)

        elif leg == self.no_legs - 1:  # take finish-point of task
            distance = calculate_distance(start_tp_fix, self.finish.fix)
            distance -= calculate_distance(self.finish.fix, outlanding_fix)

        else:
            tp1 = self.waypoints[leg + 1]

            bearing = calculate_bearing(tp1.fix, outlanding_fix)
            closest_area_fix = calculate_destination(tp1.fix, tp1.r_max, bearing)

            if leg == 0:
                distance = calculate_distance(self.start.fix, closest_area_fix)
            else:
                distance = calculate_distance(start_tp_fix, closest_area_fix)
            distance -= calculate_distance(outlanding_fix, closest_area_fix)

        return distance

    def _calculate_distance_completed_leg(self, leg, start_tp_fix, end_tp_fix):
        if leg == 0:  # take start-point of task
            start = self.waypoints[0]
            distance = calculate_distance(start.fix, end_tp_fix)

            if start.distance_correction == 'shorten_legs':
                distance -= start.r_max
        elif leg == self.no_legs - 1:  # take finish-point of task
            finish = self.waypoints[-1]
            distance = calculate_distance(start_tp_fix, finish.fix)

            if finish.distance_correction == 'shorten_legs':
                distance -= finish.r_max
        else:
            distance = calculate_distance(start_tp_fix, end_tp_fix)

        return distance
