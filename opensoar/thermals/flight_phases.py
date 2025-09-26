from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

from opensoar.task.trip import Trip
from opensoar.thermals.pysoar_thermal_detector import PySoarThermalDetector
from opensoar.utilities.helper_functions import (
    calculate_distance_bearing,
    total_distance_travelled,
)


@dataclass
class Phase:
    is_cruise: bool
    fixes: list[dict[str, Any]]
    duration: Optional[float] = None  # Duration in seconds
    gps_altitude_gain: Optional[float] = None  # Gain using GPS altitude
    pressure_altitude_gain: Optional[float] = None  # Gain using pressure altitude
    average_climb_rate_gps: Optional[float] = None  # Climb rate from GPS
    average_climb_rate_pressure: Optional[float] = None  # Climb rate from pressure
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class FlightPhases:
    """
    Container to combine the different flight phases (thermal and cruise) with helper methods for easy access.
    """

    def __init__(
        self,
        classification_method: str,
        trace: list[dict[str, Any]],
        trip: Optional[Trip] = None,
    ):
        """
        :param classification_method: currently only 'pysoar' supported
        :param trace:
        :param trip: optional parameter for obtain thermals per leg
        """

        if classification_method == "pysoar":
            self._thermal_detector = PySoarThermalDetector()
        else:
            raise ValueError(
                "Classification method {} not supported".format(classification_method)
            )

        self._trip = trip
        self._phases = self._thermal_detector.analyse(trace)

    def thermals(self, leg: Optional[Union[int, str]] = None) -> list[Phase]:
        """
        Obtain only thermal phases.

        :param leg: can be 0, 1, 2 or 'all'. Obtain only thermals within specified leg or all legs.
        :return: list of thermal Phase objects
        """

        if leg is not None:
            self._check_leg(leg)

            thermals = []
            for phase in self._phases:
                if phase.is_cruise:
                    continue

                if isinstance(leg, str) and leg == "all":
                    thermal = self._get_phase_within_trip(phase)
                elif isinstance(leg, int):
                    thermal = self._get_phase_within_leg(phase, leg)
                else:
                    # This should never happen due to _check_leg, but it's safe to guard
                    continue

                if thermal is not None:
                    thermals.append(thermal)

            return thermals
        else:
            return [phase for phase in self._phases if not phase.is_cruise]

    def cruises(self, leg: Optional[Union[int, str]] = None) -> list[Phase]:
        """
        Obtain only cruise phases.

        :param leg: can be 0, 1, ... or 'all'. Obtain only cruises within specified leg or all legs.
        :return: list of cruise Phase objects
        """

        if leg is not None:
            self._check_leg(leg)

            cruises = []
            for phase in self._phases:
                if not phase.is_cruise:
                    continue

                if isinstance(leg, str) and leg == "all":
                    cruise = self._get_phase_within_trip(phase)
                elif isinstance(leg, int):
                    cruise = self._get_phase_within_leg(phase, leg)
                else:
                    continue  # Shouldn't happen due to _check_leg

                if cruise is not None:
                    cruises.append(cruise)

            return cruises
        else:
            return [phase for phase in self._phases if phase.is_cruise]

    def all_phases(self, leg: Optional[Union[int, str]] = None) -> list[Phase]:
        """
        Obtain all phases (cruise and thermal).

        :param leg: obtain only phases within specified leg (using int for leg),
                    or obtain only phases within trip (using leg='all')
        :return: list of Phase objects
        """

        if leg is not None:
            self._check_leg(leg)

            phases: list[Phase] = []
            for phase in self._phases:
                if isinstance(leg, str) and leg == "all":
                    phase_ = self._get_phase_within_trip(phase)
                elif isinstance(leg, int):
                    phase_ = self._get_phase_within_leg(phase, leg)
                else:
                    continue  # Shouldn't happen due to _check_leg

                if phase_ is not None:
                    phases.append(phase_)

            return phases
        else:
            return self._phases

    def _check_leg(self, leg: Union[int, str]) -> None:
        if self._trip is None:
            raise ValueError("No trip specified")

        if isinstance(leg, str):
            if leg != "all":
                raise NotImplementedError(
                    "Only 'all' is supported as a string leg identifier"
                )
        elif isinstance(leg, int):
            if leg > self._trip.started_legs() - 1:
                raise ValueError(f"Trip only contains {self._trip.started_legs()} legs")
        else:
            raise NotImplementedError("Leg must be an int or 'all'")

    def _get_phase_within_leg(self, phase: Phase, leg: int) -> Optional[Phase]:
        """
        Get part of phase that falls within a specified leg
        :param leg:
        :return: Phase with metadata, or None if outside leg
        """
        if self._trip is None:
            raise ValueError("No trip specified")

        phase_start_in_leg = self._trip.fix_on_leg(phase.fixes[0], leg)
        phase_end_in_leg = self._trip.fix_on_leg(phase.fixes[-1], leg)
        phase_start_before_leg = self._trip.fix_before_leg(phase.fixes[0], leg)
        phase_end_after_leg = self._trip.fix_after_leg(phase.fixes[-1], leg)

        if not phase_start_in_leg and not phase_end_in_leg:
            if phase_start_before_leg and phase_end_after_leg:
                use_trip_start_fix = True
                use_trip_end_fix = True
            else:
                return None
        elif phase_start_in_leg and phase_end_in_leg:
            use_trip_start_fix = False
            use_trip_end_fix = False
        elif phase_start_in_leg and not phase_end_in_leg:
            use_trip_start_fix = False
            use_trip_end_fix = True
        else:  # not phase_start_in_leg and phase_end_in_leg:
            use_trip_start_fix = True
            use_trip_end_fix = False

        start_fix = self._trip.fixes[leg] if use_trip_start_fix else phase.fixes[0]

        if use_trip_end_fix:
            if self._trip.outlanded() and leg == self._trip.outlanding_leg():
                end_fix = self._trip.outlanding_fix
            else:
                end_fix = self._trip.fixes[leg + 1]
        else:
            end_fix = phase.fixes[-1]

        try:
            duration = (end_fix["datetime"] - start_fix["datetime"]).total_seconds()
        except (KeyError, TypeError):
            duration = None

        try:
            gps_gain = end_fix["gps_alt"] - start_fix["gps_alt"]
            pressure_gain = end_fix["pressure_alt"] - start_fix["pressure_alt"]
        except (KeyError, TypeError):
            gps_gain = None
            pressure_gain = None

        climb_rate_gps = (
            gps_gain / duration if duration and gps_gain is not None else None
        )
        climb_rate_pressure = (
            pressure_gain / duration if duration and pressure_gain is not None else None
        )

        try:
            phase_start_index = phase.fixes.index(start_fix)
            phase_end_index = phase.fixes.index(end_fix)
            fix_subset = phase.fixes[phase_start_index : phase_end_index + 1]
        except ValueError:
            return None

        return Phase(
            is_cruise=phase.is_cruise,
            fixes=fix_subset,
            duration=duration,
            gps_altitude_gain=gps_gain,
            pressure_altitude_gain=pressure_gain,
            average_climb_rate_gps=climb_rate_gps,
            average_climb_rate_pressure=climb_rate_pressure,
            start_time=start_fix.get("datetime"),
            end_time=end_fix.get("datetime"),
        )

    def _get_phase_within_trip(self, phase: Phase) -> Optional[Phase]:
        """
        Get part of phase that falls within the trip.

        :param phase:
        :return: Phase with metadata, or None if outside trip
        """

        if self._trip is None:
            raise ValueError("No trip specified")

        first_leg = 0
        last_leg = self._trip.started_legs() - 1

        phase_start_before_trip = self._trip.fix_before_leg(phase.fixes[0], first_leg)
        phase_start_after_trip = self._trip.fix_after_leg(phase.fixes[0], last_leg)
        phase_end_before_trip = self._trip.fix_before_leg(phase.fixes[-1], first_leg)
        phase_end_after_trip = self._trip.fix_after_leg(phase.fixes[-1], last_leg)

        if phase_start_before_trip and phase_end_before_trip:
            return None
        elif phase_start_before_trip and not phase_end_before_trip:
            use_trip_start_fix = True
            if phase_end_after_trip:
                use_trip_end_fix = True
            else:
                use_trip_end_fix = False
        elif not phase_start_before_trip and not phase_end_after_trip:
            use_trip_start_fix = False
            use_trip_end_fix = False
        else:  # if not phase_start_before_trip and phase_end_after_trip
            use_trip_end_fix = True
            use_trip_start_fix = False
            if phase_start_after_trip:
                return None

        start_fix = (
            self._trip.fixes[first_leg]
            if use_trip_start_fix
            else phase.fixes[first_leg]
        )

        if use_trip_end_fix:
            if self._trip.outlanded() and last_leg == self._trip.outlanding_leg():
                end_fix = self._trip.outlanding_fix
            else:
                end_fix = self._trip.fixes[last_leg + 1]
        else:
            end_fix = phase.fixes[-1]

        try:
            duration = (end_fix["datetime"] - start_fix["datetime"]).total_seconds()
        except (KeyError, TypeError):
            duration = None

        try:
            gps_gain = end_fix["gps_alt"] - start_fix["gps_alt"]
            pressure_gain = end_fix["pressure_alt"] - start_fix["pressure_alt"]
        except (KeyError, TypeError):
            gps_gain = None
            pressure_gain = None

        climb_rate_gps = (
            gps_gain / duration if duration and gps_gain is not None else None
        )
        climb_rate_pressure = (
            pressure_gain / duration if duration and pressure_gain is not None else None
        )

        try:
            phase_start_index = phase.fixes.index(start_fix)
            phase_end_index = phase.fixes.index(end_fix)
            fix_subset = phase.fixes[phase_start_index : phase_end_index + 1]
        except ValueError:
            return None  # Fix not found in phase

        return Phase(
            is_cruise=phase.is_cruise,
            fixes=fix_subset,
            duration=duration,
            gps_altitude_gain=gps_gain,
            pressure_altitude_gain=pressure_gain,
            average_climb_rate_gps=climb_rate_gps,
            average_climb_rate_pressure=climb_rate_pressure,
            start_time=start_fix.get("datetime"),
            end_time=end_fix.get("datetime"),
        )

    def filter_by_time_range(self, start: datetime, end: datetime) -> list[Phase]:
        """
        Return all phases that overlap with the given time range.

        :param start: Start of the time window
        :param end: End of the time window
        :return: List of Phase objects that intersect with the time range
        """
        return [
            phase
            for phase in self._phases
            if phase.start_time
            and phase.end_time
            and not (phase.end_time < start or phase.start_time > end)
        ]

    def filter_by_location(
        self, center_lat: float, center_lon: float, radius_km: float
    ) -> list[Phase]:
        """
        Return all phases that pass within a given radius of a geographic point.

        :param center_lat: Latitude of the center point
        :param center_lon: Longitude of the center point
        :param radius_km: Radius in kilometers
        :return: List of Phase objects that intersect the area
        """

        def within_radius(fix) -> bool:
            try:
                dist, _ = calculate_distance_bearing(
                    fix, {"lat": center_lat, "lon": center_lon}
                )
                return dist <= radius_km * 1000  # convert km to meters
            except KeyError:
                return False

        return [
            phase
            for phase in self._phases
            if any(within_radius(fix) for fix in phase.fixes)
        ]

    def summary_stats(self) -> dict:
        """
        Return summary statistics for the flight phases.

        Includes:
        - Total number of thermals
        - Total number of cruises
        - Average thermal duration (in seconds)
        - Total cruise distance (in meters)
        """
        thermals = [p for p in self._phases if not p.is_cruise]
        cruises = [p for p in self._phases if p.is_cruise]

        total_thermals = len(thermals)
        total_cruises = len(cruises)

        avg_thermal_duration = None
        if thermals:
            durations = [p.duration for p in thermals if p.duration is not None]
            if durations:
                avg_thermal_duration = sum(durations) / len(durations)

        total_cruise_distance = 0
        for cruise in cruises:
            try:
                total_cruise_distance += total_distance_travelled(cruise.fixes)
            except Exception:
                continue  # Skip if fix data is malformed

        return {
            "total_thermals": total_thermals,
            "total_cruises": total_cruises,
            "average_thermal_duration_sec": avg_thermal_duration,
            "total_cruise_distance_m": total_cruise_distance,
        }
