"""
File with helper functions for soaringspot competitions:
- reading waypoints from soaringspot igc
"""
from typing import List

import datetime

from OpenSoar.competition.competition_day import CompetitionDay
from OpenSoar.competition.competitor import Competitor
from OpenSoar.task.waypoint import Waypoint
from OpenSoar.utilities.helper_functions import dms2dd
from OpenSoar.competition.daily_results_page import DailyResultsPage


def get_waypoints_from_parsed_file(parsed_igc_file):
    lcu_lines = list()
    lseeyou_lines = list()
    for comment_record in parsed_igc_file['comment_records'][1]:
        line = 'L{}{}'.format(comment_record['source'], comment_record['comment'])
        if line.startswith('LCU::C'):
            lcu_lines.append(line)
        elif line.startswith('LSEEYOU OZ'):
            lseeyou_lines.append(line)

    waypoints = get_waypoints(lcu_lines, lseeyou_lines)
    return waypoints


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

    latitude_degrees = float(lcu_line[6:8])
    latitude_minutes = float(lcu_line[8:10])
    latitude_seconds = float(lcu_line[10:13])
    latitude_cardinal = lcu_line[13]

    longitude_degrees = float(lcu_line[14:17])
    longitude_minutes = float(lcu_line[17:19])
    longitude_seconds = float(lcu_line[19:22])
    longitude_cardinal = lcu_line[22]

    latitude = dms2dd(latitude_degrees, latitude_minutes, latitude_seconds, latitude_cardinal)
    longitude = dms2dd(longitude_degrees, longitude_minutes, longitude_seconds, longitude_cardinal)

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

    def __init__(self, url, target_directory):
        DailyResultsPage.__init__(self, url, target_directory)

    def get_competitors(self) -> List[Competitor]:
        base_url = "https://www.soaringspot.com"
        competitors = list()

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

                competitor = Competitor(trace=list(), ranking=ranking, competition_id=competition_id, igc_url=igc_url)
                competitors.append(competitor)

        return competitors

    def get_competition_day(self) -> CompetitionDay:
        if self.url.startswith('https://') or self.url.startswith('http://'):
            _, _, _, _, name, _, plane_class, date_description, _ = self.url.split('/')
        else:
            _, _, name, _, plane_class, date_description, _ = self.url.split('/')

        date_us = date_description[-10::]

        print(date_us)

        date = datetime.date(int(date_us[0:4]), int(date_us[5:7]), int(date_us[-2::]))

        return CompetitionDay(name, date, plane_class, competitors=list())
