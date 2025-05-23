"""
Helper functions for SoaringSpot competitions.
The files from SoaringSpot always contain task information, which can be used for competition analysis.
"""
import datetime
import re
from typing import List, Tuple, Union, Optional
from urllib.error import URLError
from urllib.parse import urljoin

from aerofiles.igc import Reader
from bs4 import BeautifulSoup

from opensoar.competition.competition_day import CompetitionDay
from opensoar.competition.competitor import Competitor
from opensoar.task.aat import AAT
from opensoar.task.race_task import RaceTask
from opensoar.task.task import Task
from opensoar.task.waypoint import Waypoint
from opensoar.utilities.helper_functions import dm2dd
from opensoar.competition.daily_results_page import DailyResultsPage
from opensoar.utilities.helper_functions import double_iterator


def get_comment_lines_from_parsed_file(parsed_igc_file: dict) -> List[str]:
    """In the parsed file, lines are split into source and comment. This function stiches them back together"""
    records = parsed_igc_file['comment_records'][1]
    return ["L{}{}".format(record['source'], record['comment']) for record in records]


def get_task_rules(lseeyou_tsk_line: str) -> Tuple[datetime.time, datetime.timedelta, bool]:
    start_opening = None
    t_min = None
    multi_start = False
    for element in lseeyou_tsk_line.split(','):
        if element.startswith('TaskTime'):
            time = element.split('=')[1]
            hours, minutes, seconds = [int(part) for part in time.split(':')]
            t_min = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
        elif element.startswith('NoStart'):
            time = element.split('=')[1]
            hours, minutes, seconds = [int(part) for part in time.split(':')]
            start_opening = datetime.time(hours, minutes, seconds)
        elif element.startswith('MultiStart:'):
            multi_start = element.split(':')[1] == 'True'

    return start_opening, t_min, multi_start


def get_info_from_comment_lines(parsed_igc_file: dict, date: datetime.date, start_time_buffer: int=0) -> Tuple[Optional[Task], dict, dict]:
    """
    There is specific contest information stored in the comment lines of the IGC files.
    This function extracts this information
    """

    lcu_lines = list()
    lseeyou_lines = list()

    contest_information = dict()
    competitor_information = dict()

    comment_lines = get_comment_lines_from_parsed_file(parsed_igc_file)

    timezone = None
    t_min = None
    start_opening = None
    multi_start = False

    for line in comment_lines:
        if line.startswith('LCU::C'):
            lcu_lines.append(line)
        elif line.startswith('LSEEYOU OZ'):
            lseeyou_lines.append(line)
        elif line.startswith('LCU::HPGTYGLIDERTYPE:'):
            competitor_information['plane_model'] = line.split(':')[3]
        elif line.startswith('LCU::HPPLTPILOT:'):
            competitor_information['pilot_name'] = line.split(':')[3]
        elif line.startswith('LCU::HPCIDCOMPETITIONID:'):
            competitor_information['competition_id'] = line.split(':')[3]
        elif line.startswith('LCU::HPCCLCOMPETITIONCLASS:'):
            contest_information['competition_class'] = line.split(':')[3]
        elif line.startswith('LSEEYOU TSK'):
            start_opening, t_min, multi_start = get_task_rules(line)
        elif line.startswith('LCU::HPTZNTIMEZONE:'):
            timezone = int(line.split(':')[3])

    if start_opening is not None:
        # make timezone aware datetime object
        start_opening = datetime.datetime.combine(date=date, time=start_opening, tzinfo=datetime.timezone(datetime.timedelta(hours=timezone)))

    if len(lcu_lines) == 0 or len(lseeyou_lines) == 0:
        # somehow some IGC files do not contain the LCU or LSEEYOU lines with task information
        task = None
    else:
        waypoints = get_waypoints(lcu_lines, lseeyou_lines)

        if t_min is None:
            task = RaceTask(waypoints, timezone, start_opening, start_time_buffer, multi_start)
        else:
            task = AAT(waypoints, t_min, timezone, start_opening, start_time_buffer, multi_start)

    return task, contest_information, competitor_information


