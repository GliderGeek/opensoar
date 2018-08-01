import datetime
from typing import List

from opensoar.task.waypoint import Waypoint
from opensoar.utilities.helper_functions import calculate_bearing, calculate_distance, calculate_bearing_difference, \
    interpolate_fixes, double_iterator


class Task:
    """
    Base Class for specific task implementations.
    """

    ENL_VALUE_THRESHOLD = 500
    ENL_TIME_THRESHOLD = 30

    def __init__(self, waypoints: List[Waypoint], timezone: int, start_opening: datetime.time, start_time_buffer: int,
                 multistart: bool):
        """
        :param waypoints:
        :param timezone: time difference wrt UTC in hours
        :param start_opening: in UTC
        :param start_time_buffer: in seconds
        :param multistart: flag whether multistart takes place
        """

        self._waypoints = waypoints
        self.timezone = timezone
        self.start_opening = start_opening
        self.start_time_buffer = start_time_buffer
        self.multistart = multistart

        self.set_orientation_angles(self.waypoints)

    def __eq__(self, other):
        same_number_waypoints = len(self.waypoints) == len(other.waypoints)

        if not same_number_waypoints:
            return False
        else:
            for waypoint, other_waypoint in zip(self.waypoints, other.waypoints):
                if waypoint != other_waypoint:
                    return False

        return (self.start_opening == other.start_opening and
                self.start_time_buffer == other.start_time_buffer)

    @property
    def waypoints(self):
        # waypoints may not be altered because subclasses perform tasks to calculate distances based on waypoints.
        return self._waypoints

    @property
    def no_tps(self):
        return len(self.waypoints) - 2

    @property
    def no_legs(self):
        return self.no_tps + 1

    @property
    def start(self):
        return self.waypoints[0]

    @property
    def finish(self):
        return self.waypoints[-1]

    @staticmethod
    def set_orientation_angles(waypoints):
        # sector orientations and angles
        for index in range(len(waypoints)):

            if index == 0:  # necessary for index out of bounds
                angle = calculate_bearing(waypoints[index + 1].fix,  waypoints[index].fix, final_bearing=True)
                waypoints[index].set_orientation_angle(angle_next=angle)
            elif index == len(waypoints) - 1:  # necessary for index out of bounds
                angle = calculate_bearing(waypoints[index - 1].fix, waypoints[index].fix, final_bearing=True)
                waypoints[index].set_orientation_angle(angle_previous=angle)
            else:
                angle_start = calculate_bearing(waypoints[0].fix, waypoints[index].fix, final_bearing=True)
                angle_previous = calculate_bearing(waypoints[index - 1].fix, waypoints[index].fix, final_bearing=True)
                angle_next = calculate_bearing(waypoints[index + 1].fix, waypoints[index].fix, final_bearing=True)
                waypoints[index].set_orientation_angle(angle_start=angle_start,
                                                       angle_previous=angle_previous,
                                                       angle_next=angle_next)

    @staticmethod
    def distance_shortened_leg(distance, current, currentP1, shortened_point):
        if shortened_point == "current":
            distance -= current.r_max if current.r_max is not None else current.r_min
            return distance
        elif shortened_point == "end":
            distance -= currentP1.r_max if currentP1.r_max is not None else currentP1.r_min
            return distance
        else:
            raise ValueError("Shortened point is not recognized: {}".format(shortened_point))

    @staticmethod
    def distance_moved_turnpoint(distance, begin, end, moved_point, move_direction='reduce'):
        from math import sqrt, cos, pi, acos

        if moved_point == "begin":
            moved = begin
            other = end
            angle_reduction = 0
        elif moved_point == "end":
            moved = end
            other = begin
            angle_reduction = 0
        elif moved_point == "both_end":
            moved = end
            other = begin
            original_distance = calculate_distance(begin.fix, end.fix)

            distance_moved_current = begin.r_max if begin.angle_max == 180 else begin.r_min
            angle_reduction = abs(acos((distance_moved_current ** 2 - distance ** 2 - original_distance ** 2) / (-2 * distance * original_distance))) * 180 / pi
        else:
            raise ValueError("Displaced point is not recognized: %s" % moved_point)

        displacement_dist = moved.r_max if moved.angle_max == 180 else moved.r_min
        bearing1 = moved.orientation_angle
        bearing2 = calculate_bearing(other.fix, moved.fix, final_bearing=True)

        if move_direction == 'increase':
            angle = 180 - abs(calculate_bearing_difference(bearing1, bearing2)) - angle_reduction
        else:
            angle = abs(calculate_bearing_difference(bearing1, bearing2)) - angle_reduction
        distance = sqrt(distance**2 + displacement_dist**2 - 2 * distance * displacement_dist * cos(angle * pi / 180))

        return distance

    def started(self, fix1, fix2):
        start = self.waypoints[0]
        if start.is_line:
            return start.crossed_line(fix1, fix2)
        else:
            return start.inside_sector(fix1) and start.outside_sector(fix2)

    def finished(self, fix1, fix2):
        finish = self.waypoints[-1]
        if finish.is_line:
            return finish.crossed_line(fix1, fix2)
        else:
            return finish.outside_sector(fix1) and finish.inside_sector(fix2)

    def determine_refined_start(self, trace, fixes):
        start_i = trace.index(fixes[0])
        interpolated_fixes = interpolate_fixes(trace[start_i], trace[start_i+1])

        for fix, next_fix in double_iterator(interpolated_fixes):
            if self.started(fix, next_fix):
                return fix['time']

        raise ValueError('Start should have been determined')

    def enl_value_exceeded(self, fix) -> bool:
        """
        Check whether ENL value is exceeded.
        :param fix:
        :return: returns False when not exceeded or when ENL information is not present in fix
        """
        return 'ENL' in fix and fix['ENL'] > self.ENL_VALUE_THRESHOLD

    def enl_time_exceeded(self, enl_time):
        return enl_time >= self.ENL_TIME_THRESHOLD
