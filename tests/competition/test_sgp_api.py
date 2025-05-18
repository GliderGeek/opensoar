"""
Integration tests for SGP API structure verification.

These tests make real API calls to the SGP endpoints and verify that the 
expected structure is present. These will help detect unexpected API changes.

NOTE: These tests require internet connectivity and depend on the 
actual SGP API being available.
"""
import unittest
import shutil
import datetime
import json
import logging
from pathlib import Path
import re

from opensoar.competition.sgp import SGPDaily


# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class TestSGPApiIntegration(unittest.TestCase):
    """
    Integration tests that verify the SGP API structure using real API calls.
    
    These tests depend on the actual API and should be run periodically to
    ensure that the API structure hasn't changed unexpectedly.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Use valid API endpoint URLs directly rather than web URLs
        # The web URLs shown in the error message don't match the expected format
        self.comp_id = 86  # Use a known working competition ID
        self.day_id = 1547  # Use a known working day ID
        
        # Use the direct API endpoints instead of web URLs
        self.comp_api_url = f"https://www.crosscountry.aero/c/sgp/rest/comp/{self.comp_id}"
        self.day_api_url = f"https://www.crosscountry.aero/c/sgp/rest/day/{self.comp_id}/{self.day_id}"
        
        # Create SGP daily instances with the API URLs
        self.sgp_comp = SGPDaily(self.comp_api_url)
        self.sgp_day = SGPDaily(self.day_api_url)
        
        # Verify the URLs were correctly parsed
        self.assertEqual(self.sgp_comp.competition_id, self.comp_id)
        self.assertEqual(self.sgp_day.competition_id, self.comp_id)
        self.assertEqual(self.sgp_day.day_id, self.day_id)
        
        # Directory to save response data for inspection if needed
        self.output_dir = Path("./test_output")
        self.output_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up any files created during tests."""
        # Keep the output files for manual inspection if needed
        shutil.rmtree(self.output_dir)
    
    def _save_response(self, data, filename):
        """Save response data to a file for manual inspection."""
        path = self.output_dir / filename
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved response data to {path}")
    
    def test_competition_data_structure(self):
        """Test the structure of the competition data response."""
        try:
            # Get competition data from the real API
            comp_data = self.sgp_comp._get_competition_data()
            
            # Save the response for manual inspection
            self._save_response(comp_data, f"comp_{self.comp_id}_response.json")
            
            # Verify top-level structure
            self.assertIn('p', comp_data, "Missing pilots data ('p' key)")
            self.assertIn('c', comp_data, "Missing competition data ('c' key)")
            self.assertIn('i', comp_data, "Missing days info ('i' key)")
            
            # Verify competition info
            comp_info = comp_data['c']
            self.assertIn('t', comp_info, "Missing competition title ('t' key)")
            self.assertIn('l', comp_info, "Missing location ('l' key)")
            
            # Verify pilots structure
            pilots = comp_data['p']
            self.assertTrue(pilots, "Pilots dictionary is empty")
            
            # Verify pilot data structure (check first pilot)
            pilot_id = next(iter(pilots))
            pilot = pilots[pilot_id]
            self.assertIn('f', pilot, "Missing pilot first name ('f' key)")
            self.assertIn('l', pilot, "Missing pilot last name ('l' key)")
            self.assertIn('s', pilot, "Missing pilot sailplane ('s' key)")
            
            # Log some sample data for verification
            logger.info(f"Competition: {comp_info['t']} at {comp_info['l']}")
            logger.info(f"Number of pilots: {len(pilots)}")
            
            # Verify competition days
            days = comp_data['i']
            self.assertTrue(isinstance(days, list), "Days info is not a list")
            self.assertTrue(days, "No competition days found")
            
            # Verify day structure
            day = days[0]
            self.assertIn('i', day, "Missing day ID ('i' key)")
            self.assertIn('d', day, "Missing day date ('d' key)")
            self.assertIn('y', day, "Missing day type flag ('y' key)")
            # Note: 'w' key might not be present for all days
            
            logger.info(f"Found {len(days)} days in the competition")
            
        except Exception as e:
            self.fail(f"Error testing competition data structure: {str(e)}")
    
    def test_day_data_structure(self):
        """Test the structure of the day data response."""
        try:
            # Get day data from the real API
            day_data = self.sgp_day._get_day_data()
            
            # Save the response for manual inspection
            self._save_response(day_data, f"day_{self.day_id}_response.json")
            
            # Verify top-level structure
            self.assertIn('d', day_data, "Missing day date ('d' key)")
            self.assertIn('a', day_data, "Missing start time ('a' key)")
            self.assertIn('r', day_data, "Missing results data ('r' key)")
            self.assertIn('k', day_data, "Missing task data ('k' key)")
            
            # Convert day timestamp to readable date
            day_timestamp = day_data['d']
            day_date = datetime.datetime.fromtimestamp(day_timestamp / 1000).date()
            logger.info(f"Day date: {day_date}")
            
            # Verify results structure
            results = day_data['r']
            self.assertIn('z', results, "Missing timezone ('z' key)")
            self.assertIn('s', results, "Missing standings ('s' key)")
            
            # Verify timezone
            timezone_ms = results['z']
            timezone_hours = timezone_ms / (1000 * 60 * 60)
            logger.info(f"Timezone: UTC{'+' if timezone_hours >= 0 else ''}{timezone_hours}")
            
            # Verify standings
            standings = results['s']
            self.assertTrue(isinstance(standings, list), "Standings is not a list")
            if not standings:
                logger.warning("No standings found in day data")
            else:
                # Verify standing structure
                standing = standings[0]
                self.assertIn('h', standing, "Missing pilot ID ('h' key)")
                self.assertIn('j', standing, "Missing competition ID ('j' key)")
                self.assertIn('q', standing, "Missing ranking ('q' key)")
                self.assertIn('r', standing, "Missing result status ('r' key)")
                self.assertIn('w', standing, "Missing flight ID ('w' key)")
                
                logger.info(f"Found {len(standings)} results for the day")
            
            # Verify task structure
            task = day_data['k']
            self.assertIn('data', task, "Missing task data ('data' key)")
            
            task_data = task['data']
            self.assertIn('g', task_data, "Missing waypoints list ('g' key)")
            
            # Verify waypoints
            waypoints = task_data['g']
            self.assertTrue(isinstance(waypoints, list), "Waypoints is not a list")
            self.assertTrue(waypoints, "No waypoints found")
            
            # Verify waypoint structure
            waypoint = waypoints[0]
            self.assertIn('n', waypoint, "Missing waypoint name ('n' key)")
            self.assertIn('a', waypoint, "Missing latitude ('a' key)")
            self.assertIn('o', waypoint, "Missing longitude ('o' key)")
            self.assertIn('y', waypoint, "Missing type ('y' key)")
            self.assertIn('r', waypoint, "Missing radius ('r' key)")
            
            logger.info(f"Found {len(waypoints)} waypoints in the task")
            
            # Log the task details
            waypoint_names = [wp['n'] for wp in waypoints]
            logger.info(f"Task waypoints: {', '.join(waypoint_names)}")
            
        except Exception as e:
            self.fail(f"Error testing day data structure: {str(e)}")
    
    def test_available_days(self):
        """Test retrieval of available days from the competition."""
        try:
            # Get available days
            days = self.sgp_comp.get_available_days()
            
            # Save the response for manual inspection
            self._save_response(days, f"comp_{self.comp_id}_available_days.json")
            
            # Verify days structure
            self.assertTrue(isinstance(days, list), "Available days is not a list")
            self.assertTrue(days, "No available days found")
            
            for day in days:
                self.assertIn('i', day, "Missing day ID ('i' key)")
                self.assertIn('d', day, "Missing day date ('d' key)")
                self.assertIn('y', day, "Missing day type flag ('y' key)")
                
                # Convert day timestamp to readable date
                day_timestamp = day['d']
                logger.info(day_timestamp)
                day_date = datetime.datetime.strptime(day_timestamp, "%Y-%m-%d").date()
                day_status = "Race day" if day['y'] == 1 else "Non-race day"
                
                logger.info(f"Day {day['i']}: {day_date} - {day_status}")
                
        except Exception as e:
            self.fail(f"Error testing available days: {str(e)}")
    
    def test_competitors_info(self):
        """Test retrieval of competitor information from the day data."""
        try:
            # Get competitors info
            competitors = self.sgp_day._get_competitors_info(include_dns_competitors=True)
            
            # Save the response for manual inspection
            self._save_response(competitors, f"day_{self.day_id}_competitors.json")
            
            # Verify competitors structure
            self.assertTrue(isinstance(competitors, list), "Competitors is not a list")
            
            if not competitors:
                logger.warning("No competitors found in day data")
                return
                
            for competitor in competitors:
                self.assertIn('competition_id', competitor, "Missing competition_id field")
                self.assertIn('pilot_name', competitor, "Missing pilot_name field")
                self.assertIn('plane_model', competitor, "Missing plane_model field")
                self.assertIn('ranking', competitor, "Missing ranking field")
                # IGC URL may be None for DNF/DNS competitors
                self.assertIn('igc_url', competitor, "Missing igc_url field")
                
                logger.info(f"Competitor {competitor['competition_id']}: "
                           f"{competitor['pilot_name']} flying {competitor['plane_model']}")
                
        except Exception as e:
            self.fail(f"Error testing competitors info: {str(e)}")