def get_waypoints(lcu_lines: List[str], lseeyou_lines: List[str]) -> List[Waypoint]:
    """
    :param lcu_lines: lines in soaringspot igc file starting with 'LCU::C'
    :param lseeyou_lines: lines in soaringspot igc starting with 'LSEEYOU OZ'
    :return: list of Waypoints
    """
    # check on sizes
    if len(lcu_lines) - 3 != len(lseeyou_lines):
        raise ValueError('lcu_lines and lseeyou_lines do not have expected lengths!')

    waypoints = list()
    number_of_waypoints = len(lseeyou_lines)
    for lcu_line, lseeyou_line in zip(lcu_lines[2:-1], lseeyou_lines):
        waypoint = get_waypoint(lcu_line, lseeyou_line, number_of_waypoints)
        waypoints.append(waypoint)

    return waypoints


def get_waypoint(lcu_line: str, lseeyou_line: str, number_of_waypoints: int) -> Waypoint:
    """
    :param number_of_waypoints:
    :param lcu_line: line in soaringspot igc starting with 'LCU::C
    :param lseeyou_line: line in soaringspot igc starting with 'LSEEYOU OZ'
    :return: Waypoint
    """
    name = lcu_line[23::]
    lat, lon = get_lat_long(lcu_line)
    r_min, angle_min, r_max, angle_max = get_sector_dimensions(lseeyou_line)

    sector_orientation = get_sector_orientation(lseeyou_line, number_of_waypoints)
    if sector_orientation == 'fixed':
        orientation_angle = get_fixed_orientation_angle(lseeyou_line)
    else:
        orientation_angle = None

    distance_correction = get_distance_correction(lseeyou_line)

    line = 'Line=1\n' in lseeyou_line.split(',') or 'Line=1' in lseeyou_line.split(',')

    return Waypoint(name, lat, lon, r_min, angle_min, r_max, angle_max, line, sector_orientation, distance_correction,
                    orientation_angle)


def get_lat_long(lcu_line: str) -> Tuple[float, float]:
    """
    :param lcu_line: line in soaringspot igc file starting with 'LCU::C'
    :return: latitude, longitude in degrees
    """

    lat_degrees = float(lcu_line[6:8])
    lat_minutes = float(lcu_line[8:10]) + float(lcu_line[10:13]) / 1000
    lat_cardinal = lcu_line[13]

    long_degrees = float(lcu_line[14:17])
    long_minutes = float(lcu_line[17:19]) + float(lcu_line[19:22]) / 1000
    long_cardinal = lcu_line[22]

    latitude = dm2dd(lat_degrees, lat_minutes, lat_cardinal)
    longitude = dm2dd(long_degrees, long_minutes, long_cardinal)

    return latitude, longitude


def get_fixed_orientation_angle(lseeyou_line: str) -> float:
    components = lseeyou_line.rstrip().split(",")
    for component in components:
        if component.startswith("A12="):
            return float(component.split("=")[1])


def get_sector_orientation(lseeyou_line: str, number_of_waypoints: int) -> str:
    """
    :param lseeyou_line: e.g. 'LSEEYOU OZ=-1,Style=1,R1=500m,A1=180'
    :param number_of_waypoints:
    :return:
    """
    components = lseeyou_line.rstrip().split(",")

    assert components[0].startswith('LSEEYOU OZ')
    waypoint_index = int(components[0].split('=')[1]) + 1

    for component in components:
        if component.startswith("Style="):

            # remove SpeedStyle from component.
            component = re.sub(r'SpeedStyle=[0-9]', '', component)

            if waypoint_index == 0:
                return 'next'
            elif waypoint_index == number_of_waypoints - 1:
                return 'previous'
            else:
                style = int(component.split("=")[1])
                if style == 0:
                    return "fixed"
                elif style == 1:
                    return "symmetrical"
                elif style == 2:
                    return "next"
                elif style == 3:
                    return "previous"
                elif style == 4:
                    return "start"
                else:
                    raise ValueError("Unknown taskpoint style: {}".format(style))


def get_distance_correction(lseeyou_line: str) -> Union[str, None]:
    components = lseeyou_line.rstrip().split(",")
    reduce = False
    move = False
    for component in components:
        if component.startswith("Reduce="):
            reduce = bool(component.split("=")[1])
        elif component.startswith("Move="):
            move = bool(component.split("=")[1])

    if reduce and move:
        return "shorten_legs"
    elif reduce:
        return "shorten_legs"
    elif move:
        return "move_tp"
    else:
        return None


