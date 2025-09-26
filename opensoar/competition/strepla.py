"""
Helper functions for Strepla competitions.
The files from Strepla always contain task information, which can be used for competition analysis.
"""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Optional, Union
from urllib.error import URLError

from aerofiles.igc import Reader

from opensoar.competition.competition_day import CompetitionDay
from opensoar.competition.competitor import Competitor
from opensoar.competition.daily_results_page import DailyResultsPage
from opensoar.task.aat import AAT
from opensoar.task.race_task import RaceTask
from opensoar.task.waypoint import Waypoint
from opensoar.utilities.helper_functions import dm2dd

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    tp: list = field(default_factory=list)
    s_line_rad: Optional[int] = None
    tp_key: bool = False
    tp_key_dim: Optional[list[int]] = None
    tp_cyl: bool = False
    tp_cyl_rad: Optional[int] = None
    f_line: bool = False
    f_line_rad: Optional[int] = None
    f_cyl: bool = False
    f_cyl_rad: Optional[int] = None
    tp_aat_rad: list[int] = field(default_factory=list)
    tp_aat_angle: list[int] = field(default_factory=list)
    aat: bool = False
    time_window: Optional[datetime.timedelta] = None
    gate_open: Optional[datetime.time] = None


@dataclass
class CompetitorInformation:
    pilot_name: Optional[str] = None
    competition_id: Optional[str] = None


def get_task_and_competitor_info(
    lscsd_lines: list[str], lscsr_lines: list[str], lscsa_lines: list[str]
) -> tuple[TaskInfo, CompetitorInformation]:

    task_info = TaskInfo()
    competitor_info = CompetitorInformation()

    for line in [*lscsd_lines, *lscsr_lines, *lscsa_lines]:
        try:
            if line.startswith("LSCSRSLINE"):
                parts = line.split(":")
                if len(parts) > 1:
                    task_info.s_line_rad = int(parts[1]) / 2
                    logger.info(f"Start line radius set to {task_info.s_line_rad}")
            elif line.startswith("LSCSRFLINE"):
                parts = line.split(":")
                if len(parts) > 1:
                    task_info.f_line = True
                    task_info.f_line_rad = int(parts[1])
                    logger.info(f"Finish line radius set to {task_info.f_line_rad}")
            elif line.startswith("LSCSRTKEYHOLE"):
                parts = line.split(":")
                if len(parts) >= 4:
                    task_info.tp_key = True
                    task_info.tp_key_dim = [int(p) for p in parts[1:4]]
                    logger.info(
                        f"Keyhole sector dimensions set to {task_info.tp_key_dim}"
                    )
            elif line.startswith("LSCSRTCYLINDER"):
                parts = line.split(":")
                if len(parts) > 1:
                    task_info.tp_cyl = True
                    task_info.tp_cyl_rad = int(parts[1])
                    logger.info(
                        f"Turnpoint cylinder radius set to {task_info.tp_cyl_rad}"
                    )
            elif line.startswith("LSCSRFCYLINDER"):
                parts = line.split(":")
                if len(parts) > 1:
                    task_info.f_cyl = True
                    task_info.f_cyl_rad = int(parts[1])
                    logger.info(f"Finish cylinder radius set to {task_info.f_cyl_rad}")
            elif line.startswith("LSCSA0"):
                parts = line.split(":")
                if len(parts) >= 4:
                    task_info.tp_aat_rad.append(int(parts[1]))
                    angle = int(parts[3])
                    task_info.tp_aat_angle.append(360 if angle == 0 else angle)
                    task_info.aat = True
                    logger.info(
                        f"AAT sector radius {task_info.tp_aat_rad[-1]}, angle {task_info.tp_aat_angle[-1]}"
                    )
            elif line.startswith("LSCSDTime window"):
                parts = line.split(":")
                if len(parts) >= 3:
                    task_info.time_window = datetime.timedelta(
                        hours=int(parts[1]), minutes=int(parts[2])
                    )
                    logger.info(f"Time window set to {task_info.time_window}")
            elif line.startswith("LSCSDGate open"):
                parts = line.split(":")
                if len(parts) >= 3:
                    task_info.gate_open = datetime.time(int(parts[1]), int(parts[2]))
                    logger.info(f"Gate open time set to {task_info.gate_open}")
            elif line.startswith("LSCSDName"):
                parts = line.split(":")
                if len(parts) > 1:
                    competitor_info.pilot_name = parts[1]
                    logger.info(f"Pilot name set to {competitor_info.pilot_name}")
            elif line.startswith("LSCSDCID"):
                parts = line.split(":")
                if len(parts) > 1:
                    competitor_info.competition_id = parts[1]
                    logger.info(
                        f"Competition ID set to {competitor_info.competition_id}"
                    )
        except (ValueError, IndexError) as e:
            logger.warning(f"Skipping malformed line: {line} — Error: {e}")
            continue

    return task_info, competitor_info


