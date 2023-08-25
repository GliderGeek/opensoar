import unittest
from copy import deepcopy

from opensoar.task.waypoint import Waypoint
from opensoar.utilities.helper_functions import calculate_destination


class TestWaypoint(unittest.TestCase):

    def test_waypoint_rmax(self):
        waypoint = Waypoint('test_waypoint', latitude=51.7509, longitude=-0.981, r_min=None, angle_min=180, r_max=50000,
                            angle_max=20, is_line=False, sector_orientation='fixed', distance_correction=None,
                            orientation_angle=190)
        fix_inside = {'lat': 52, 'lon': -0.981}  # within maximum distance and within the angle
        self.assertTrue(waypoint.inside_sector(fix_inside))

        fix_outside = {'lat': 51.5, 'lon': -1.0}  # within maximum distance, but not within the angle
        self.assertFalse(waypoint.inside_sector(fix_outside))

    def test_waypoint_rmin_and_rmax(self):
        # waypoint consists of
        # - inner half circle segment (angle_min=90)
        # - outer quarter circle segment (angle_min=45)

        wp = Waypoint('testwaypoint', latitude=52, longitude=1, r_min=5000, angle_min=90, r_max=10000,
                      angle_max=45, is_line=False, sector_orientation='fixed', distance_correction=None,
                      orientation_angle=180)

        point_in_inner_sector = calculate_destination(wp.fix, 3000, 80)
        point_in_outer_sector = calculate_destination(wp.fix, 7500, 35)
        point_outside_inner_sector = calculate_destination(wp.fix, 3000, 100)
        point_outside_outer_sector = calculate_destination(wp.fix, 7500, 55)
        point_outside_too_far = calculate_destination(wp.fix, 11000, 0)  # distance too large

        self.assertTrue(wp.inside_sector(point_in_inner_sector))
        self.assertTrue(wp.inside_sector(point_in_outer_sector))
        self.assertFalse(wp.inside_sector(point_outside_inner_sector))
        self.assertFalse(wp.inside_sector(point_outside_outer_sector))
        self.assertFalse(wp.inside_sector(point_outside_too_far))

    def test_equal_waypoints(self):
        waypoint1 = Waypoint('test_waypoint', latitude=51.7509, longitude=-0.981, r_min=None, angle_min=180,
                             r_max=50000, angle_max=20, is_line=False, sector_orientation='fixed',
                             distance_correction=None, orientation_angle=190)

        waypoint2 = Waypoint('test_waypoint', latitude=51.7509, longitude=-0.981, r_min=None, angle_min=180,
                             r_max=50000, angle_max=20, is_line=False, sector_orientation='fixed',
                             distance_correction=None, orientation_angle=190)

        self.assertTrue(waypoint1 == waypoint2)

    def test_unequal_waypoints(self):
        waypoint1 = Waypoint('test_waypoint', latitude=51.7509, longitude=-0.981, r_min=None, angle_min=180,
                             r_max=50000, angle_max=20, is_line=False, sector_orientation='fixed',
                             distance_correction=None, orientation_angle=190)

        waypoints = [deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1),
                     deepcopy(waypoint1)]

        waypoints[0].latitude = 51
        waypoints[1].longitude = 0
        waypoints[2].r_min = 0.5
        waypoints[3].angle_min = None
        waypoints[4].r_max = 51000
        waypoints[5].angle_max = 10
        waypoints[6].is_line = True
        waypoints[7].sector_orientation = None
        waypoints[8].distance_correction = 'displace_tp'
        waypoints[9].orientation_angle = 180

        for waypoint in waypoints:
            self.assertFalse(waypoint == waypoint1)

    def test_crossed_start_line(self):
        """
        Test whether points in correct order trigger line crossing
        Start line is W-E oriented, with a point north first and then a point south should be a start
        """
        # start line is pointing sout

        start_line = Waypoint('testwaypoint', latitude=52, longitude=1, r_min=None, angle_min=None, r_max=1000,
                      angle_max=45, is_line=True, sector_orientation='next', distance_correction=None,
                      orientation_angle=180)

        # test direction of crossing
        point_north = calculate_destination(start_line.fix, 1000, 0)
        point_south = calculate_destination(start_line.fix, 1000, 180)
        self.assertTrue(start_line.crossed_line(point_north, point_south))
        self.assertFalse(start_line.crossed_line(point_south, point_north))

        # test within radius of line
        point_north_close = calculate_destination(start_line.fix, 500, 45)
        point_south_close = calculate_destination(start_line.fix, 500, 135)
        self.assertTrue(start_line.crossed_line(point_north_close, point_south_close))

        # test outside radius of line
        point_north_far = calculate_destination(start_line.fix, 2000, 45)
        point_south_far = calculate_destination(start_line.fix, 2000, 135)
        self.assertFalse(start_line.crossed_line(point_north_far, point_south_far))

    def test_crossed_finish_line(self):
        """
        Test whether points in correct order trigger line crossing
        Finish line is W-E oriented, with a point north first and then a point south should be a finish
        """
        # start line is pointing sout

        finish_line = Waypoint('testwaypoint', latitude=52, longitude=1, r_min=None, angle_min=None, r_max=1000,
                      angle_max=45, is_line=True, sector_orientation='previous', distance_correction=None,
                      orientation_angle=0)

        # test direction of crossing
        point_north = calculate_destination(finish_line.fix, 1000, 0)
        point_south = calculate_destination(finish_line.fix, 1000, 180)
        self.assertTrue(finish_line.crossed_line(point_north, point_south))
        self.assertFalse(finish_line.crossed_line(point_south, point_north))

        # test within radius of line
        point_north_close = calculate_destination(finish_line.fix, 500, 45)
        point_south_close = calculate_destination(finish_line.fix, 500, 135)
        self.assertTrue(finish_line.crossed_line(point_north_close, point_south_close))

        # test outside radius of line
        point_north_far = calculate_destination(finish_line.fix, 2000, 45)
        point_south_far = calculate_destination(finish_line.fix, 2000, 135)
        self.assertFalse(finish_line.crossed_line(point_north_far, point_south_far))
