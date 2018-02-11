import datetime
from typing import List

from OpenSoar.competition.competition_day import CompetitionDay
from OpenSoar.competition.competitor import Competitor
from OpenSoar.competition.daily_results_page import DailyResultsPage
from OpenSoar.task.waypoint import Waypoint
from OpenSoar.utilities.helper_functions import dm2dd


def get_task_info(lscsd_lines, lscsr_lines):
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
        'aat': False
    }

    for line in [*lscsd_lines, *lscsr_lines]:
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
            if int(((line.split(':'))[3])[0:-1]) == 0:
                task_info['tp_aat_angle'].append(360)
            else:
                task_info['tp_aat_angle'].append(int(((line.split(':'))[3])[0:-1]))
            task_info['aat'] = True

    return task_info


def get_waypoint_name_lat_long(lscs_line_tp):
    """Parse LSCSCT line (LSCSCT:074 Main Lohr-M:N4959700:E00934900)"""
    _, name, lat, lon = lscs_line_tp.split(':')

    lat_cardinal, lat_degrees, lat_minutes = lat[0], float(lat[1:3]), float(lat[3:5]) + float(lat[5:8]) / 1000
    lon_cardinal, lon_degrees, lon_minutes = lon[0], float(lon[1:4]), float(lon[4:6]) + float(lon[6:9]) / 1000

    lat = dm2dd(lat_degrees, lat_minutes, lat_cardinal)
    lon = dm2dd(lon_degrees, lon_minutes, lon_cardinal)

    return name, lat, lon


def get_waypoint(lscs_line_tp, task_info, n, n_tp):

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


def get_waypoints(lscsc_lines, lscsd_lines, lscsr_lines):
    task_info = get_task_info(lscsd_lines, lscsr_lines)

    waypoints = list()
    for n, lscsc_line in enumerate(lscsc_lines):
        waypoint = get_waypoint(lscsc_line, task_info, n, len(lscsc_lines))
        waypoints.append(waypoint)

    return waypoints


def get_waypoints_from_parsed_file(parsed_igc_file):
    lscsd_lines = list()
    lscsr_lines = list()
    lscsc_lines = list()

    for comment_record in parsed_igc_file['comment_records'][1]:
        line = 'L{}{}'.format(comment_record['source'], comment_record['comment'])

        if line.startswith('LSCSD'):
            lscsd_lines.append(line)
        elif line.startswith('LSCSC'):
            lscsc_lines.append(line)
        elif line.startswith('LSCSR'):
            lscsr_lines.append(line)

    return get_waypoints(lscsc_lines, lscsd_lines, lscsr_lines)


class StreplaDaily(DailyResultsPage):

    def __init__(self, url, target_directory):
        super().__init__(url, target_directory)

    def get_competition_day(self) -> CompetitionDay:
        soup = self._get_html_soup()

        competition_name = soup.find('div', id="public_contest_info").find('span', id="ctl00_lblCompName").text
        plane_class = soup.find('div', {"class": "h3a"}).find('span', id="ctl00_Content_lblCompClass").text

        # remove spaces in names
        competition_name = competition_name.replace(' ', '_')
        plane_class = plane_class.replace(' ', '_')

        raw_date = soup.find('div', {"class": "h3a"}).find('span', id="ctl00_Content_lblDate").text[0:10]
        dd, mm, yyyy = str(raw_date).split('.')
        date = datetime.date(int(yyyy), int(mm), int(dd))

        return CompetitionDay(competition_name, date, plane_class, self.get_competitors())

    def get_competitors(self) -> List[Competitor]:
        soup = self._get_html_soup()

        competitors = list()

        table = soup.find("table")
        num_comp = len(table.findAll('tr'))
        for i in range(num_comp - 1):
            comp = table.findAll('tr')[i + 1]
            if comp.findAll('span')[0].text != 'dnf':

                ranking = int(comp.findAll('span')[0].text)
                relative_file_url = comp.findAll('a')[0].get('href')
                competition_id = comp.findAll('span')[1].text
                plane = comp.findAll('span')[3].text

                igc_url = f"http://www.strepla.de/scs/Public/{relative_file_url}"

                competitor = Competitor(trace=list(), competition_id=competition_id, airplane=plane, ranking=ranking,
                                        igc_url=igc_url)
                competitors.append(competitor)

        return competitors