def get_waypoint_name_lat_long(lscs_line_tp: str) -> tuple[str, float, float]:
    """Parse LSCSCT line (LSCSCT:074 Main Lohr-M:N4959700:E00934900)"""
    _, name, lat, lon = lscs_line_tp.split(":")

    lat_cardinal, lat_degrees, lat_minutes = (
        lat[0],
        float(lat[1:3]),
        float(lat[3:5]) + float(lat[5:8]) / 1000,
    )
    lon_cardinal, lon_degrees, lon_minutes = (
        lon[0],
        float(lon[1:4]),
        float(lon[4:6]) + float(lon[6:9]) / 1000,
    )

    lat = dm2dd(lat_degrees, lat_minutes, lat_cardinal)
    lon = dm2dd(lon_degrees, lon_minutes, lon_cardinal)

    return name, lat, lon


def get_waypoint(lscs_line_tp: str, task_info: TaskInfo, n: int, n_tp: int) -> Waypoint:
    name, lat, lon = get_waypoint_name_lat_long(lscs_line_tp)
    logger.debug(f"Waypoint {n+1}: {name} at ({lat}, {lon})")

    r_min = r_max = angle_min = angle_max = orientation_angle = None
    line = False
    sector_orientation = distance_correction = None

    if n == 0:
        line = True
        sector_orientation = "next"
        r_max = task_info.s_line_rad
        angle_max = 90
    elif 0 < n < (n_tp - 1):
        sector_orientation = "symmetrical"

        if task_info.aat:
            # AAT tasks use variable sectors; set radius and angle from LSCSA lines
            angle_max = task_info.tp_aat_angle[n - 1] / 2
            r_max = task_info.tp_aat_rad[n - 1]
            sector_orientation = "previous"
        elif task_info.tp_key:
            # Keyhole sector: use dimensions from LSCSRTKEYHOLE line
            r_max = task_info.tp_key_dim[1]
            angle_max = task_info.tp_key_dim[2] / 2
            r_min = task_info.tp_key_dim[0]
            angle_min = 180
        elif task_info.tp_cyl:
            r_max = task_info.tp_cyl_rad
            angle_max = 180
    elif n == n_tp - 1:
        sector_orientation = "previous"
        if task_info.f_cyl:
            r_max = task_info.f_cyl_rad
            distance_correction = "shorten_legs"
            angle_max = 180
        elif task_info.f_line:
            r_max = task_info.f_line_rad
            angle_max = 90
            line = True

    logger.info(
        f"Waypoint {name} sector type: {'AAT' if task_info.aat else 'Keyhole' if task_info.tp_key else 'Cylinder' if task_info.tp_cyl else 'Line' if line else 'Unknown'}"
    )

    return Waypoint(
        name,
        lat,
        lon,
        r_min,
        angle_min,
        r_max,
        angle_max,
        line,
        sector_orientation,
        distance_correction,
        orientation_angle,
    )


def get_waypoints(lscsc_lines: list[str], task_info: TaskInfo) -> list[Waypoint]:
    return [
        get_waypoint(line, task_info, n, len(lscsc_lines))
        for n, line in enumerate(lscsc_lines)
    ]


def get_info_from_comment_lines(
    parsed_igc_file: dict, start_time_buffer: int = 0
) -> tuple[Union[RaceTask, AAT], TaskInfo, CompetitorInformation]:

    lscsd_lines = []
    lscsr_lines = []
    lscsc_lines = []
    lscsa_lines = []

    for comment_record in parsed_igc_file["comment_records"][1]:
        line = f"L{comment_record['source']}{comment_record['comment']}"

        if line.startswith("LSCSD"):
            lscsd_lines.append(line)
        elif line.startswith("LSCSC"):
            lscsc_lines.append(line)
        elif line.startswith("LSCSR"):
            lscsr_lines.append(line)
        elif line.startswith("LSCSA"):
            lscsa_lines.append(line)

    logger.debug(
        f"Collected {len(lscsd_lines)} LSCSD lines, {len(lscsr_lines)} LSCSR lines, {len(lscsc_lines)} LSCSC lines, {len(lscsa_lines)} LSCSA lines"
    )

    task_info, competitor_info = get_task_and_competitor_info(
        lscsd_lines, lscsr_lines, lscsa_lines
    )
    waypoints = get_waypoints(lscsc_lines, task_info)

    # Strepla IGC files do not include timezone info; may need external source
    timezone = None

    task = (
        AAT(
            waypoints,
            task_info.time_window,
            timezone,
            task_info.gate_open,
            start_time_buffer,
        )
        if task_info.aat
        else RaceTask(waypoints, timezone, task_info.gate_open, start_time_buffer)
    )
    logger.info(
        f"Created {'AAT' if task_info.aat else 'RaceTask'} with {len(waypoints)} waypoints"
    )
    logger.info(
        f"Parsed task for pilot {competitor_info.pilot_name} (ID: {competitor_info.competition_id})"
    )
    return task, task_info, competitor_info
