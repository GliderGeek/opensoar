import unittest
import os
import datetime

from opensoar.competition.soaringspot import get_lat_long, get_fixed_orientation_angle, get_sector_orientation, \
    get_sector_dimensions, get_waypoint, get_waypoints, SoaringSpotDaily, get_task_rules, get_info_from_comment_lines
from opensoar.task.waypoint import Waypoint
from opensoar.task.task import Task

from aerofiles.igc import Reader


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
        orientation = get_sector_orientation('LSEEYOU OZ=0,Style=1,R1=500m,A1=180', 3)
        self.assertEqual(orientation, 'symmetrical')

    def test_get_sector_orientation_start(self):
        """Should always be next, independent on Style. Sometimes soaringspot files have wrong styles."""

        lseeyou_lines = [
            'LSEEYOU OZ=-1,Style=1,R1=500m,A1=180',
            'LSEEYOU OZ=-1,Style=2,R1=500m,A1=180',
            'LSEEYOU OZ=-1,Style=3,R1=500m,A1=180',
            'LSEEYOU OZ=-1,Style=4,R1=500m,A1=180',
        ]

        for lseeyou_line in lseeyou_lines:
            orientation = get_sector_orientation(lseeyou_line, 3)
            self.assertEqual(orientation, 'next')

    def test_get_sector_orientation_finish(self):
        """Should always be previous, independent on Style. Sometimes soaringspot files have wrong styles."""

        lseeyou_lines = [
            'LSEEYOU OZ=2,Style=1,R1=500m,A1=180',
            'LSEEYOU OZ=2,Style=2,R1=500m,A1=180',
            'LSEEYOU OZ=2,Style=3,R1=500m,A1=180',
            'LSEEYOU OZ=2,Style=4,R1=500m,A1=180',
        ]

        for lseeyou_line in lseeyou_lines:
            orientation = get_sector_orientation(lseeyou_line, 4)
            self.assertEqual(orientation, 'previous')

    def test_get_sector_orientation_speedstyle_error(self):
        """In some of the soaringspot igc files  a wrong SpeedStyle entry is found"""

        orientation = get_sector_orientation('LSEEYOU OZ=-1,Style=2SpeedStyle=0,R1=5000m,A1=180,Line=1', 4)
        self.assertEqual(orientation, 'next')

        orientation = get_sector_orientation('LSEEYOU OZ=0,Style=1SpeedStyle=3,R1=500m,A1=180,Reduce=1', 4)
        self.assertEqual(orientation, 'symmetrical')

        orientation = get_sector_orientation('LSEEYOU OZ=0,Style=1SpeedStyle=2,R1=500m,A1=180,Reduce=1', 4)
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
        waypoint = get_waypoint(lcu_line, lseeyou_line, 3)
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
        Task.set_orientation_angles(waypoints)

        self.assertEqual(len(waypoints), 5)

        # name, orientation_angle, is_line
        expected = [
            ("SALLAND AF1", 209, True),
            ("Deventer", 81, False),
            ("Ruurlo", 335, False),
            ("Archemerberg", 220, False),
            ("SALLAND FL", 84, False),
        ]

        wp = waypoints[0]
        print(wp.r_min, wp.angle_min, wp.r_max, wp.angle_max)

        for w, expected_w in zip(waypoints, expected):
            name, orientation_angle, is_line = expected_w
            self.assertEqual(w.name, name)
            self.assertEqual(int(w.orientation_angle), orientation_angle)
            self.assertEqual(w.is_line, is_line)

    def test_get_competitors(self):
        # old format
        soaringspot_page = SoaringSpotDaily(
            'https://www.soaringspot.com/en/sallandse-tweedaagse-2014/results/club/task-1-on-2014-06-21/daily')

        competitors = soaringspot_page._get_competitors_info(include_hc_competitors=False, include_dns_competitors=True)
        self.assertEqual(len(competitors), 10)
        competitors = soaringspot_page._get_competitors_info(include_hc_competitors=False, include_dns_competitors=False)
        self.assertEqual(len(competitors), 8)
        competitor_pk = soaringspot_page._get_competitors_info(include_hc_competitors=False)[2]

        self.assertEqual(competitor_pk['competition_id'], 'PK')
        self.assertEqual(competitor_pk['ranking'], 3)
        self.assertEqual(competitor_pk['pilot_name'], 'Erik Berendes')
        self.assertEqual(competitor_pk['plane_model'], 'Pik20D')

        expected_igc_url = 'https://archive.soaringspot.com/contest/013/1323/flights/2477/2597322754.igc'
        self.assertEqual(competitor_pk['igc_url'], expected_igc_url)

        # new format
        soaringspot_page = SoaringSpotDaily(
            'https://www.soaringspot.com/en_gb/pribina-cup-2025-nitra-2025/results/club/task-6-on-2025-04-24/daily')

        competitors = soaringspot_page._get_competitors_info(include_hc_competitors=False, include_dns_competitors=True)
        self.assertEqual(len(competitors), 15)
        competitors = soaringspot_page._get_competitors_info(include_hc_competitors=False, include_dns_competitors=False)
        self.assertEqual(len(competitors), 13)
        competitor_pk = soaringspot_page._get_competitors_info(include_hc_competitors=False)[1]

        self.assertEqual(competitor_pk['competition_id'], 'X11')
        self.assertEqual(competitor_pk['ranking'], 2)
        self.assertEqual(competitor_pk['pilot_name'], 'Kengo Matsumoto')
        self.assertEqual(competitor_pk['plane_model'], 'ASW-20')

    def test_get_competitors_info_relative_downloads(self):
        """relative IGC URLs"""
        soaringspot_page = SoaringSpotDaily(
            'https://www.soaringspot.com/en_gb/nation-gliding-championships-taupo-2020/results/racing/task-5-on-2020-02-10/daily'
        )
        competitors = soaringspot_page._get_competitors_info(include_hc_competitors=False)
        self.assertEqual(len(competitors), 10)

    # disabled because this URL is no longer used. unclear whether all dev urls are cleared
    # def test_get_competitors_dev_url(self):
    #     soaringspot_page = SoaringSpotDaily(
    #         'https://dev.soaringspot.com/en_gb/53-hww/results/std/task-6-on-2019-06-01/daily')
    #
    #     competitor_a1 = soaringspot_page._get_competitors_info(include_hc_competitors=False)[0]
    #
    #     self.assertEqual(competitor_a1['competition_id'], 'A1')
    #     self.assertEqual(competitor_a1['ranking'], 1)
    #
    #     expected_igc_url = 'https://dev.soaringspot.com/en_gb/download-contest-flight/2818-5941231725'
    #     self.assertEqual(competitor_a1['igc_url'], expected_igc_url)

    def test_get_competition_day(self):
        soaringspot_page = SoaringSpotDaily(
            'https://www.soaringspot.com/en/sallandse-tweedaagse-2014/results/club/task-1-on-2014-06-21/daily')

        competition_name, date, plane_class = soaringspot_page._get_competition_day_info()

        self.assertEqual(competition_name, 'sallandse-tweedaagse-2014')
        self.assertEqual(plane_class, 'club')
        self.assertEqual(date, datetime.date(2014, 6, 21))

    def test_get_task_rules(self):
        lseeyou_tsk_line = 'LSEEYOU TSK,NoStart=13:29:00,TaskTime=03:30:00,WpDis=False,' \
                           'MinDis=True,NearDis=0.5km,NearAlt=200.0m,MinFinAlt=0.0km'

        start_opening, t_min, multi_start = get_task_rules(lseeyou_tsk_line)

        self.assertEqual(start_opening, datetime.time(13, 29, 0))
        self.assertEqual(t_min, datetime.timedelta(hours=3, minutes=30, seconds=0))

    def test_get_info_from_comment_lines_no_lcu_no_lseeyou(self):
        """
        Some IGC files from soaringspot seem to miss the task information written in LCU and LSEEYOU lines
        This test checks that the function then return a None task.
        """

        cwd = os.path.dirname(__file__)
        igc_path = os.path.join(cwd, '..', 'igc_files', 'missing_lcu_lseeyou_lines.igc')

        # try:  # try utf-8
        with open(igc_path, 'r', encoding='latin1') as f:
            parsed_igc_file = Reader().read(f)

        task, contest_information, competitor_information = get_info_from_comment_lines(parsed_igc_file, date=datetime.date(2023, 7, 4))
        self.assertIsNone(task, None)
