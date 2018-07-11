import unittest

import datetime

from opensoar.competition.strepla import get_waypoint_name_lat_long, get_waypoints, get_waypoint, \
    StreplaDaily, get_task_and_competitor_info


class TestStrepla(unittest.TestCase):
    lscsc_lines = [
        'LSCSCS:AP4 Fronhofen Strassen-T:N4942358:E00851490',
        'LSCSCT:074 Main Lohr-M:N4959700:E00934900',
        'LSCSCT:050 Herbstein Kirche:N5033733:E00920800',
        'LSCSCT:120 St Goar Bf:N5009067:E00742850',
        'LSCSCT:079 Meisenheim Station:N4942550:E00739767',
        'LSCSCT:010 Bensheim Lindenfels Krehberg TV:N4941150:E00843883',
        'LSCSCF:ZP Reinheim (Darmstadt Dieburg):N4950433:E00851050',
    ]

    lscsr_lines = [
        'LSCSRSLINE:20000',
        'LSCSRTKEYHOLE:500:10000:90',
        'LSCSRFCYLINDER:2500',
    ]

    lscsd_lines = [
        'LSCSDCID:IBG',
        'LSCSDName:Leip, Dennis',
        'LSCSDGate open:10:44',
        'LSCSDGate close:12:14',
        'LSCSDTime window:03:30',
        'LSCSDmax Elevation start:1200',
        'LSCSDmax Elevation:3000',
        'LSCSDQNH:1021',
        'LSCSDElevation start:155',
    ]

    def test_waypoint_info_parsing(self):
        """test whether name and coordinates are correctly read from line in igc file"""

        lscs_line_tp = 'LSCSCT:074 Main Lohr-M:N4959700:E00934900'
        name, lat, lon = get_waypoint_name_lat_long(lscs_line_tp)

        self.assertEqual(name, '074 Main Lohr-M')
        self.assertAlmostEqual(lat, 49.9950, places=4)
        self.assertAlmostEqual(lon, 9.5817, places=4)

    def test_get_waypoints(self):
        task_info, competitor_information = get_task_and_competitor_info(self.lscsd_lines, self.lscsr_lines)
        waypoints = get_waypoints(self.lscsc_lines, task_info)
        self.assertEqual(len(waypoints), 7)

    def test_get_waypoint(self):

        lscsc_line = 'LSCSCS:AP4 Fronhofen Strassen-T:N4942358:E00851490'

        task_info, competitor_information = get_task_and_competitor_info(self.lscsd_lines, self.lscsr_lines)
        waypoint = get_waypoint(lscsc_line, task_info, n=0, n_tp=7)

        self.assertEqual(waypoint.name, 'AP4 Fronhofen Strassen-T')
        self.assertTrue(waypoint.is_line)


class TestStreplaDaily(unittest.TestCase):

    daily_page = StreplaDaily("http://www.strepla.de/scs/public/scoreDay.aspx?cId=222&idDay=2388")

    def test_get_competitionday_info(self):
        competition_name, date, plane_class = self.daily_page._get_competition_day_info()
        self.assertEqual(competition_name, 'Reinheim_Cup')
        self.assertEqual(plane_class, 'Standard')
        self.assertEqual(date, datetime.date(2013, 8, 5))

    def test_get_table_info(self):
        competitors_info = self.daily_page._get_table_info(include_hc_competitors=False)
        self.assertEqual(len(competitors_info), 10)
