import unittest
from copy import deepcopy

from opensoar.task.waypoint import Waypoint


class TestWaypoint(unittest.TestCase):

    def test_inside_sector_true(self):
        """Fix is within maximum distance and within the angle"""
        waypoint = Waypoint('test_waypoint', latitude=51.7509, longitude=-0.981, r_min=None, angle_min=180, r_max=50000,
                            angle_max=20, is_line=False, sector_orientation='fixed', distance_correction=None,
                            orientation_angle=190)
        fix = {'lat': 52, 'lon': -0.981}
        self.assertTrue(waypoint.inside_sector(fix))

    def test_inside_sector_false(self):
        """Fix is within maximum distance, but not within the angle"""
        waypoint = Waypoint('test_waypoint', latitude=51.7509, longitude=-0.981, r_min=None, angle_min=180, r_max=50000,
                            angle_max=20, is_line=False, sector_orientation='fixed', distance_correction=None,
                            orientation_angle=190)
        fix = {'lat': 51.5, 'lon': -1.0}
        self.assertFalse(waypoint.inside_sector(fix))

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
