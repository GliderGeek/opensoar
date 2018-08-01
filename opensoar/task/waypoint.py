from math import isclose

from opensoar.utilities.helper_functions import calculate_distance, both_none_or_same_float, both_none_or_same_str
from opensoar.utilities.helper_functions import calculate_bearing
from opensoar.utilities.helper_functions import calculate_bearing_difference
from opensoar.utilities.helper_functions import calculate_average_bearing


class Waypoint(object):

    SEEYOU_SECTOR_MARGIN = 12  # SeeYou does not outland flights which come this close to the sector

    def __init__(self, name: str, latitude: float, longitude: float, r_min: float, angle_min: float, r_max: float,
                 angle_max: float, is_line: bool, sector_orientation: str,
                 distance_correction=None, orientation_angle=None):
        """
        Waypoint is either the start point, one of the turn points or the finish point of a task.
        :param name:
        :param latitude: latitude in degrees
        :param longitude: in degrees
        :param r_min: in m or None
        :param angle_min: in degrees
        :param r_max: in m
        :param angle_max: in degrees
        :param is_line: boolean denoting whether waypoint is a line
        :param sector_orientation:  valid values: 'fixed', 'symmetrical', 'next', 'previous', 'start'
        :param distance_correction: optional argument. valid values: 'displace_tp', 'shorten_legs'
        :param orientation_angle: optional argument. Should only be set when sector_orientation='fixed'.
        """

        self.name = name

        self.latitude = latitude
        self.longitude = longitude

        self.r_min = r_min
        self.angle_min = angle_min
        self.r_max = r_max
        self.angle_max = angle_max
        self.orientation_angle = orientation_angle

        self.is_line = is_line
        self.sector_orientation = sector_orientation
        self.distance_correction = distance_correction

    def __eq__(self, other):

        return (self.name == other.name and
                isclose(self.latitude, other.latitude) and
                isclose(self.longitude, other.longitude) and
                both_none_or_same_float(self.r_min, other.r_min) and
                both_none_or_same_float(self.angle_min, other.angle_min) and
                isclose(self.r_max, other.r_max) and
                isclose(self.angle_max, other.angle_max) and
                isclose(self.orientation_angle, other.orientation_angle) and
                self.is_line == other.is_line and
                both_none_or_same_str(self.sector_orientation, other.sector_orientation) and
                both_none_or_same_str(self.distance_correction, other.distance_correction))

    def __repr__(self):
        return "<Waypoint lat=%s, lon=%s>" % (self.latitude, self.longitude)

    @property
    def fix(self):
        return dict(lat=self.latitude, lon=self.longitude)

    def set_orientation_angle(self, angle_start=None, angle_previous=None, angle_next=None):
        # Fixed orientation is skipped as that has already been set

        if self.sector_orientation == "symmetrical":
            self.orientation_angle = calculate_average_bearing(angle_previous, angle_next)
        elif self.sector_orientation == "next":
            self.orientation_angle = angle_next
        elif self.sector_orientation == "previous":
            self.orientation_angle = angle_previous
        elif self.sector_orientation == "start":
            self.orientation_angle = angle_start
        elif self.sector_orientation == "fixed":
            if self.orientation_angle is None:
                raise ValueError("Orientation angle should be set fox fixed sector")

        else:
            raise ValueError("Unknown sector orientation: %s " % self.sector_orientation)

    def inside_sector(self, fix):

        distance = calculate_distance(fix, self.fix)
        bearing = calculate_bearing(self.fix, fix)

        angle_wrt_orientation = abs(calculate_bearing_difference(self.orientation_angle, bearing))

        if self.is_line:
            raise ValueError('Calling inside_sector on a line')
        elif self.r_min is not None:
            inside_outer_sector = self.r_min - self.SEEYOU_SECTOR_MARGIN < distance < self.r_max + self.SEEYOU_SECTOR_MARGIN and angle_wrt_orientation < self.angle_max
            inside_inner_sector = distance < self.r_min and angle_wrt_orientation < self.angle_min
            return inside_outer_sector or inside_inner_sector
        else:  # self.r_min is None
            return distance < self.r_max + self.SEEYOU_SECTOR_MARGIN and (180 - angle_wrt_orientation) < self.angle_max

    def outside_sector(self, fix):
        return not self.inside_sector(fix)

    def crossed_line(self, fix1, fix2):

        distance1 = calculate_distance(fix1, self.fix)
        distance2 = calculate_distance(fix2, self.fix)

        if not self.is_line:
            raise ValueError('Calling crossed_line on a sector!')
        else:
            if distance2 > self.r_max and distance1 > self.r_max:
                return False
            else:  # either both within circle or only one, leading to small amount of false positives
                bearing1 = calculate_bearing(self.fix, fix1)
                bearing2 = calculate_bearing(self.fix, fix2)

                angle_wrt_orientation1 = abs(calculate_bearing_difference(self.orientation_angle, bearing1))
                angle_wrt_orientation2 = abs(calculate_bearing_difference(self.orientation_angle, bearing2))

                if self.sector_orientation == "next":  # start line
                    return angle_wrt_orientation1 < 90 < angle_wrt_orientation2
                elif self.sector_orientation == "previous":  # finish line
                    return angle_wrt_orientation2 < 90 < angle_wrt_orientation1
                else:
                    raise ValueError("A line with this orientation is not implemented!")
