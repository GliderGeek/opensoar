import unittest

from OpenSoar.task.waypoint import Waypoint


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
