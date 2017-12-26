import datetime
from aerofiles.igc import Reader

from OpenSoar.competition.soaringspot import get_waypoints
from OpenSoar.task.aat import AAT
from OpenSoar.task.race_task import RaceTask


def get_trace(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader().read(f)

    _, trace = parsed_igc_file['fix_records']

    return trace


def waypoints_from_parsed_file(parsed_igc_file):
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


def get_race_task(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader().read(f)

    waypoints = waypoints_from_parsed_file(parsed_igc_file)
    return RaceTask(waypoints)


def get_aat(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader().read(f)

    waypoints = waypoints_from_parsed_file(parsed_igc_file)
    return AAT(waypoints, datetime.time(hour=3, minute=30))
