"""
Helper functions for Strepla competitions.
The files from Strepla always contain task information, which can be used for competition analysis.
"""
import datetime
from typing import List, Tuple
from urllib.error import URLError

from aerofiles.igc import Reader

from opensoar.competition.competition_day import CompetitionDay
from opensoar.competition.competitor import Competitor
from opensoar.competition.daily_results_page import DailyResultsPage
from opensoar.task.aat import AAT
from opensoar.task.race_task import RaceTask
from opensoar.task.waypoint import Waypoint
from opensoar.utilities.helper_functions import dm2dd


def get_task_and_competitor_info(lscsd_lines: List[str], lscsr_lines: List[str], lscsa_lines: List[str]) -> Tuple[dict, dict]:
    task_info = {
        'tp': [],
        's_line_rad': None,
        'tp_key': False,
        'tp_key_dim': None,
        'tp_cyl': False,
        'tp_cyl_rad': None,
        'f_line': False,
        'f_line_rad': None,
        'f_cyl': False,
        'f_cyl_rad': None,
        'tp_aat_rad': [],
        'tp_aat_angle': [],
        'aat': False,
        'time_window': None,
        'gate_open': None,
    }

    competitor_information = {
        'pilot_name': None,
        'competition_id': None,
    }

    for line in [*lscsd_lines, *lscsr_lines, *lscsa_lines]:
        if line.startswith('LSCSRSLINE'):
            task_info['s_line_rad'] = int((line.split(':'))[1]) / 2
        elif line.startswith('LSCSRFLINE'):
            task_info['f_line'] = True
            task_info['f_line_rad'] = int((line.split(':'))[1])
        elif line.startswith('LSCSRTKEYHOLE'):
            task_info['tp_key'] = True
            task_info['tp_key_dim'] = [int(part) for part in line.split(':')[1::]]
        elif line.startswith('LSCSRTCYLINDER'):
            task_info['tp_cyl'] = True
            task_info['tp_cyl_rad'] = int((line.split(':'))[1])
        elif line.startswith('LSCSRFCYLINDER'):
            task_info['f_cyl'] = True
            task_info['f_cyl_rad'] = int((line.split(':'))[1])
        elif line.startswith('LSCSA0'):
            task_info['tp_aat_rad'].append(int((line.split(':'))[1]))
            if int(line.split(':')[3]) == 0:
                task_info['tp_aat_angle'].append(360)
            else:
                task_info['tp_aat_angle'].append(int(line.split(':')[3]))
            task_info['aat'] = True
        elif line.startswith('LSCSDTime window'):
            _, hours, minutes = line.split(':')
            task_info['time_window'] = datetime.timedelta(hours=int(hours), minutes=int(minutes))
        elif line.startswith('LSCSDGate open'):
            _, hours, minutes = line.split(':')
            task_info['gate_open'] = datetime.time(int(hours), int(minutes))
        elif line.startswith('LSCSDName'):
            competitor_information['pilot_name'] = line.split(':')[1]
        elif line.startswith('LSCSDCID'):
            competitor_information['competition_id'] = line.split(':')[1]

    return task_info, competitor_information


def get_waypoint_name_lat_long(lscs_line_tp: str) -> Tuple[str, float, float]:
    """Parse LSCSCT line (LSCSCT:074 Main Lohr-M:N4959700:E00934900)"""
    _, name, lat, lon = lscs_line_tp.split(':')

    lat_cardinal, lat_degrees, lat_minutes = lat[0], float(lat[1:3]), float(lat[3:5]) + float(lat[5:8]) / 1000
    lon_cardinal, lon_degrees, lon_minutes = lon[0], float(lon[1:4]), float(lon[4:6]) + float(lon[6:9]) / 1000

    lat = dm2dd(lat_degrees, lat_minutes, lat_cardinal)
    lon = dm2dd(lon_degrees, lon_minutes, lon_cardinal)

    return name, lat, lon


def get_waypoint(lscs_line_tp: str, task_info: dict, n: int, n_tp: int) -> Waypoint:

    name, lat, lon = get_waypoint_name_lat_long(lscs_line_tp)

    r_min = None
    r_max = None
    angle_min = None
    angle_max = None
    orientation_angle = None
    line = False
    sector_orientation = None
    distance_correction = None

    if n == 0:
        line = True
        sector_orientation = "next"
        r_max = task_info['s_line_rad']
        angle_max = 90
    elif 0 < n < (n_tp - 1):
        sector_orientation = "symmetrical"

        if task_info['aat']:
            angle_max = (task_info['tp_aat_angle'])[n - 1] / 2
            r_max = (task_info['tp_aat_rad'])[n - 1]
            sector_orientation = "previous"
        else:
            # turnpoint is DAEC keyhole
            if task_info['tp_key']:
                r_max = (task_info['tp_key_dim'])[1]
                angle_max = ((task_info['tp_key_dim'])[2]) / 2
                r_min = (task_info['tp_key_dim'])[0]
                angle_min = 180

            # turnpoint is cylinder
            elif task_info['tp_cyl']:
                r_max = task_info['tp_cyl_rad']
                angle_max = 180

    elif n == n_tp - 1:
        sector_orientation = "previous"

        # finish is cylinder
        if task_info['f_cyl']:
            r_max = task_info['f_cyl_rad']
            distance_correction = "shorten_legs"
            angle_max = 180

        # finish is line
        elif task_info['f_line']:
            r_max = task_info['f_line_rad']
            angle_max = 90
            line = True

    return Waypoint(name, lat, lon, r_min, angle_min, r_max, angle_max, line, sector_orientation, distance_correction,
                    orientation_angle)


