import unittest

from OpenSoar.competition.strepla import get_waypoint_name_lat_long


class TestStrepla(unittest.TestCase):

    def test_waypoint_info_parsing(self):
        """test whether name and coordinates are correctly read from line in igc file"""

        lscs_line_tp = 'LSCSCT:074 Main Lohr-M:N4959700:E00934900'
        name, lat, lon = get_waypoint_name_lat_long(lscs_line_tp)

        self.assertEqual(name, '074 Main Lohr-M')
        self.assertAlmostEqual(lat, 49.9950, places=4)
        self.assertAlmostEqual(lon, 9.5817, places=4)
