"""
Helper functions for SGP (Sailplane Grand Prix) competitions.
This module provides functionality to access competition data from the SGP API endpoints
and download IGC files for analysis.
"""
import json
import re
import datetime
from typing import List, Dict, Tuple, Optional
import urllib.request
import logging

from aerofiles.igc import Reader

from opensoar.competition.competition_day import CompetitionDay
from opensoar.competition.competitor import Competitor
from opensoar.competition.daily_results_page import DailyResultsPage
from opensoar.task.task import Task
from opensoar.task.waypoint import Waypoint
from opensoar.task.race_task import RaceTask

logger = logging.getLogger(__name__)

class SGPDaily(DailyResultsPage):
    """
    Helper class for dealing with SGP (Sailplane Grand Prix) daily result pages.
    This class interfaces with the SGP API to retrieve competition data.
    """
    
    # API endpoints
    BASE_API_URL = "https://www.crosscountry.aero/c/sgp/rest"
    FLIGHT_DOWNLOAD_URL = "https://www.crosscountry.aero/flight/download/sgp"
    
    def __init__(self, url: str):
        """
        Initialize with the URL to the SGP API.
        
        Args:
            url: URL to the SGP API, in format:
                 https://www.crosscountry.aero/c/sgp/rest/day/{comp_id}/{day_id}
                 or
                 https://www.crosscountry.aero/c/sgp/rest/comp/{comp_id}
        """
        super().__init__(url)
        
        # Extract competition ID and day ID from the URL
        self.competition_id = None
        self.day_id = None
        self._extract_ids_from_url(url)
        
        # API data will be loaded on demand
        self._competition_data = None
        self._day_data = None
    
    def _extract_ids_from_url(self, url: str):
        """
        Extract competition ID and day ID from the URL.
        
        Args:
            url: URL to the SGP API
        """
        # Try to match day URL pattern
        day_pattern = r'crosscountry\.aero/c/sgp/rest/day/(\d+)/(\d+)'
        day_match = re.search(day_pattern, url)
        
        if day_match:
            self.competition_id = int(day_match.group(1))
            self.day_id = int(day_match.group(2))
            logger.info(f"Extracted competition ID: {self.competition_id}, day ID: {self.day_id}")
            return
            
        # Try to match competition URL pattern
        comp_pattern = r'crosscountry\.aero/c/sgp/rest/comp/(\d+)'
        comp_match = re.search(comp_pattern, url)
        
        if comp_match:
            self.competition_id = int(comp_match.group(1))
            logger.info(f"Extracted competition ID: {self.competition_id}")
            return
            
        # If it's an sgp.aero URL, we'll need to discover the competition ID
        sgp_pattern = r'sgp\.aero/([^/]+)'
        sgp_match = re.search(sgp_pattern, url)
        
        if sgp_match:
            self.competition_name = sgp_match.group(1)
            logger.info(f"Found SGP competition name: {self.competition_name}, will need to discover API endpoints")
            return
            
        # If no patterns match, warn but don't fail yet
        logger.warning(f"Could not extract IDs from URL: {url}")
    
    def _get_competition_data(self) -> Dict:
        """
        Fetch competition data from the SGP API.
        
        Returns:
            Dictionary with competition data
        """
        if self._competition_data is not None:
            return self._competition_data
        
        if not self.competition_id:
            raise ValueError("No competition ID available")
            
        url = f"{self.BASE_API_URL}/comp/{self.competition_id}"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                self._competition_data = data
                return data
        except Exception as e:
            logger.error(f"Error fetching competition data: {e}")
            raise
    
    def _get_day_data(self) -> Dict:
        """
        Fetch day data from the SGP API.
        
        Returns:
            Dictionary with day data
        """
        if self._day_data is not None:
            return self._day_data
            
        if not self.competition_id:
            raise ValueError("No competition ID available")
            
        if not self.day_id:
            # We need to select a day
            comp_data = self._get_competition_data()
            days = comp_data.get('i', [])
            # Only get the days that have a winner
            days = [day_data for day_data in days if day_data.get('w')]
            
            if not days:
                raise ValueError("No competition days found")
                
            # Sort days by date and get the latest
            sorted_days = sorted(days, key=lambda d: d.get('d', ''), reverse=True)
            self.day_id = sorted_days[0].get('i')
            
            if not self.day_id:
                raise ValueError("Could not determine day ID")
                
            logger.info(f"Selected day ID: {self.day_id}")
            
        url = f"{self.BASE_API_URL}/day/{self.competition_id}/{self.day_id}"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                self._day_data = data
                return data
        except Exception as e:
            logger.error(f"Error fetching day data: {e}")
            raise
    
    def _get_competition_day_info(self) -> Tuple[str, datetime.date, str]:
        """
        Get competition name, date, and class.
        
        Returns:
            tuple containing (competition_name, date, class_name)
        """
        # Get competition data
        comp_data = self._get_competition_data()
        
        if not comp_data:
            raise ValueError("No competition data available")
            
        comp_info = comp_data.get('c', {})
        competition_name = comp_info.get('t', 'Unknown Competition')
        
        # Get day data
        day_data = self._get_day_data()
        
        # Extract date
        timestamp_ms = day_data.get('d')
        if timestamp_ms:
            try:
                day_date = datetime.date.fromtimestamp(timestamp_ms / 1000)
            except ValueError:
                logger.warning(f"Could not parse date: {timestamp_ms}")
                day_date = datetime.date.today()
        else:
            day_date = datetime.date.today()
            
        # Use the class name from competition info
        class_name = "SGP"  # SGP typically has just one class
            
        return competition_name, day_date, class_name
    
    def _get_competitors_info(self, include_hc_competitors: bool = True, include_dns_competitors: bool = False) -> List[Dict]:
        """
        Extract competitor information from the SGP API.
        
        Args:
            include_hc_competitors: Whether to include hors-concours competitors
            include_dns_competitors: Whether to include competitors who did not start
            
        Returns:
            List of dictionaries with competitor information
        """
        # Get day data
        competition_data = self._get_competition_data()
        day_data = self._get_day_data()
        
        competitors_info = []
        
        # Get pilots info
        pilots = competition_data.get('p', {})
        
        # Get results for the day
        results = day_data.get('r', {}).get('s', [])
        
        for result in results:
            pilot_id = result.get('h')
            pilot_info = pilots.get(str(pilot_id), {})
            
            status = result.get('r', '')
            if status in ['DNS', 'DNF'] and not include_dns_competitors:
                continue
                
            # Check for HC (hors concours) status
            is_hc = isinstance(result.get('w'), int) and result.get('w') == 0
            if is_hc and not include_hc_competitors:
                continue
                
            # Extract ranking
            try:
                ranking = int(result.get('q', 0))  # Position in results
            except (ValueError, TypeError):
                ranking = result.get('q', 0)
                
            # Get competition ID (CN)
            competition_id = result.get('j', '')
            
            # Extract pilot name
            first_name = pilot_info.get('f', '')
            last_name = pilot_info.get('l', '')
            pilot_name = f"{first_name} {last_name}".strip()
            
            # Extract glider model
            plane_model = pilot_info.get('s', '')
            
            # Extract IGC URL if available
            igc_id = result.get('w')
            igc_url = f"{self.FLIGHT_DOWNLOAD_URL}/{igc_id}" if igc_id else None
            
            competitors_info.append({
                'ranking': ranking,
                'competition_id': competition_id,
                'igc_url': igc_url,
                'pilot_name': pilot_name,
                'plane_model': plane_model
            })
        
        return competitors_info
    
    def get_available_days(self) -> List[Dict]:
        """
        Get all available days/tasks for this competition.
        
        Returns:
            List of dictionaries with day information
        """
        comp_data = self._get_competition_data()
        days = comp_data.get('i', [])
        
        # Filter out practice days if needed
        race_days = [day for day in days if day.get('y') == 1]  # Type 1 seems to be race days
        
        return race_days

    def generate_competition_day(self, target_directory: str, download_progress=None, start_time_buffer: int = 0):
        """
        Get competition day with all flights from the SGP API.
        
        Args:
            target_directory: Directory in which the IGC files are saved
            download_progress: Optional progress function
            start_time_buffer: Optional relaxation on the start time in seconds
            
        Returns:
            CompetitionDay object
        """
        # Set the directory for downloaded IGC files
        competition_name, date, class_name = self._get_competition_day_info()
        self.set_igc_directory(target_directory, competition_name, class_name, date)
        
        # Get the day data
        day_data = self._get_day_data()
        
        # Get competitors information
        competitors_info = self._get_competitors_info()
        
        # Get task information from the day data
        task_data = day_data.get('k', {}).get('data', {})
        waypoints = self._extract_waypoints(task_data)
        
        # Extract task start time
        start_opening = self._extract_start_opening(day_data)
        
        # Create task object (assuming Race Task for SGP)
        # Get timezone information if available
        timezone_offset = day_data.get('r', {}).get('z')
        timezone = timezone_offset // 3600000 if timezone_offset else None  # Convert from ms to hours
        
        task = RaceTask(waypoints, timezone, start_opening, start_time_buffer)
        
        # Download flights and create Competitor objects
        competitors = []
        files_downloaded = 0
        total_competitors = len(competitors_info)
        
        for competitor_info in competitors_info:
            competition_id = competitor_info['competition_id']
            igc_url = competitor_info['igc_url']
            ranking = competitor_info['ranking']
            plane_model = competitor_info['plane_model']
            pilot_name = competitor_info['pilot_name']
            
            if igc_url is None:
                logger.info(f"No IGC file available for {competition_id}")
                continue
                
            try:
                file_path = self.download_flight(igc_url, competition_id)
                files_downloaded += 1
                
                # Try to read the IGC file with different encodings
                try:
                    # Try utf-8
                    with open(file_path, 'r', encoding='utf-8') as f:
                        parsed_igc = Reader(skip_duplicates=True).read(f)
                except UnicodeDecodeError:
                    # If not utf-8 use latin1
                    with open(file_path, 'r', encoding='latin1') as f:
                        parsed_igc = Reader(skip_duplicates=True).read(f)
                    
                # Create and add the competitor
                trace = parsed_igc['fix_records'][1]
                competitor = Competitor(trace, competition_id, plane_model, ranking, pilot_name)
                competitors.append(competitor)
                
                # Update progress if callback provided
                if download_progress is not None:
                    download_progress(files_downloaded, total_competitors)
                    
            except Exception as e:
                logger.error(f"Error processing competitor {competition_id}: {e}")
                continue
                    
        # Create CompetitionDay object with competitors and task
        competition_day = CompetitionDay(competition_name, date, class_name, competitors, task)
        
        return competition_day

    def _extract_waypoints(self, task_data: Dict) -> List[Waypoint]:
        """
        Extract waypoints from the task data.
        
        Args:
            task_data: Dictionary containing task data
            
        Returns:
            List of Waypoint objects
        """
        waypoints = []
        
        # Extract turnpoints from task data
        turnpoints = task_data.get('g', [])
        
        for tp_idx, tp in enumerate(turnpoints):
            name = tp.get('n', f"TP{tp_idx}")
            lat = tp.get('a')  # Latitude
            lon = tp.get('o')  # Longitude
            
            if lat is None or lon is None:
                logger.warning(f"Skipping waypoint {name}: missing coordinates")
                continue
                
            # Get waypoint type
            wp_type = tp.get('y', 'cylinder')
            radius = tp.get('r', 500)  # Default radius 500m
            
            # Different handling based on waypoint type
            if wp_type == 'line':
                # Start or finish line
                is_line = True
                r_min = None
                angle_min = None
                r_max = radius
                angle_max = 90  # Standard line is 90 degrees to bisector
                
                # Determine if start or finish based on position
                if tp_idx == 0:
                    # Start line
                    sector_orientation = "next"
                elif tp_idx == len(turnpoints) - 1:
                    # Finish line
                    sector_orientation = "previous"
                else:
                    # Unlikely, but default to symmetrical
                    sector_orientation = "symmetrical"
            else:
                # Cylinder or other point type
                is_line = False
                r_min = None
                angle_min = None
                r_max = radius
                angle_max = 180  # Full cylinder
                sector_orientation = "symmetrical"
                
            # Create Waypoint object
            waypoint = Waypoint(
                name=name,
                latitude=lat,
                longitude=lon,
                r_min=r_min,
                angle_min=angle_min,
                r_max=r_max,
                angle_max=angle_max,
                is_line=is_line,
                sector_orientation=sector_orientation
            )
            
            waypoints.append(waypoint)
            
        # Set orientation angles based on waypoint positions
        Task.set_orientation_angles(waypoints)
        
        return waypoints
    
    def _extract_start_opening(self, day_data: Dict) -> Optional[datetime.datetime]:
        """
        Extract start opening time from the day data.
        
        Args:
            day_data: Dictionary containing day data
            
        Returns:
            Start opening time as datetime.datetime or None if not available
        """
        # Get date from day data
        timestamp_ms = day_data.get('d')
        if not timestamp_ms:
            return None
            
        try:
            task_date = datetime.date.fromtimestamp(timestamp_ms / 1000)
        except ValueError:
            logger.warning(f"Could not parse date: {timestamp_ms}")
            return None
            
        # Get start opening time in milliseconds
        start_ms = day_data.get('a')
        if start_ms is None:
            return None
            
        # Convert milliseconds to time
        start_seconds = start_ms // 1000
        hours = start_seconds // 3600
        minutes = (start_seconds % 3600) // 60
        seconds = start_seconds % 60
        
        start_time = datetime.time(hours, minutes, seconds)
        
        # Combine date and time
        start_opening = datetime.datetime.combine(task_date, start_time)
        
        # Set timezone if available
        timezone_offset = day_data.get('r', {}).get('z')
        if timezone_offset:
            timezone_hours = timezone_offset // 3600000  # Convert from milliseconds to hours
            tz = datetime.timezone(datetime.timedelta(hours=timezone_hours))
            start_opening = start_opening.replace(tzinfo=tz)
            
        return start_opening

if __name__ == "__main__":
# Direct API URL for the day
    day_url = "https://www.crosscountry.aero/c/sgp/rest/day/86/1547"

# Create a SGPDaily instance
    sgp_daily = SGPDaily(day_url)

# Directory to store IGC files
    target_directory = "./bin"

# Generate a CompetitionDay with all flights
    competition_day = sgp_daily.generate_competition_day(target_directory)

# Now you can analyze flights using the existing OpenSoar framework
    for competitor in competition_day.competitors:
        competitor.analyse(competition_day.task, classification_method="pysoar")
        
        # Work with the analyzed flight data
        print(f"Competitor: {competitor.competition_id}")
        if competitor.phases:
            thermals = competitor.phases.thermals()
            print(f"  Number of thermals: {len(thermals)}")
