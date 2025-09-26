import datetime
import os
import unittest

from aerofiles.igc import Reader

from opensoar.competition.competitor import Competitor
from opensoar.competition.strepla import (
    CompetitorInformation,
    TaskInfo,
    get_info_from_comment_lines,
    get_task_and_competitor_info,
    get_waypoint,
    get_waypoint_name_lat_long,
    get_waypoints,
)
from opensoar.task.aat import AAT


class TestStrepla(unittest.TestCase):
    lscsc_lines = [
        "LSCSCS:AP4 Fronhofen Strassen-T:N4942358:E00851490",
        "LSCSCT:074 Main Lohr-M:N4959700:E00934900",
        "LSCSCT:050 Herbstein Kirche:N5033733:E00920800",
        "LSCSCT:120 St Goar Bf:N5009067:E00742850",
        "LSCSCT:079 Meisenheim Station:N4942550:E00739767",
        "LSCSCT:010 Bensheim Lindenfels Krehberg TV:N4941150:E00843883",
        "LSCSCF:ZP Reinheim (Darmstadt Dieburg):N4950433:E00851050",
    ]

    lscsr_lines = [
        "LSCSRSLINE:20000",
        "LSCSRTKEYHOLE:500:10000:90",
        "LSCSRFCYLINDER:2500",
    ]

    lscsd_lines = [
        "LSCSDCID:IBG",
        "LSCSDName:Leip, Dennis",
        "LSCSDGate open:10:44",
        "LSCSDGate close:12:14",
        "LSCSDTime window:03:30",
        "LSCSDmax Elevation start:1200",
        "LSCSDmax Elevation:3000",
        "LSCSDQNH:1021",
        "LSCSDElevation start:155",
    ]

    lscsa_lines = []

    def setUp(self):
        self.task_info, self.competitor_info = get_task_and_competitor_info(
            self.lscsd_lines, self.lscsr_lines, self.lscsa_lines
        )

    def test_waypoint_info_parsing(self):
        """Test whether name and coordinates are correctly read from line in igc file"""
        lscs_line_tp = "LSCSCT:074 Main Lohr-M:N4959700:E00934900"
        name, lat, lon = get_waypoint_name_lat_long(lscs_line_tp)

        self.assertEqual(name, "074 Main Lohr-M")
        self.assertAlmostEqual(lat, 49.9950, places=4)
        self.assertAlmostEqual(lon, 9.5817, places=4)

    def test_get_waypoints(self):
        waypoints = get_waypoints(self.lscsc_lines, self.task_info)
        self.assertEqual(len(waypoints), 7)

    def test_get_waypoint(self):
        """Test parsing of a single waypoint and its sector type"""
        lscsc_line = self.lscsc_lines[0]
        waypoint = get_waypoint(lscsc_line, self.task_info, n=0, n_tp=7)

        self.assertEqual(waypoint.name, "AP4 Fronhofen Strassen-T")
        self.assertTrue(waypoint.is_line)
        self.assertEqual(waypoint.sector_orientation, "next")
        self.assertEqual(waypoint.angle_max, 90)

    def test_task_info_fields(self):
        """Test that TaskInfo dataclass fields are correctly populated"""
        self.assertIsInstance(self.task_info, TaskInfo)
        self.assertTrue(self.task_info.tp_key)
        self.assertEqual(self.task_info.tp_key_dim, [500, 10000, 90])
        self.assertEqual(self.task_info.s_line_rad, 10000)
        self.assertEqual(self.task_info.f_cyl_rad, 2500)

    def test_competitor_info_fields(self):
        """Test that CompetitorInformation dataclass fields are correctly populated"""
        self.assertIsInstance(self.competitor_info, CompetitorInformation)
        self.assertEqual(self.competitor_info.pilot_name, "Leip, Dennis")
        self.assertEqual(self.competitor_info.competition_id, "IBG")

    def test_aat_from_file(self):
        """
        Test if AAT is correctly recognised and waypoints are correct.
        File from: https://www.strepla.de/scs/Public/scoreDay.aspx?cId=451&idDay=7912, competitor 1 CX
        """
        file_path = os.path.join(
            os.path.dirname(__file__), "..", "igc_files", "aat_strepla.igc"
        )

        with open(file_path, "r", encoding="utf-8") as f:
            parsed_igc_file = Reader().read(f)

        trace_errors, trace = parsed_igc_file["fix_records"]
        self.assertEqual(len(trace_errors), 0)

        task, task_info, competitor_info = get_info_from_comment_lines(parsed_igc_file)

        self.assertIsInstance(task, AAT)
        self.assertEqual(task.t_min, datetime.timedelta(hours=2, minutes=30))

        expected_waypoints = [
            ("AP3 Muellhalde", None),
            ("Loreley", 20000),
            ("Kusel", 40000),
            ("Loreley", 20000),
            ("ZP Anspach/Taunus", None),
        ]

        self.assertEqual(len(task.waypoints), len(expected_waypoints))

        for i, waypoint in enumerate(task.waypoints):
            with self.subTest(i=i):
                expected_name, expected_r_max = expected_waypoints[i]
                self.assertEqual(waypoint.name, expected_name)
                if 0 < i < len(expected_waypoints) - 1:
                    self.assertEqual(waypoint.r_max, expected_r_max)

        competitor = Competitor(trace, "CX", "Discus2b", 1, "Karsten Leucker")
        competitor.analyse(task, "pysoar")

        self.assertEqual(competitor.trip.refined_start_time.hour, 13)
        self.assertEqual(competitor.trip.refined_start_time.minute, 22)
        self.assertLessEqual(abs(competitor.trip.refined_start_time.second - 40), 1)

        dist_diff = sum(competitor.trip.distances) - 283500
        self.assertEqual(len(competitor.trip.fixes), len(expected_waypoints))
        self.assertLessEqual(abs(dist_diff), 1000)

    def test_empty_inputs(self):
        """Test behavior when input lists are empty"""
        task_info, competitor_info = get_task_and_competitor_info([], [], [])
        self.assertIsInstance(task_info, TaskInfo)
        self.assertIsInstance(competitor_info, CompetitorInformation)
        self.assertFalse(task_info.aat)
        self.assertIsNone(competitor_info.pilot_name)

    def test_malformed_line_handling(self):
        """Test robustness against malformed input lines"""
        malformed_lines = [
            "LSCSRSLINE",
            "LSCSRTKEYHOLE:bad:data",
            "LSCSDGate open:xx:yy",
        ]
        try:
            get_task_and_competitor_info(malformed_lines, [], [])
        except Exception as e:
            self.fail(f"Function raised an exception on malformed input: {e}")