def get_waypoints(lscsc_lines: List[str], task_info: dict) -> List[Waypoint]:
    waypoints = list()
    for n, lscsc_line in enumerate(lscsc_lines):
        waypoint = get_waypoint(lscsc_line, task_info, n, len(lscsc_lines))
        waypoints.append(waypoint)

    return waypoints


def get_info_from_comment_lines(parsed_igc_file: dict, start_time_buffer: int=0):

    lscsd_lines = list()
    lscsr_lines = list()
    lscsc_lines = list()
    lscsa_lines = list()

    for comment_record in parsed_igc_file['comment_records'][1]:
        line = 'L{}{}'.format(comment_record['source'], comment_record['comment'])

        if line.startswith('LSCSD'):
            lscsd_lines.append(line)
        elif line.startswith('LSCSC'):
            lscsc_lines.append(line)
        elif line.startswith('LSCSR'):
            lscsr_lines.append(line)
        elif line.startswith('LSCSA'):
            lscsa_lines.append(line)

    task_information, competitor_information = get_task_and_competitor_info(lscsd_lines, lscsr_lines, lscsa_lines)
    waypoints = get_waypoints(lscsc_lines, task_information)

    aat = task_information['aat']
    t_min = task_information.get('time_window', None)
    start_opening = task_information.get('gate_open', None)
    timezone = None  # unclear where to get timezone information from strepla igc file

    if aat:
        task = AAT(waypoints, t_min, timezone, start_opening, start_time_buffer)
    else:
        task = RaceTask(waypoints, timezone, start_opening, start_time_buffer)

    return task, task_information, competitor_information


class StreplaDaily(DailyResultsPage):
    """
    Helper class for dealing with daily result pages which are published on the Strepla platform.
    """

    def __init__(self, url: str):
        super().__init__(url)

    def _get_competition_day_info(self) -> Tuple[str, datetime.date, str]:
        soup = self._get_html_soup()

        competition_name = soup.find('div', id="public_contest_info").find('span', id="ctl00_lblCompName").text
        plane_class = soup.find('div', {"class": "h3a"}).find('span', id="ctl00_Content_lblCompClass").text

        # remove spaces in names
        competition_name = competition_name.replace(' ', '_')
        plane_class = plane_class.replace(' ', '_')

        raw_date = soup.find('div', {"class": "h3a"}).find('span', id="ctl00_Content_lblDate").text[0:10]
        dd, mm, yyyy = str(raw_date).split('.')
        date = datetime.date(int(yyyy), int(mm), int(dd))

        return competition_name, date, plane_class

    def _get_table_info(self, include_hc_competitors: bool) -> List[dict]:
        """
        :param include_hc_competitors: include pilots which do not officially compete
        :return:
        """
        soup = self._get_html_soup()

        competitors_info = list()

        table = soup.find("table")
        num_comp = len(table.findAll('tr'))

        uses_https = self.url.startswith('https://')

        for i in range(num_comp - 1):
            comp = table.findAll('tr')[i + 1]
            if comp.findAll('span')[0].text != 'dnf':

                ranking = comp.findAll('span')[0].text

                if ranking == 'hc':
                    if not include_hc_competitors:
                        continue
                else:
                    ranking = int(ranking)

                relative_file_url = comp.findAll('a')[0].get('href')
                competition_id = comp.findAll('span')[1].text
                plane_model = comp.findAll('span')[3].text

                if uses_https:
                    igc_url = "https://www.strepla.de/scs/Public/{}".format(relative_file_url)
                else:
                    igc_url = "http://www.strepla.de/scs/Public/{}".format(relative_file_url)

                competitors_info.append(dict(plane_model=plane_model, ranking=ranking, competition_id=competition_id,
                                             igc_url=igc_url))

        return competitors_info

    def generate_competition_day(self, target_directory: str, download_progress=None, start_time_buffer: int=0,
                                 include_hc_competitors: bool = True) -> CompetitionDay:

        # get info from website
        competition_name, date, plane_class = self._get_competition_day_info()
        table_info = self._get_table_info(include_hc_competitors)

        self.set_igc_directory(target_directory, competition_name, plane_class, date)

        competitors = list()
        tasks = list()
        files_downloaded = 0
        for table_entry in table_info:
            competition_id = table_entry['competition_id']
            igc_url = table_entry['igc_url']
            plane_model = table_entry['ranking']
            ranking = table_entry['plane_model']

            # download files. skip if not valid
            try:
                file_path = self.download_flight(igc_url, competition_id)
            except URLError:
                print('{} is skipped because of invalid URL'.format(competition_id))
                continue

            files_downloaded += 1
            if download_progress is not None:
                download_progress(files_downloaded, len(table_info))

            try:
                try:  # try utf-8
                    with open(file_path, 'r', encoding='utf-8') as f:
                        parsed_igc_file = Reader().read(f)
                except UnicodeDecodeError:  # if not utf-8 use latin1
                    with open(file_path, 'r', encoding='latin1') as f:
                        parsed_igc_file = Reader().read(f)
            except Exception:
                print('{} is skipped because the file could not be parsed'.format(competition_id))
                continue

            trace_errors, trace = parsed_igc_file['fix_records']
            if len(trace_errors) != 0:
                print('{} is skipped because of invalid trace'.format(competition_id))
                continue

            # get info from file
            task, task_info, competitor_information = get_info_from_comment_lines(parsed_igc_file, start_time_buffer)
            pilot_name = competitor_information.get('pilot_name', None)

            competitor = Competitor(trace, competition_id, plane_model, ranking, pilot_name)

            competitors.append(competitor)
            tasks.append(task)

        # Select task from tasks list
        task = self._select_task(tasks)

        return CompetitionDay(competition_name, date, plane_class, competitors, task)
