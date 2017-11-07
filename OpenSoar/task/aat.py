from OpenSoar.task.task import Task
from OpenSoar.utilities.helper_functions import calculate_distance, calculate_bearing, seconds_time_difference, \
    calculate_destination, double_iterator


class AAT(Task):
    def __init__(self, waypoints, multi_start, start_opening, utc_diff, t_min):
        super().__init__(waypoints, multi_start, start_opening, utc_diff)

        self.t_min = t_min
        self.nominal_distances = []

        self.set_task_distances()

    def set_task_distances(self):
        for previous_waypoint, waypoint in double_iterator(self.waypoints):
            distance = calculate_distance(previous_waypoint.fix, waypoint.fix)
            self.nominal_distances.append(distance)

    def apply_rules(self, trace, trip, trace_settings):
        self.determine_trip_fixes(trace, trip, trace_settings)
        self.refine_start(trip, trace)
        self.determine_trip_distances(trip)

    def add_aat_sector_fix(self, sector_fixes, taskpoint_index, fix):
        if len(sector_fixes) < (taskpoint_index + 1):
            sector_fixes.append([fix])
        else:
            sector_fixes[taskpoint_index].append(fix)

    def get_sector_fixes(self, trace, trace_settings):

        # following assumptions are currently in place
        # - outlanding inside sector leads to wrong distance

        current_leg = -1  # not yet started
        sector_fixes = []

        enl_time = 0
        enl_first_fix = None
        enl_outlanding = False

        for fix, next_fix in double_iterator(trace):

            # check ENL when aircraft logs ENL and no ENL outlanding has taken place
            if trace_settings['enl_indices'] is not None and not enl_outlanding:
                if self.enl_value_exceeded(fix, trace_settings['enl_indices']):
                    if enl_first_fix is None:
                        enl_first_fix = fix
                    enl_time += seconds_time_difference(fix, next_fix)
                    if self.enl_time_exceeded(enl_time):
                        enl_outlanding = True
                        if current_leg > 0:
                            break
                else:
                    enl_time = 0
                    enl_first_fix = None

            if current_leg == -1:  # before start
                if self.started(fix, next_fix):
                    self.add_aat_sector_fix(sector_fixes, 0, next_fix)  # at task start point
                    current_leg = 0
                    enl_outlanding = False
                    enl_first_fix = None
                    enl_time = 0
            elif current_leg == 0:  # first leg, re-start still possible
                if self.started(fix, next_fix):  # restart
                    sector_fixes[0] = [next_fix]  # at task start point
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
                if self.waypoints[current_leg].inside_sector(fix):
                    self.add_aat_sector_fix(sector_fixes, current_leg, fix)
                elif self.finished(fix, next_fix):
                    sector_fixes.append([next_fix])  # at task finish point
                    current_leg = self.no_legs
                    break

        if enl_outlanding:
            return sector_fixes, enl_first_fix
        else:
            return sector_fixes, None

    @staticmethod
    def reduce_fixes(fixes, max_fixes):
        reduction_factor = len(fixes) / max_fixes + 1
        return fixes[0::reduction_factor]

    @staticmethod
    def reduce_sector_fixes(sector_fixes, max_fixes_sector):
        reduced_sector_fixes = []
        for sector in range(len(sector_fixes)):
            reduced_sector_fixes.append(AAT.reduce_fixes(sector_fixes[sector], max_fixes_sector))

        return reduced_sector_fixes

    @staticmethod
    def reduce_outside_sector_fixes(outside_sector_fixes, max_fixes_sector):
        return AAT.reduce_fixes(outside_sector_fixes, max_fixes_sector)

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

    def calculate_distance_outlanding_leg(self, leg, start_tp_fix, outlanding_fix):
        # room for improvement:
        # by using LatLon objects instead of records, the switch case can be reduced
        # since pnt are now the same as tsk records

        start = self.waypoints[0]
        finish = self.waypoints[-1]
        next_waypoint = self.waypoints[leg + 1]

        if leg == self.no_legs - 1:  # take finish-point of task
            distance = calculate_distance(start_tp_fix, finish.fix)
            distance -= calculate_distance(finish.fix, outlanding_fix)
        else:
            bearing = calculate_bearing(next_waypoint.fix, outlanding_fix)
            closest_area_fix = calculate_destination(next_waypoint, next_waypoint.r_max, bearing)

            if leg == 0:
                distance = calculate_distance(start.fix, closest_area_fix)
            else:
                distance = calculate_distance(start_tp_fix, closest_area_fix)
            distance -= calculate_distance(outlanding_fix, closest_area_fix)

        return distance

    def fill_distances(self, distances, fixes, leg):
        distances[leg + 1] = [[0, 0] for _ in range(len(fixes[leg + 1]))]
        for fix2_index, fix2 in enumerate(fixes[leg + 1]):
            for fix1_index, fix1 in enumerate(fixes[leg]):

                distance = self.calculate_distance_completed_leg(leg, fix1, fix2)
                total_distance = distances[leg][fix1_index][0] + distance
                if total_distance > distances[leg + 1][fix2_index][0]:
                    distances[leg + 1][fix2_index][0] = total_distance
                    distances[leg + 1][fix2_index][1] = fix1_index

        distances[leg + 1] = [[0, 0] for _ in range(len(fixes))]
        for fix2_index, fix2 in enumerate(fixes):
            for fix1_index, fix1 in enumerate(fixes[leg]):
                distance = self.calculate_distance_outlanding_leg(leg, fix1, fix2)
                total_distance = distances[leg][fix1_index][0] + distance
                if total_distance > distances[leg + 1][fix2_index][0]:
                    distances[leg + 1][fix2_index][0] = total_distance
                    distances[leg + 1][fix2_index][1] = fix1_index

        distances[leg + 1] = [[0, 0] for _ in range(len(fixes[leg]))]
        for fix2_index, fix2 in enumerate(fixes[leg]):
            for fix1_index, fix1 in enumerate(fixes[leg][0:fix2_index]):
                distance = self.calculate_distance_outlanding_leg(leg, fix1, fix2)
                total_distance = distances[leg][fix1_index][0] + distance
                if total_distance > distances[leg + 1][fix2_index][0]:
                    distances[leg + 1][fix2_index][0] = total_distance
                    distances[leg + 1][fix2_index][1] = fix1_index


    def compute_max_distance_fixes(self, sector_fixes, outlanded, outside_sector_fixes=None):

        # to prevent problems with mutable default argument
        if outside_sector_fixes is None:
            outside_sector_fixes = []

        distances = [[]] * len(sector_fixes) if not outlanded else [[]] * (len(sector_fixes) + 1)
        distances[0] = [[0, 0]] * len(sector_fixes[0])

        completed_legs = len(sector_fixes) - 1
        for leg in range(completed_legs):
            distances[leg + 1] = [[0, 0] for _ in range(len(sector_fixes[leg + 1]))]
            for fix2_index, fix2 in enumerate(sector_fixes[leg + 1]):
                for fix1_index, fix1 in enumerate(sector_fixes[leg]):
                    distance = self.calculate_distance_completed_leg(leg, fix1, fix2)
                    total_distance = distances[leg][fix1_index][0] + distance
                    if total_distance > distances[leg + 1][fix2_index][0]:
                        distances[leg + 1][fix2_index][0] = total_distance
                        distances[leg + 1][fix2_index][1] = fix1_index

        if outlanded:
            if outside_sector_fixes:  # outlanding outside AAT sector
                leg = completed_legs
                distances[leg + 1] = [[0, 0] for _ in range(len(outside_sector_fixes))]
                for fix2_index, fix2 in enumerate(outside_sector_fixes):
                    for fix1_index, fix1 in enumerate(sector_fixes[leg]):
                        distance = self.calculate_distance_outlanding_leg(leg, fix1, fix2)
                        total_distance = distances[leg][fix1_index][0] + distance
                        if total_distance > distances[leg + 1][fix2_index][0]:
                            distances[leg + 1][fix2_index][0] = total_distance
                            distances[leg + 1][fix2_index][1] = fix1_index

            else:  # outlanding inside AAT sector
                leg = completed_legs
                distances[leg + 1] = [[0, 0] for _ in range(len(sector_fixes[leg]))]
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

        if outlanded:
            if outside_sector_fixes:  # outlanding outside aat sector
                max_distance_fixes = [outside_sector_fixes[index]]
            else:
                max_distance_fixes = [sector_fixes[-1][index]]
        else:
            max_distance_fixes = [sector_fixes[-1][index]]

        legs = completed_legs if not outlanded else completed_legs + 1
        for leg in list(reversed(range(legs))):
            index = distances[leg + 1][index][1]
            max_distance_fixes.insert(0, sector_fixes[leg][index])

        return max_distance_fixes

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

    def determine_trip_fixes(self, trace, trip, trace_settings):  # trace settings for ENL

        sector_fixes, enl_outlanding_fix = self.get_sector_fixes(trace, trace_settings)
        reduced_sector_fixes = self.reduce_sector_fixes(sector_fixes, max_fixes_sector=300)

        if enl_outlanding_fix is not None:
            trip.enl_fix = enl_outlanding_fix

        outlanded = False if len(sector_fixes) == self.no_legs+1 else True

        # compute maximum distance fixes
        if outlanded:

            outside_sector_fixes = self.outside_sector_fixes(trace, sector_fixes, enl_outlanding_fix)
            reduced_outside_sector_fixes = self.reduce_outside_sector_fixes(outside_sector_fixes, max_fixes_sector=300)

            #todo: figure out why reduced_outside_sector_fixes is list of list instead of list?
            max_distance_fixes = self.compute_max_distance_fixes(reduced_sector_fixes, outlanded,
                                                                 reduced_outside_sector_fixes)
            max_distance_fixes = self.refine_max_distance_fixes(sector_fixes, max_distance_fixes, outlanded,
                                                                outside_sector_fixes)

            trip.fixes = max_distance_fixes[:-1]
            trip.outlanding_fix = max_distance_fixes[-1]

        else:
            max_distance_fixes = self.compute_max_distance_fixes(reduced_sector_fixes, outlanded)
            max_distance_fixes = self.refine_max_distance_fixes(sector_fixes, max_distance_fixes, outlanded)

            trip.fixes = max_distance_fixes

    # candidate for trip class?
    def determine_trip_distances(self, trip):

        # todo: formalize distance correction for start and finish (inside taskpoint?)

        # can this be replaced by call to self.calculate_distance_completed_leg?
        for fix1_index, fix1 in enumerate(trip.fixes[:-1]):

            if fix1_index == 0:
                fix2 = trip.fixes[fix1_index + 1]
                start = self.waypoints[0]
                distance = calculate_distance(start.fix, fix2)

                if start.distance_correction == 'shorten_legs':
                    distance -= start.r_max
            elif fix1_index == self.no_legs-1:
                taskpoint = self.waypoints[-1]
                distance = calculate_distance(fix1, taskpoint.fix)
                if taskpoint.distance_correction == 'shorten_legs':
                    distance -= taskpoint.r_max
            else:
                fix2 = trip.fixes[fix1_index + 1]
                distance = calculate_distance(fix1, fix2)

            trip.distances.append(distance)

        if trip.outlanded():
            leg = trip.outlanding_leg()
            distance = self.calculate_distance_outlanding_leg(leg, trip.fixes[-1], trip.outlanding_fix)
            trip.distances.append(distance)
