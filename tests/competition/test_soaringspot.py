import unittest

from OpenSoar.competition.soaringspot import dms2dd, get_lat_long, get_fixed_orientation_angle, get_sector_orientation, \
    get_sector_dimensions, get_waypoint, get_waypoints
from OpenSoar.task.waypoint import Waypoint


class TestSoaringspot(unittest.TestCase):

    def test_dms2dd(self):

        dms_dd = [
            (52, 15, 0, 'N', 52.25),
            (52, 15, 0, 'S', -52.25),
            (6, 9, 500, 'E', 6.1583333),
            (6, 9, 500, 'W', -6.1583333),
        ]

        for degrees, minutes, seconds, cardinal, expected_dd in dms_dd:
            dd = dms2dd(degrees, minutes, seconds, cardinal)
            self.assertAlmostEqual(dd, expected_dd)

    def test_get_lat_long(self):
        lcu_line = 'LCU::C5215000N00609500EDeventer'
        lat, lon = get_lat_long(lcu_line)

        self.assertAlmostEqual(lat, 52.25)
        self.assertAlmostEqual(lon, 6.1583333)

    def test_get_fixed_orientation_angle(self):
        angle = get_fixed_orientation_angle('LSEEYOU OZ=2,Style=0,R1=20000m,A1=45,A12=215')
        self.assertEqual(angle, 215)

    def test_get_sector_orientation(self):
        orientation = get_sector_orientation('LSEEYOU OZ=0,Style=1,R1=500m,A1=180')
        self.assertEqual(orientation, 'symmetrical')

    def test_get_sector_dimensions(self):
        lseeyou_line = 'LSEEYOU OZ=0,Style=1,R1=500m,A1=180'
        r_min, angle_min, r_max, angle_max = get_sector_dimensions(lseeyou_line)
        self.assertEqual(r_max, 500)
        self.assertIsNone(r_min)
        self.assertEqual(angle_max, 180)
        self.assertIsNone(angle_min)

    def test_get_waypoint(self):
        lcu_line = 'LCU::C5215000N00609500EDeventer'
        lseeyou_line = 'LSEEYOU OZ=0,Style=1,R1=500m,A1=180'
        waypoint = get_waypoint(lcu_line, lseeyou_line)
        self.assertTrue(isinstance(waypoint, Waypoint))
        self.assertEqual(waypoint.name, 'Deventer')
        self.assertAlmostEqual(waypoint.latitude, 52.25)
        self.assertAlmostEqual(waypoint.longitude, 6.1583333)
        self.assertEqual(waypoint.r_max, 500)
        self.assertEqual(waypoint.angle_max, 180)

    def test_get_waypoints(self):
        lcu_lines = [
            'LCU::C210614200004301299000003',
            'LCU::C5228133N00620000ESALLAND FL',
            'LCU::C5226783N00620467ESALLAND AF1',
            'LCU::C5215000N00609500EDeventer',
            'LCU::C5204900N00626800ERuurlo',
            'LCU::C5228400N00624600EArchemerberg',
            'LCU::C5228133N00620000ESALLAND FL',
            'LCU::C5228133N00620000ESALLAND FL'
        ]

        lseeyou_lines = [
            'LSEEYOU OZ=-1,Style=2,R1=2500m,A1=35,Line=1',
            'LSEEYOU OZ=0,Style=1,R1=500m,A1=180',
            'LSEEYOU OZ=1,Style=1,R1=500m,A1=180',
            'LSEEYOU OZ=2,Style=1,R1=500m,A1=180',
            'LSEEYOU OZ=3,Style=3,R1=500m,A1=180',
        ]

        waypoints = get_waypoints(lcu_lines, lseeyou_lines)
        self.assertEqual(len(waypoints), 5)

        for waypoint in waypoints:
            self.assertTrue(isinstance(waypoint, Waypoint))

        self.assertEqual(waypoints[2].name, 'Ruurlo')
