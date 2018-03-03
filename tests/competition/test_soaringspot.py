import unittest

import datetime

from opensoar.competition.soaringspot import get_lat_long, get_fixed_orientation_angle, get_sector_orientation, \
    get_sector_dimensions, get_waypoint, get_waypoints, SoaringSpotDaily, get_task_rules
from opensoar.task.waypoint import Waypoint


class TestSoaringspot(unittest.TestCase):

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

    def test_get_competitors(self):
        soaringspot_page = SoaringSpotDaily(
            'https://www.soaringspot.com/en/sallandse-tweedaagse-2014/results/club/task-1-on-2014-06-21/daily', '')

        competitor_pk = soaringspot_page.get_competitors()[2]
        self.assertEqual(competitor_pk.competition_id, 'PK')

        self.assertEqual(competitor_pk.ranking, 3)

        expected_igc_url = 'https://archive.soaringspot.com/contest/013/1323/flights/2477/2597322754.igc'
        self.assertEqual(competitor_pk.igc_url, expected_igc_url)

    def test_get_competition_day(self):
        soaringspot_page = SoaringSpotDaily(
            'https://www.soaringspot.com/en/sallandse-tweedaagse-2014/results/club/task-1-on-2014-06-21/daily', '')

        competitionday = soaringspot_page.get_competition_day()

        self.assertEqual(competitionday.name, 'sallandse-tweedaagse-2014')
        self.assertEqual(competitionday.plane_class, 'club')
        self.assertEqual(competitionday.date, datetime.date(2014, 6, 21))
        self.assertEqual(len(competitionday.competitors), 8)

    def test_get_task_rules(self):
        lseeyou_tsk_line = 'LSEEYOU TSK,NoStart=13:29:00,TaskTime=03:30:00,WpDis=False,' \
                           'MinDis=True,NearDis=0.5km,NearAlt=200.0m,MinFinAlt=0.0km'

        task_rules = get_task_rules(lseeyou_tsk_line)

        self.assertIn('start_opening', task_rules)
        self.assertIn('task_time', task_rules)

        self.assertEquals(task_rules['start_opening'], datetime.time(13, 29, 0))
        self.assertEquals(task_rules['task_time'], datetime.time(3, 30, 0))