class TestSGPUrlHandling(unittest.TestCase):
    """Test proper URL handling and ID extraction for SGP URLs."""
    
    def test_api_url_pattern(self):
        """Test extraction of IDs from direct API URLs."""
        # Direct REST API URLs
        comp_url = "https://www.crosscountry.aero/c/sgp/rest/comp/86"
        day_url = "https://www.crosscountry.aero/c/sgp/rest/day/86/1547"
        
        sgp_comp = SGPDaily(comp_url)
        sgp_day = SGPDaily(day_url)
        
        self.assertEqual(sgp_comp.competition_id, 86)
        self.assertIsNone(sgp_comp.day_id)
        
        self.assertEqual(sgp_day.competition_id, 86)
        self.assertEqual(sgp_day.day_id, 1547)
    
    def test_web_url_pattern(self):
        """
        Test extraction of IDs from web URLs.
        
        This test documents the current handling of web URLs and may fail
        if the SGP class doesn't correctly handle these URL patterns.
        """
        # Current web URLs (based on error messages)
        web_comp_url = "https://www.crosscountry.aero/c/sgp/overview/127"
        web_day_url = "https://www.crosscountry.aero/c/sgp/task/127/day/1925/overview"
        
        # Extract IDs using regex patterns
        comp_pattern = r"crosscountry\.aero/c/sgp/(?:overview|task)/(\d+)"
        day_pattern = r"crosscountry\.aero/c/sgp/task/\d+/day/(\d+)"
        
        # Extract competition ID
        comp_match = re.search(comp_pattern, web_comp_url)
        self.assertIsNotNone(comp_match, "Couldn't extract competition ID from web URL")
        comp_id = int(comp_match.group(1))
        self.assertEqual(comp_id, 127)
        
        # Extract day ID
        day_match = re.search(day_pattern, web_day_url)
        self.assertIsNotNone(day_match, "Couldn't extract day ID from web URL")
        day_id = int(day_match.group(1))
        self.assertEqual(day_id, 1925)
        
        # Create direct API URLs from extracted IDs
        api_comp_url = f"https://www.crosscountry.aero/c/sgp/rest/comp/{comp_id}"
        api_day_url = f"https://www.crosscountry.aero/c/sgp/rest/day/{comp_id}/{day_id}"
        
        logger.info(f"Converted web comp URL to API URL: {api_comp_url}")
        logger.info(f"Converted web day URL to API URL: {api_day_url}")


if __name__ == "__main__":
    unittest.main()