def get_sector_dimensions(lseeyou_line: str) -> Tuple[int, int, int, int]:
    components = lseeyou_line.rstrip().split(",")
    r_min = None
    angle_min = None
    r_max = None
    angle_max = None
    for component in components:
        if component.startswith("R1="):
            r_max = int(component.split("=")[1][:-1])
        elif component.startswith("A1="):
            angle_max = int(component.split("=")[1])
        elif component.startswith("R2="):
            r_min = int(component.split("=")[1][:-1])
        elif component.startswith("A2="):
            angle_min = int(component.split("=")[1])

    return r_min, angle_min, r_max, angle_max


class SoaringSpotDaily(DailyResultsPage):
    """
    Helper class for dealing with daily result pages which are published on the SoaringSpot platform.
    """

    def __init__(self, url: str):
        super().__init__(url)

    def _get_competitors_info(self, include_hc_competitors: bool, include_dns_competitors: bool = False) -> List[dict]:
        """
        Extract competitor information from a SoaringSpot daily results page.

        Args:
            include_hc_competitors: Whether to include pilots competing hors-concours
            include_dns_competitors: Whether to include pilots who did not start or finish

        Returns:
            List of dictionaries with competitor information:
            - ranking: Position in the competition or status (DNF/DNS)
            - competition_id: Glider ID
            - igc_url: URL to download the IGC file (None for DNF/DNS)
            - pilot_name: Name of the pilot
            - plane_model: Type of glider
        """
        competitors_info = []

        table = self._get_html_soup().find("table")
        if not table:
            raise ValueError(f"Could not find results table in the page at {self.url}")

        # Default column indices (fallback values)
        col_indices = {
            'ranking': 0,  # First column typically has the ranking
            'cn': 2,       # Third column typically has competition ID
            'pilot': 3,    # Fourth column typically has pilot name
            'glider': 4    # Fifth column typically has glider model
        }
        
        # Try to determine accurate column indices from headers
        headers = table.find('thead').findAll('th') if table.find('thead') else []
        
        if headers:
            for i, header in enumerate(headers):
                header_text = header.text.strip().lower()
                
                # Check for ranking column (could be # or empty for the first column)
                if header_text == '#' or (i == 0 and header_text == ''):
                    col_indices['ranking'] = i
                
                # Check for CN column (competition number)
                elif header_text == 'cn' or header_text.startswith('comp'):
                    col_indices['cn'] = i
                
                # Check for pilot/contestant column
                elif 'contestant' in header_text or 'pilot' in header_text:
                    col_indices['pilot'] = i
                
                # Check for glider column
                elif 'glider' in header_text or 'plane' in header_text:
                    col_indices['glider'] = i
        
        for row in table.findAll('tr')[1:]:  # Skip header row
            cells = row.findAll('td')
            if not cells or len(cells) <= col_indices['cn']:  # Need at least CN column
                continue

            # Extract status/ranking from ranking column
            ranking_idx = min(col_indices['ranking'], len(cells) - 1)
            status = cells[ranking_idx].text.strip()
            
            # Skip DNF/DNS if not requested
            if (status == "DNF" or status == "DNS") and not include_dns_competitors:
                continue

            # Extract competition ID from CN column
            cn_idx = min(col_indices['cn'], len(cells) - 1)
            cn_cell = cells[cn_idx]
            competition_id = cn_cell.text.strip()
            
            # Extract pilot name from pilot/contestant column
            pilot_idx = min(col_indices['pilot'], len(cells) - 1)
            contestant_cell = cells[pilot_idx]
            pilot_name = contestant_cell.text.strip()
            
            # Try to find a div with flag inside contestant cell and remove it from pilot name
            flag_div = contestant_cell.find('div', class_='flag')
            if flag_div:
                pilot_name = pilot_name.replace(flag_div.text, '').strip()
            
            # Extract plane model from glider column
            plane_model = None
            glider_idx = col_indices['glider']
            if glider_idx < len(cells):
                plane_model = cells[glider_idx].text.strip()

            # Handle HC competitors
            if status == "HC":
                if not include_hc_competitors:
                    continue
                ranking = status
            # Handle DNF/DNS
            elif status == "DNF" or status == "DNS":
                ranking = status
                competitors_info.append({
                    "ranking": ranking,
                    "competition_id": competition_id,
                    "igc_url": None,
                    "pilot_name": pilot_name,
                    "plane_model": plane_model,
                })
                continue
            else:
                # Normal competitors - extract numeric ranking
                try:
                    ranking = int(status.rstrip("."))
                except ValueError:
                    ranking = status

            # Extract IGC URL
            igc_url = None
            for link in cn_cell.findAll('a'):
                data_content = link.get('data-content')
                if data_content:
                    popup_soup = BeautifulSoup(data_content, 'html.parser')
                    for a in popup_soup.findAll('a'):
                        if 'download' in a.text.lower() or '.igc' in a.text.lower():
                            href = a.get('href')
                            if href:
                                if href.startswith("http://") or href.startswith("https://"):
                                    igc_url = href
                                else:
                                    igc_url = urljoin(self.url, href)
                                break

            competitors_info.append({
                "ranking": ranking,
                "competition_id": competition_id,
                "igc_url": igc_url,
                "pilot_name": pilot_name,
                "plane_model": plane_model,
            })

        return competitors_info
   
    def _get_competition_day_info(self) -> Tuple[str, datetime.date, str]:

        if self.url.startswith('https://') or self.url.startswith('http://'):
            _, _, _, _, competition_name, _, plane_class, date_description, *_ = self.url.split('/')
        else:
            _, _, competition_name, _, plane_class, date_description, *_ = self.url.split('/')

        date_us = date_description[-10::]
        date = datetime.date(int(date_us[0:4]), int(date_us[5:7]), int(date_us[-2::]))

        return competition_name, date, plane_class

    def generate_competition_day(self, target_directory: str, download_progress=None, start_time_buffer: int=0,
                                 include_hc_competitors: bool = True) -> CompetitionDay:

        # get info from website
        competition_name, date, plane_class = self._get_competition_day_info()
        competitors_info = self._get_competitors_info(include_hc_competitors)

        self.set_igc_directory(target_directory, competition_name, plane_class, date)

        competitors = list()
        tasks = list()
        files_downloaded = 0
        unknown_number = 1  # number for empty competition IDs
        for competitor_info in competitors_info:
            competition_id = competitor_info['competition_id']
            if competition_id == '':
                # come up with comp ID when empty. entries on soaring can have empty comp ID but valid download link
                competition_id = f'unknown{unknown_number}'
                unknown_number += 1

            igc_url = competitor_info['igc_url']
            ranking = competitor_info['ranking']

            # download files. skip if not valid
            try:
                file_path = self.download_flight(igc_url, competition_id)
            except URLError as e:
                print('{} is skipped because of invalid URL'.format(competition_id))
                continue

            files_downloaded += 1
            if download_progress is not None:
                download_progress(files_downloaded, len(competitors_info))

            try:
                try:  # try utf-8
                    with open(file_path, 'r', encoding='utf-8') as f:
                        parsed_igc_file = Reader(skip_duplicates=True).read(f)
                except UnicodeDecodeError:  # if not utf-8 use latin1
                    with open(file_path, 'r', encoding='latin1') as f:
                        parsed_igc_file = Reader(skip_duplicates=True).read(f)
            except Exception:
                print('{} is skipped because the file could not be parsed'.format(competition_id))
                continue

            trace_errors, trace = parsed_igc_file['fix_records']
            if len(trace_errors) != 0:
                print('{} is skipped because of invalid trace'.format(competition_id))
                continue

            # get info from file
            task, _, competitor_information = get_info_from_comment_lines(parsed_igc_file, date, start_time_buffer)
            plane_model = competitor_information.get('plane_model', None)
            pilot_name = competitor_information.get('pilot_name', None)

            competitor = Competitor(trace, competition_id, plane_model, ranking, pilot_name)

            competitors.append(competitor)
            if task is not None:
                tasks.append(task)

        # Select task from tasks list
        task = self._select_task(tasks)

        return CompetitionDay(competition_name, date, plane_class, competitors, task)
