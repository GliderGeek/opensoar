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
                      angle_max=45, is_line=False, sector_orientation='fixes', distance_correction=None,
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
