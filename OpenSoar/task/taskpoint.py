from math import pi

from OpenSoar.utilities.helper_functions import calculate_distance, calculate_bearing, calculate_bearing_difference, \
    calculate_average_bearing


class Waypoint(object):  # startpoint, turnpoints and finish

    def __init__(self, name, lat, lon, r_min, angle_min, r_max, angle_max, orientation_angle,
                 line, sector_orientation, distance_correction):

        self.name = name

        self.lat = lat
        self.lon = lon

        self.r_min = r_min
        self.angle_min = angle_min
        self.r_max = r_max
        self.angle_max = angle_max
        self.orientation_angle = orientation_angle

        self.line = line
        self.sector_orientation = sector_orientation  # fixed, symmetrical, next, previous, start
        self.distance_correction = distance_correction  # None, displace_tp, shorten_legs

    @property
    def fix(self):
        return dict(lat=self.lat, lon=self.lon)

    @staticmethod
    def cuc_fixed_orientation_angle(LSEEYOU_line):
        components = LSEEYOU_line.rstrip().split(",")
        for component in components:
            if component.startswith("A12="):
                return float(component.split("=")[1])

    @staticmethod
    def cuc_sector_orientation(LSEEYOU_line):
        components = LSEEYOU_line.rstrip().split(",")
        for component in components:
            if component.startswith("Style="):
                style = int(component.split("=")[1])
                if style == 0:
                    return "fixed"
                elif style == 1:
                    return "symmetrical"
                elif style == 2:
                    return "next"
                elif style == 3:
                    return "previous"
                elif style == 4:
                    return "start"
                else:
                    raise ValueError("Unknown waypoin style: {}".format(style))

    @staticmethod
    def cuc_distance_correction(LSEEYOU_line):
        components = LSEEYOU_line.rstrip().split(",")
        reduce = False
        move = False
        for component in components:
            if component.startswith("Reduce="):
                reduce = bool(component.split("=")[1])
            elif component.startswith("Move="):
                move = bool(component.split("=")[1])

        if reduce and move:
            return "shorten_legs"
        elif reduce:
            return "shorten_legs"
        elif move:
            return "move_tp"
        else:
            return None

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
        else:
            raise ValueError("Unknown sector orientation: %s " % self.sector_orientation)

    @staticmethod
    def cuc_sector_dimensions(LSEEYOU_line):
        components = LSEEYOU_line.rstrip().split(",")
        r_min = None
        angle_min = None
        r_max = None
        angle_max = None
        for component in components:
            if component.startswith("R1="):
                r_max = int(component.split("=")[1][:-1])
            elif component.startswith("A1="):
                angle_max = int(component.split("=")[1])
            elif component.startswith("R2="):
                r_min = int(component.split("=")[1][:-1])
            elif component.startswith("A2="):
                angle_min = int(component.split("=")[1])
        return r_min, angle_min, r_max, angle_max

    def inside_sector(self, fix):

        distance = calculate_distance(fix, self.fix)
        bearing = calculate_bearing(self.fix, fix)

        angle_wrt_orientation = abs(calculate_bearing_difference(self.orientation_angle, bearing))

        if self.line:
            raise ValueError('Calling inside_sector on a line')
        elif self.r_min is not None:
            inside_outer_sector = self.r_min < distance < self.r_max and angle_wrt_orientation < self.angle_max
            inside_inner_sector = distance < self.r_min and angle_wrt_orientation < self.angle_min
            return inside_outer_sector or inside_inner_sector
        else:  # self.r_min is None
            return distance < self.r_max and (pi - angle_wrt_orientation) < self.angle_max

    def outside_sector(self, fix):
        return not self.inside_sector(fix)

    def crossed_line(self, fix1, fix2):

        distance1 = calculate_distance(fix1, self.fix)
        distance2 = calculate_distance(fix2, self.fix)

        if not self.line:
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

    @classmethod
    def from_scs(cls):
        # todo: implement scs helper class
        pass

    @classmethod
    def from_cuc(cls):
        # todo: implement cuc helper class
        pass
