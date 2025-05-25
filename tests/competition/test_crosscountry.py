"""
Unit tests for Crosscountry (Sailplane Grand Prix) module.

This module tests the functionality for accessing Crosscountry API endpoints 
and downloading/analyzing IGC files.
"""
import datetime
import json
import unittest
from unittest import mock
from pathlib import Path

from opensoar.competition.crosscountry import CrosscountryDaily
from opensoar.task.race_task import RaceTask


class MockResponse:
    """Mock urllib.request.urlopen response object."""
    
    def __init__(self, data, status_code=200):
        self.data = json.dumps(data).encode('utf-8')
        self.status = status_code
        
    def read(self):
        return self.data
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass


class TestCrosscountryDaily(unittest.TestCase):
    """Tests for CrosscountryDaily class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.day_url = "https://www.crosscountry.aero/c/sgp/rest/day/86/1547"
        self.comp_url = "https://www.crosscountry.aero/c/sgp/rest/comp/86"
        
        # Sample competition data
        self.comp_data = {
            "p": {
                "123": {
                    "f": "John",
                    "l": "Doe",
                    "s": "LS8"
                },
                "124": {
                    "f": "Jane",
                    "l": "Smith",
                    "s": "ASG-29"
                },
                "125": {
                    "f": "Bob",
                    "l": "Brown",
                    "s": "Ventus"
                }
            },
            "c": {
                "t": "Test Crosscountry Competition",
                "l": "Test Location"
            },
            "i": [
                {
                    "i": 1547,
                    "d": 1618012800000,  # 2021-04-10
                    "y": 1,  # Race day
                    "w": "JV"  # Winner defined
                },
                {
                    "i": 1548,
                    "d": 1618099200000,  # 2021-04-11
                    "y": 1,  # Race day
                    "w": None  # No winner defined
                }
            ]
        }
        
        # Sample day data
        self.day_data = {
            "d": 1618012800000,  # 2021-04-10
            "a": 36000000,  # Start time 10:00:00 (in milliseconds)
            "r": {
                "z": 7200000,  # UTC+2 in milliseconds
                "s": [
                    {
                        "h": 123,
                        "j": "ABC",
                        "q": 1,
                        "r": "",
                        "w": 456
                    },
                    {
                        "h": 124,
                        "j": "DEF",
                        "q": 2,
                        "r": "",
                        "w": 457
                    },
                    {
                        "h": 125,
                        "j": "GHI",
                        "q": 0,
                        "r": "DNS",
                        "w": 0
                    }
                ]
            },
            "k": {
                "data": {
                    "g": [
                        {
                            "n": "Start",
                            "a": 51.0,
                            "o": 10.0,
                            "y": "line",
                            "r": 1000
                        },
                        {
                            "n": "TP1",
                            "a": 51.1,
                            "o": 10.1,
                            "y": "cylinder",
                            "r": 500
                        },
                        {
                            "n": "Finish",
                            "a": 51.0,
                            "o": 10.0,
                            "y": "line",
                            "r": 1000
                        }
                    ]
                }
            }
        }
        
        # Create a temporary directory for downloaded files
        self.temp_dir = Path("./test_igc_files")
        self.temp_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test files
        for file in self.temp_dir.glob("*.igc"):
            file.unlink()
        
        # Remove test directory
        self.temp_dir.rmdir()
    
    def test_extract_ids_from_url_day(self):
        """Test extraction of competition and day IDs from day URL."""
        sgp = CrosscountryDaily(self.day_url)
        
        self.assertEqual(sgp.competition_id, 86)
        self.assertEqual(sgp.day_id, 1547)
    
    def test_extract_ids_from_url_comp(self):
        """Test extraction of competition ID from competition URL."""
        sgp = CrosscountryDaily(self.comp_url)
        
        self.assertEqual(sgp.competition_id, 86)
        self.assertIsNone(sgp.day_id)
    
    @mock.patch('urllib.request.urlopen')
    def test_get_competition_data(self, mock_urlopen):
        """Test fetching competition data from the API."""
        mock_urlopen.return_value = MockResponse(self.comp_data)
        
        sgp = CrosscountryDaily(self.comp_url)
        data = sgp._get_competition_data()
        
        self.assertEqual(data, self.comp_data)
        mock_urlopen.assert_called_once_with(f"{CrosscountryDaily.BASE_API_URL}/comp/86")
    
    @mock.patch('urllib.request.urlopen')
    def test_get_day_data(self, mock_urlopen):
        """Test fetching day data from the API."""
        mock_urlopen.return_value = MockResponse(self.day_data)
        
        sgp = CrosscountryDaily(self.day_url)
        data = sgp._get_day_data()
        
        self.assertEqual(data, self.day_data)
        mock_urlopen.assert_called_once_with(f"{CrosscountryDaily.BASE_API_URL}/day/86/1547")
    
    @mock.patch('urllib.request.urlopen')
    def test_get_day_data_without_day_id(self, mock_urlopen):
        """Test fetching day data when day ID is not provided."""
        mock_urlopen.side_effect = [
            MockResponse(self.comp_data),
            MockResponse(self.day_data)
        ]
        
        sgp = CrosscountryDaily(self.comp_url)
        data = sgp._get_day_data()
        
        self.assertEqual(data, self.day_data)
        self.assertEqual(sgp.day_id, 1547)  # Should select the latest day with a winner
        
        expected_calls = [
            mock.call(f"{CrosscountryDaily.BASE_API_URL}/comp/86"),
            mock.call(f"{CrosscountryDaily.BASE_API_URL}/day/86/1547")
        ]
        mock_urlopen.assert_has_calls(expected_calls)
    
    @mock.patch('urllib.request.urlopen')
    def test_get_competition_day_info(self, mock_urlopen):
        """Test retrieving competition day information."""
        mock_urlopen.side_effect = [
            MockResponse(self.comp_data),
            MockResponse(self.day_data)
        ]
        
        sgp = CrosscountryDaily(self.day_url)
        name, date, class_name = sgp._get_competition_day_info()
        
        self.assertEqual(name, "Test Crosscountry Competition")
        self.assertEqual(date, datetime.date(2021, 4, 10))
        self.assertEqual(class_name, "Default")
    
    @mock.patch('urllib.request.urlopen')
    def test_get_competitors_info(self, mock_urlopen):
        """Test retrieving competitor information."""
        # Need to mock both competition data and day data since both are used
        mock_urlopen.side_effect = [
            MockResponse(self.comp_data),  # For _get_competition_data call
            MockResponse(self.day_data)    # For _get_day_data call
        ]
        
        sgp = CrosscountryDaily(self.day_url)
        # Force caching of competition data
        sgp._competition_data = self.comp_data
        # Force caching of day data
        sgp._day_data = self.day_data
        
        competitors = sgp._get_competitors_info(include_dns_competitors=False)
        
        self.assertEqual(len(competitors), 2)  # Should exclude DNS competitor
        
        self.assertEqual(competitors[0]['competition_id'], "ABC")
        self.assertEqual(competitors[0]['pilot_name'], "John Doe")
        self.assertEqual(competitors[0]['plane_model'], "LS8")
        self.assertEqual(competitors[0]['ranking'], 1)
        self.assertEqual(competitors[0]['igc_url'], f"{CrosscountryDaily.FLIGHT_DOWNLOAD_URL}/456")
        
        # Test including DNS competitors
        competitors = sgp._get_competitors_info(include_dns_competitors=True)
        self.assertEqual(len(competitors), 3)  # Should include DNS competitor
    
    @mock.patch('urllib.request.urlopen')
    def test_get_available_days(self, mock_urlopen):
        """Test retrieving available competition days."""
        mock_urlopen.return_value = MockResponse(self.comp_data)
        
        sgp = CrosscountryDaily(self.comp_url)
        days = sgp.get_available_days()
        
        self.assertEqual(len(days), 2)
        self.assertEqual(days[0]['i'], 1547)
        self.assertEqual(days[1]['i'], 1548)
    
    def test_extract_waypoints(self):
        """Test extracting waypoints from task data."""
        task_data = self.day_data['k']['data']
        
        sgp = CrosscountryDaily(self.day_url)
        waypoints = sgp._extract_waypoints(task_data)
        
        self.assertEqual(len(waypoints), 3)
        
        # Check start point
        self.assertEqual(waypoints[0].name, "Start")
        self.assertEqual(waypoints[0].latitude, 51.0)
        self.assertEqual(waypoints[0].longitude, 10.0)
        self.assertEqual(waypoints[0].r_max, 1000)
        self.assertEqual(waypoints[0].angle_max, 90)
        self.assertTrue(waypoints[0].is_line)
        self.assertEqual(waypoints[0].sector_orientation, "next")
        
        # Check turnpoint
        self.assertEqual(waypoints[1].name, "TP1")
        self.assertEqual(waypoints[1].latitude, 51.1)
        self.assertEqual(waypoints[1].longitude, 10.1)
        self.assertEqual(waypoints[1].r_max, 500)
        self.assertEqual(waypoints[1].angle_max, 180)
        self.assertFalse(waypoints[1].is_line)
        
        # Check finish point
        self.assertEqual(waypoints[2].name, "Finish")
        self.assertEqual(waypoints[2].r_max, 1000)
        self.assertTrue(waypoints[2].is_line)
        self.assertEqual(waypoints[2].sector_orientation, "previous")
    
    def test_extract_start_opening(self):
        """Test extracting start opening time from day data."""
        sgp = CrosscountryDaily(self.day_url)
        start_opening = sgp._extract_start_opening(self.day_data)
        
        expected_datetime = datetime.datetime(
            2021, 4, 10, 10, 0, 0, 
            tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )
        self.assertEqual(start_opening, expected_datetime)
    
    @mock.patch('urllib.request.urlopen')
    @mock.patch('opensoar.competition.crosscountry.CrosscountryDaily.download_flight')
    @mock.patch('opensoar.competition.crosscountry.Reader')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_generate_competition_day(self, mock_open, mock_reader, mock_download, mock_urlopen):
        """Test generating a CompetitionDay object from Crosscountry data."""
        # Setup mocks
        mock_urlopen.side_effect = [
            MockResponse(self.comp_data),  # For _get_competition_data call
            MockResponse(self.day_data),   # For _get_day_data call
            MockResponse(self.comp_data),  # For _get_competition_day_info -> _get_competition_data
            MockResponse(self.day_data),   # For _get_competition_day_info -> _get_day_data
            MockResponse(self.day_data),   # For additional _get_day_data call
            MockResponse(self.comp_data),  # For _get_competitors_info -> _get_competition_data
            MockResponse(self.day_data)    # For _get_competitors_info -> _get_day_data
        ]
        
        # Cache data to prevent too many API calls
        sgp = CrosscountryDaily(self.day_url)
        sgp._competition_data = self.comp_data
        sgp._day_data = self.day_data
        
        # Mock downloading IGC files
        mock_download.side_effect = lambda url, cn: f"{self.temp_dir}/{cn}.igc"
        
        # Mock IGC file content and reading
        mock_igc_content = "AFILETYPENM"  # Minimal IGC content for testing
        mock_open.return_value.read.return_value = mock_igc_content
        
        # Mock the Reader class and its read method
        mock_parser = mock.MagicMock()
        mock_parser.read.return_value = {
            'fix_records': (None, [{'time': '101010', 'lat': 51.0, 'lon': 10.0}])
        }
        mock_reader.return_value = mock_parser
        
        # Create CrosscountryDaily instance and generate competition day
        competition_day = sgp.generate_competition_day(str(self.temp_dir))
        
        # Verify results
        self.assertEqual(competition_day.name, "Test Crosscountry Competition")
        self.assertEqual(competition_day.date, datetime.date(2021, 4, 10))
        self.assertEqual(competition_day.plane_class, "Default")
        
        # Verify competitors were created
        self.assertEqual(len(competition_day.competitors), 2)
        self.assertEqual(competition_day.competitors[0].competition_id, "ABC")
        self.assertEqual(competition_day.competitors[0].pilot_name, "John Doe")
        
        # Verify task was created correctly
        self.assertIsInstance(competition_day.task, RaceTask)
        self.assertEqual(len(competition_day.task.waypoints), 3)
        
        # Verify that files were properly opened and read
        mock_open.assert_called()
        mock_reader.return_value.read.assert_called()

if __name__ == "__main__":
    unittest.main()
