import datetime
from aerofiles.igc import Reader

from opensoar.competition.soaringspot import get_waypoints_from_parsed_file
from opensoar.task.aat import AAT
from opensoar.task.race_task import RaceTask


def get_trace(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader().read(f)

    _, trace = parsed_igc_file['fix_records']

    return trace


def get_race_task(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader().read(f)

    waypoints = get_waypoints_from_parsed_file(parsed_igc_file)
    return RaceTask(waypoints)


def get_aat(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader().read(f)

    waypoints = get_waypoints_from_parsed_file(parsed_igc_file)
    return AAT(waypoints, datetime.time(hour=3, minute=30))
