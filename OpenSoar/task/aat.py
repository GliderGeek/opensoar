from OpenSoar.task.task import Task
from OpenSoar.utilities.helper_functions import double_iterator, calculate_distance, seconds_time_difference, \
    calculate_bearing, calculate_destination


class AAT(Task):

    def __init__(self, waypoints, start_opening, t_min, start_time_buffer=0):
        super().__init__(waypoints, start_opening, start_time_buffer)

        self._t_min = t_min
        self._nominal_distances = self._calculate_nominal_distances()

    def _calculate_nominal_distances(self):
        distances = list()

        for start_waypoint, end_waypoint in double_iterator(self.waypoints):
            distance = calculate_distance(start_waypoint, end_waypoint)
            distances.append(distance)

        return distances

    def apply_rules(self, trace, trip, trace_settings):
        # todo: remove this logic to task level? al three methods seem to have the same signature
        # this flow can thus be fixed
        fixes, outlanding_fix = self._calculate_trip_fixes(trace, trace_settings)
        refined_start = self.determine_refined_start(trace, fixes)
        distances = self.determine_trip_distances(trip, outlanding_fix)

        return fixes, refined_start, outlanding_fix, distances

    def _calculate_trip_fixes(self, trace, trace_settings):  # trace settings for ENL

        sector_fixes, enl_outlanding_fix = self._get_sector_fixes(trace, trace_settings)
        reduced_sector_fixes = self.reduce_sector_fixes(sector_fixes, max_fixes_sector=300)

        if len(sector_fixes) != self.no_legs+1:
            outlanded = True
            outside_sector_fixes = self.outside_sector_fixes(trace, sector_fixes, enl_outlanding_fix)
            reduced_outside_sector_fixes = self.reduce_outside_sector_fixes(outside_sector_fixes, max_fixes_sector=300)
        else:
            outlanded = False
            reduced_outside_sector_fixes = None
            outside_sector_fixes = None

        # todo: figure out why reduced_outside_sector_fixes is list of list instead of list?
        max_distance_fixes = self.compute_max_distance_fixes(reduced_sector_fixes, outlanded,
                                                             reduced_outside_sector_fixes)
        max_distance_fixes = self.refine_max_distance_fixes(sector_fixes, max_distance_fixes, outlanded,
                                                            outside_sector_fixes)

        # compute maximum distance fixes
        outlanding_fix = None
        if outlanded:
            fixes = max_distance_fixes[:-1]
            outlanding_fix = max_distance_fixes[-1]
        else:
            fixes = max_distance_fixes

        return fixes, outlanding_fix

    def determine_trip_distances(self, fixes, outlanding_fix):

        # todo: formalize distance correction for start and finish (inside taskpoint?)
        # is this the same as in race_task? if so -> move to task

        distances = list()

        # can this be replaced by call to self.calculate_distance_completed_leg?
        for leg, (fix1, fix2) in enumerate(double_iterator(fixes)):

            if fix1 is fixes[0]:
                start = self.waypoints[0]
                distance = calculate_distance(start.fix, fix2)

                if start.distance_correction == 'shorten_legs':
                    distance -= start.r_max
            elif leg == self.no_legs - 1:
                finish = self.waypoints[-1]
                distance = calculate_distance(fix1, finish.fix)

                if finish.distance_correction == 'shorten_legs':
                    distance -= finish.r_max
            else:
                distance = calculate_distance(fix1, fix2)

            distances.append(distance)

        if outlanding_fix is not None:
            outlanding_leg = len(fixes) - 1
            distance = self.calculate_distance_outlanding_leg(outlanding_leg, fixes[-1], outlanding_fix)
            distances.append(distance)

        return distances

    def _get_sector_fixes(self, trace, trace_settings):

        # following assumptions are currently in place
        # - outlanding inside sector leads to wrong distance
        # todo: fix this

        current_leg = -1  # not yet started
        sector_fixes = list()

        enl_time = 0
        enl_first_fix = None
        enl_outlanding = False

        for trace_index, fix in enumerate(trace[:-1]):

            # check ENL when aircraft logs ENL and no ENL outlanding has taken place
            if trace_settings['enl_indices'] is not None and not enl_outlanding:
                if 'ENL' in fix and self.enl_value_exceeded(fix['ENL']):
                    if enl_first_fix is None:
                        enl_first_fix = fix
                    fix2 = trace[trace_index + 1]
                    enl_time += seconds_time_difference(fix['time'], fix2['time'])
                    if self.enl_time_exceeded(enl_time):
                        enl_outlanding = True
                        if current_leg > 0:
                            break
                else:
                    enl_time = 0
                    enl_first_fix = None

            if current_leg == -1:  # before start
                fix2 = trace[trace_index + 1]
                if self.started(fix, fix2):
                    self.add_aat_sector_fix(sector_fixes, 0, fix2)  # at task start point
                    current_leg = 0
                    enl_outlanding = False
                    enl_first_fix = None
                    enl_time = 0
            elif current_leg == 0:  # first leg, re-start still possible
                fix2 = trace[trace_index + 1]
                if self.started(fix, fix2):  # restart
                    sector_fixes[0] = [fix2]  # at task start point
                    current_leg = 0
                    enl_outlanding = False
                    enl_first_fix = None
                    enl_time = 0
                elif self.waypoints[1].inside_sector(fix):  # first sector
                    if enl_outlanding:
                        break  # break when ENL is used and not restarted
                    self.add_aat_sector_fix(sector_fixes, 1, fix)
                    current_leg += 1
            elif 0 < current_leg < self.no_legs - 1:  # at least second leg, no re-start possible
                if self.waypoints[current_leg].inside_sector(fix):  # previous taskpoint
                    self.add_aat_sector_fix(sector_fixes, current_leg, fix)
                elif self.waypoints[current_leg + 1].inside_sector(fix):  # next taskpoint
                    self.add_aat_sector_fix(sector_fixes, current_leg + 1, fix)
                    current_leg += 1
            elif current_leg == self.no_legs - 1:  # last leg
                fix2 = trace[trace_index + 1]
                if self.waypoints[current_leg].inside_sector(fix):
                    self.add_aat_sector_fix(sector_fixes, current_leg, fix)
                elif self.finished(fix, fix2):
                    sector_fixes.append([fix2])  # at task finish point
                    current_leg = self.no_legs
                    break

        if enl_outlanding:
            return sector_fixes, enl_first_fix
        else:
            return sector_fixes, None

    @staticmethod
    def reduce_sector_fixes(sector_fixes, max_fixes_sector):
        reduced_sector_fixes = list()
        for sector in range(len(sector_fixes)):
            reduced_sector_fixes.append(AAT.reduce_fixes(sector_fixes[sector], max_fixes_sector))

        return reduced_sector_fixes

    @staticmethod
    def reduce_fixes(fixes, max_fixes):
        reduction_factor = len(fixes) / max_fixes + 1
        return fixes[0::reduction_factor]

    def outside_sector_fixes(self, trace, sector_fixes, enl_outlanding_fix):
        # todo: review whether this correctly returns empty list when outlanding inside aat sector
        last_sector_fix = sector_fixes[-1][-1]
        last_sector_index = trace.index(last_sector_fix)

        outside_sector_fixes = []
        if enl_outlanding_fix is not None:
            enl_outlanding_index = trace.index(enl_outlanding_fix)

            if enl_outlanding_index > last_sector_index:
                outside_sector_fixes = trace[last_sector_index + 1: enl_outlanding_index + 1]
        else:
            outside_sector_fixes = trace[last_sector_index+1:]

        return outside_sector_fixes

    @staticmethod
    def reduce_outside_sector_fixes(outside_sector_fixes, max_fixes_sector):
        return AAT.reduce_fixes(outside_sector_fixes, max_fixes_sector)

    def add_aat_sector_fix(self, sector_fixes, taskpoint_index, fix):
        if len(sector_fixes) < (taskpoint_index + 1):
            sector_fixes.append([fix])
        else:
            sector_fixes[taskpoint_index].append(fix)

    def compute_max_distance_fixes(self, sector_fixes, outlanded, outside_sector_fixes=None):

        # to prevent problems with mutable default argument
        if outside_sector_fixes is None:
            outside_sector_fixes = []

        distances = [[]] * len(sector_fixes) if not outlanded else [[]] * (len(sector_fixes) + 1)
        distances[0] = [[0, 0]] * len(sector_fixes[0])

        completed_legs = len(sector_fixes) - 1
        for leg in range(completed_legs):

            distances[leg + 1] = [[0, 0] for i in range(len(sector_fixes[leg + 1]))]

            for fix2_index, fix2 in enumerate(sector_fixes[leg + 1]):
                for fix1_index, fix1 in enumerate(sector_fixes[leg]):

                    distance = self.calculate_distance_completed_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index][0] = total_distance
                        distances[leg + 1][fix2_index][1] = fix1_index

        if outlanded and outside_sector_fixes:  # outlanding outside AAT sector

            leg = completed_legs
            distances[leg + 1] = [[0, 0] for _ in range(len(outside_sector_fixes))]
            for fix2_index, fix2 in enumerate(outside_sector_fixes):
                for fix1_index, fix1 in enumerate(sector_fixes[leg]):

                    distance = self.calculate_distance_outlanding_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index][0] = total_distance
                        distances[leg + 1][fix2_index][1] = fix1_index

        elif outlanded and not outside_sector_fixes:  # outlanding inside AAT sector
            leg = completed_legs
            distances[leg + 1] = [[0, 0] for i in range(len(sector_fixes[leg]))]
            for fix2_index, fix2 in enumerate(sector_fixes[leg]):
                for fix1_index, fix1 in enumerate(sector_fixes[leg][0:fix2_index]):
                    distance = self.calculate_distance_outlanding_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index][0] = total_distance
                        distances[leg + 1][fix2_index][1] = fix1_index

        # determine index on last sector/outlanding-group with maximum distance
        max_dist = 0
        maximized_dist_index = None
        for i, distance in enumerate(distances[-1]):
            if distance[0] > max_dist:
                max_dist = distance[0]
                maximized_dist_index = i

        index = maximized_dist_index

        if not outlanded:
            max_distance_fixes = [sector_fixes[-1][index]]
        elif outlanded and outside_sector_fixes:  # outlanding outside aat sector
            max_distance_fixes = [outside_sector_fixes[index]]
        else:
            max_distance_fixes = [sector_fixes[-1][index]]

        legs = completed_legs if not outlanded else completed_legs + 1
        for leg in list(reversed(range(legs))):
            index = distances[leg + 1][index][1]
            max_distance_fixes.insert(0, sector_fixes[leg][index])

        return max_distance_fixes

    def refine_max_distance_fixes(self, sector_fixes, max_distance_fixes, outlanded, outside_sector_fixes=None):
        # look around fixes whether more precise fixes can be found, increasing the distance

        if outside_sector_fixes is None:
            outside_sector_fixes = []

        refinement_fixes = 10  # this amount before and this amount after the provided fix
        refined_sector_fixes = [[max_distance_fixes[0]]]  # already include start fix
        refined_outside_sector_fixes = []
        successfull_legs = len(sector_fixes) - 1

        for leg in range(len(max_distance_fixes) - 1):
            if outlanded and leg > successfull_legs - 1:
                if outside_sector_fixes:
                    max_distance_index = outside_sector_fixes.index(max_distance_fixes[leg+1])

                    if max_distance_index + refinement_fixes + 1 <= len(outside_sector_fixes):
                        refinement_end = max_distance_index + refinement_fixes + 1
                    else:
                        refinement_end = len(outside_sector_fixes) + 1
                else:
                    max_distance_index = sector_fixes[leg].index(max_distance_fixes[leg])

                    if max_distance_index + refinement_fixes + 1 <= len(sector_fixes[leg]):
                        refinement_end = max_distance_index + refinement_fixes + 1
                    else:
                        refinement_end = len(sector_fixes[leg]) + 1
            else:
                max_distance_index = sector_fixes[leg+1].index(max_distance_fixes[leg+1])
                if max_distance_index + refinement_fixes + 1 <= len(sector_fixes[leg + 1]):
                    refinement_end = max_distance_index + refinement_fixes + 1
                else:
                    refinement_end = len(sector_fixes[leg + 1]) + 1

            refinement_start = max_distance_index - refinement_fixes if max_distance_index >= refinement_fixes else 0

            if outlanded and leg > successfull_legs - 1:
                if outside_sector_fixes:
                    refined_outside_sector_fixes = outside_sector_fixes[refinement_start:refinement_end]
                else:
                    refined_outside_sector_fixes = outside_sector_fixes[refinement_start:refinement_end]
                    # todo: these are not really outside sector fixes. should variable be renamed?
            else:
                refined_sector_fixes.append(sector_fixes[leg + 1][refinement_start:refinement_end])

        return self.compute_max_distance_fixes(refined_sector_fixes, outlanded, refined_outside_sector_fixes)

    def calculate_distance_outlanding_leg(self, leg, start_tp_fix, outlanding_fix):
        if leg == 0:
            start = self.waypoints[0]
            tp1 = self.waypoints[leg + 1]

            bearing = calculate_bearing(start_tp_fix, outlanding_fix)
            closest_area_fix = calculate_destination(start_tp_fix, tp1.r_max, bearing)

            distance = calculate_distance(start.fix, closest_area_fix)
            distance -= calculate_distance(outlanding_fix, closest_area_fix)

        elif leg == self.no_legs - 1:  # take finish-point of task
            finish = self.waypoints[leg + 1]
            distance = calculate_distance(start_tp_fix, finish.fix)
            distance -= calculate_distance(finish.fix, outlanding_fix)

        else:
            start = self.waypoints[0]
            tp1 = self.waypoints[leg + 1]

            bearing = calculate_bearing(tp1.fix, outlanding_fix)
            closest_area_fix = calculate_destination(tp1.fix, tp1.r_max, bearing)

            if leg == 0:
                distance = calculate_distance(start.fix, closest_area_fix)
            else:
                distance = calculate_distance(start_tp_fix, closest_area_fix)
            distance -= calculate_distance(outlanding_fix, closest_area_fix)

        return distance

    def calculate_distance_completed_leg(self, leg, start_tp_fix, end_tp_fix):
        if leg == 0:  # take start-point of task
            start = self.waypoints[0]
            distance = calculate_distance(start.fix, end_tp_fix)
        elif leg == self.no_legs - 1:  # take finish-point of task
            finish = self.waypoints[-1]
            distance = calculate_distance(start_tp_fix, finish.fix)
        else:
            distance = calculate_distance(start_tp_fix, end_tp_fix)

        return distance
