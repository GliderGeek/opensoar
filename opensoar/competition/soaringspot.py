"""
File with helper functions for soaringspot competitions:
- reading waypoints from soaringspot igc
"""
import datetime

from aerofiles.igc import Reader

from opensoar.competition.competition_day import CompetitionDay
from opensoar.competition.competitor import Competitor
from opensoar.task.aat import AAT
from opensoar.task.race_task import RaceTask
from opensoar.task.waypoint import Waypoint
from opensoar.utilities.helper_functions import dm2dd
from opensoar.competition.daily_results_page import DailyResultsPage


def get_comment_lines_from_parsed_file(parsed_igc_file):
    """In the parsed file, lines are split into source and comment. This function stiches them back together"""
    records = parsed_igc_file['comment_records'][1]
    return [f"L{record['source']}{record['comment']}" for record in records]


def get_task_rules(lseeyou_tsk_line):
    start_opening = None
    t_min = None
    multi_start = False
    for element in lseeyou_tsk_line.split(','):
        if element.startswith('TaskTime'):
            time = element.split('=')[1]
            hours, minutes, seconds = [int(part) for part in time.split(':')]
            t_min = datetime.time(hours, minutes, seconds)
        elif element.startswith('NoStart'):
            time = element.split('=')[1]
            hours, minutes, seconds = [int(part) for part in time.split(':')]
            start_opening = datetime.time(hours, minutes, seconds)
        elif element.startswith('MultiStart:'):
            multi_start = element.split(':')[1] == 'True'

    return start_opening, t_min, multi_start


def get_info_from_comment_lines(parsed_igc_file, start_time_buffer=0):
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

    waypoints = get_waypoints(lcu_lines, lseeyou_lines)

    if t_min is None:
        task = RaceTask(waypoints, timezone, start_opening, start_time_buffer, multi_start)
    else:
        task = AAT(waypoints, t_min, timezone, start_opening, start_time_buffer, multi_start)

    return task, contest_information, competitor_information


def get_waypoints(lcu_lines, lseeyou_lines):
    """
    :param lcu_lines: lines in soaringspot igc file starting with 'LCU::C'
    :param lseeyou_lines: lines in soaringspot igc starting with 'LSEEYOU OZ'
    :return: list of Waypoints
    """
    # check on sizes
    if len(lcu_lines) - 3 != len(lseeyou_lines):
        raise ValueError('lcu_lines and lseeyou_lines do not have expected lengths!')

    waypoints = []
    for lcu_lines, lseeyou_line in zip(lcu_lines[2:-1], lseeyou_lines):
        waypoint = get_waypoint(lcu_lines, lseeyou_line)
        waypoints.append(waypoint)

    return waypoints


def get_waypoint(lcu_line, lseeyou_line):
    """
    :param lcu_line: line in soaringspot igc starting with 'LCU::C
    :param lseeyou_line: line in soaringspot igc starting with 'LSEEYOU OZ'
    :return: Waypoint
    """
    name = lcu_line[23::]
    lat, lon = get_lat_long(lcu_line)
    r_min, angle_min, r_max, angle_max = get_sector_dimensions(lseeyou_line)

    sector_orientation = get_sector_orientation(lseeyou_line)
    if sector_orientation == 'fixed':
        orientation_angle = get_fixed_orientation_angle(lseeyou_line)
    else:
        orientation_angle = None

    distance_correction = get_distance_correction(lseeyou_line)

    line = 'Line=1\n' in lseeyou_line.split(',') or 'Line=1' in lseeyou_line.split(',')

    return Waypoint(name, lat, lon, r_min, angle_min, r_max, angle_max, line, sector_orientation, distance_correction,
                    orientation_angle)


def get_lat_long(lcu_line):
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


def get_fixed_orientation_angle(lseeyou_line):
    components = lseeyou_line.rstrip().split(",")
    for component in components:
        if component.startswith("A12="):
            return float(component.split("=")[1])


def get_sector_orientation(lseeyou_line):
    components = lseeyou_line.rstrip().split(",")
    for component in components:
        if component.startswith("Style="):
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


def get_distance_correction(lseeyou_line):
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


def get_sector_dimensions(lseeyou_line):
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

    def __init__(self, url):
        super().__init__(url)

    def _get_competitors_info(self):
        base_url = "https://www.soaringspot.com"
        competitors_info = list()

        table = self._get_html_soup().find("table")
        for row in table.findAll('tr')[1:]:
            if row.findAll('td')[0].text not in ["DNS", "DNF", "HC"]:

                ranking = int(row.findAll('td')[0].text[0:-1])

                igc_url = None
                competition_id = None
                for link in row.findAll('a'):
                    if link.get('href').startswith("http://") or link.get('href').startswith("https://"):
                        igc_url = link.get('href')
                    elif link.get('href').split('/')[2] == "download-contest-flight":
                        igc_url = base_url + link.get('href')

                    competition_id = link.text

                competitors_info.append(dict(ranking=ranking, competition_id=competition_id, igc_url=igc_url))

        return competitors_info

    def _get_competition_day_info(self):
        if self.url.startswith('https://') or self.url.startswith('http://'):
            _, _, _, _, competition_name, _, plane_class, date_description, _ = self.url.split('/')
        else:
            _, _, competition_name, _, plane_class, date_description, _ = self.url.split('/')

        date_us = date_description[-10::]
        date = datetime.date(int(date_us[0:4]), int(date_us[5:7]), int(date_us[-2::]))

        return competition_name, date, plane_class

    def generate_competition_day(self, target_directory, download_progress=None, start_time_buffer=0) -> CompetitionDay:

        # get info from website
        competition_name, date, plane_class = self._get_competition_day_info()
        competitors_info = self._get_competitors_info()

        self.set_igc_directory(target_directory, competition_name, plane_class, date)

        competitors = list()
        tasks = list()
        files_downloaded = 0
        for competitor_info in competitors_info:
            competition_id = competitor_info['competition_id']
            igc_url = competitor_info['igc_url']
            ranking = competitor_info['ranking']

            # download files
            file_path = self.download_flight(igc_url, competition_id)

            files_downloaded += 1
            if download_progress is not None:
                download_progress(files_downloaded, len(competitors_info))

            with open(file_path, 'r') as f:
                parsed_igc_file = Reader().read(f)

            trace_errors, trace = parsed_igc_file['fix_records']

            # get info from file
            task, contest_information, competitor_information = get_info_from_comment_lines(parsed_igc_file, start_time_buffer)
            plane_model = competitor_information.get('plane_model', None)
            pilot_name = competitor_information.get('pilot_name', None)

            competitor = Competitor(trace, competition_id, plane_model, ranking, pilot_name)

            competitors.append(competitor)
            tasks.append(task)

        # Select task from tasks list
        task = self._select_task(tasks)

        return CompetitionDay(competition_name, date, plane_class, competitors, task)
