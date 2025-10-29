from typing import TYPE_CHECKING

from opensoar.utilities.helper_functions import (
    calculate_bearing_change,
    calculate_distance_bearing,
    triple_iterator,
)

if TYPE_CHECKING:
    from opensoar.thermals.flight_phases import Phase


class PySoarThermalDetector:
    """
    Detector taken from the PySoar project.
    """

    MINIMUM_BEARING_CHANGE_RATE = 1e-2
    CRUISE_THRESHOLD_BEARINGRATE = 4  # deg/s
    CRUISE_THRESHOLD_BEARINGTOT = 225  # deg
    THERMAL_THRESHOLD_DISTANCE = 1000  # m
    THERMAL_THRESHOLD_BEARINGRATE_AVG = 2  # deg/s
    THERMAL_THRESHOLD_BEARINGRATE = 4  # deg/s

    def __init__(self) -> None:
        pass

    def _create_phase(self, is_cruise: bool, fixes: list[dict]) -> "Phase":
        from opensoar.thermals.flight_phases import Phase

        start = fixes[0]
        end = fixes[-1]
        duration = (end["datetime"] - start["datetime"]).total_seconds()
        gps_gain = end["gps_alt"] - start["gps_alt"]
        pressure_gain = end["pressure_alt"] - start["pressure_alt"]
        climb_rate_gps = gps_gain / duration if duration > 0 else None
        climb_rate_pressure = pressure_gain / duration if duration > 0 else None

        return Phase(
            is_cruise=is_cruise,
            fixes=fixes,
            duration=duration,
            gps_altitude_gain=gps_gain,
            pressure_altitude_gain=pressure_gain,
            average_climb_rate_gps=climb_rate_gps,
            average_climb_rate_pressure=climb_rate_pressure,
            start_time=start["datetime"],
            end_time=end["datetime"],
        )

    def analyse(self, trace: list[dict]) -> list["Phase"]:
        cruise = True
        possible_thermal_fixes = []
        possible_cruise_fixes = []
        sharp_thermal_entry_found = False
        turning_left = True
        total_bearing_change = 0

        phases = [self._create_phase(cruise, trace[0:2])]

        for fix_minus2, fix_minus1, fix in triple_iterator(trace):
            time_minus2 = fix_minus2["datetime"]
            time_minus1 = fix_minus1["datetime"]
            time = fix["datetime"]

            bearing_change = calculate_bearing_change(fix_minus2, fix_minus1, fix)
            delta_t = (
                0.5 * (time - time_minus1).total_seconds()
                + 0.5 * (time - time_minus2).total_seconds()
            )
            bearing_change_rate = bearing_change / delta_t

            if cruise:
                continuing_left = (
                    turning_left
                    and bearing_change_rate < self.MINIMUM_BEARING_CHANGE_RATE
                )
                continuing_right = (
                    not turning_left
                    and bearing_change_rate > -self.MINIMUM_BEARING_CHANGE_RATE
                )

                if continuing_left or continuing_right:
                    total_bearing_change += bearing_change
                    if not possible_thermal_fixes:
                        possible_thermal_fixes = [fix]
                    elif (
                        not sharp_thermal_entry_found
                        and abs(bearing_change_rate) > self.CRUISE_THRESHOLD_BEARINGRATE
                    ):
                        sharp_thermal_entry_found = True
                        phases[-1].fixes.extend(possible_thermal_fixes)
                        possible_thermal_fixes = [fix]
                    else:
                        possible_thermal_fixes.append(fix)
                else:
                    total_bearing_change = bearing_change
                    sharp_thermal_entry_found = False
                    if not possible_thermal_fixes:
                        phases[-1].fixes.append(fix)
                    else:
                        phases[-1].fixes.extend([*possible_thermal_fixes, fix])
                        possible_thermal_fixes = []
                    turning_left = bearing_change_rate < 0

                if abs(total_bearing_change) > self.CRUISE_THRESHOLD_BEARINGTOT:
                    cruise = False
                    phases[-1].fixes.append(possible_thermal_fixes[0])
                    phases.append(self._create_phase(cruise, possible_thermal_fixes))
                    possible_thermal_fixes = []
                    sharp_thermal_entry_found = False
                    total_bearing_change = 0

            else:
                if abs(bearing_change_rate) > self.THERMAL_THRESHOLD_BEARINGRATE:
                    if possible_cruise_fixes:
                        phases[-1].fixes.extend([*possible_cruise_fixes, fix])
                        possible_cruise_fixes = []
                    else:
                        phases[-1].fixes.append(fix)
                else:
                    if not possible_cruise_fixes:
                        possible_cruise_fixes = [fix]
                        total_bearing_change = bearing_change
                    else:
                        possible_cruise_fixes.append(fix)
                        total_bearing_change += bearing_change

                    delta_t = (
                        time - possible_cruise_fixes[0]["datetime"]
                    ).total_seconds()
                    cruise_distance, _ = calculate_distance_bearing(
                        possible_cruise_fixes[0], fix
                    )
                    temp_bearing_rate_avg = (
                        0 if delta_t == 0 else total_bearing_change / delta_t
                    )

                    if (
                        cruise_distance > self.THERMAL_THRESHOLD_DISTANCE
                        and abs(temp_bearing_rate_avg)
                        < self.THERMAL_THRESHOLD_BEARINGRATE_AVG
                    ):
                        cruise = True
                        phases[-1].fixes.append(possible_cruise_fixes[0])
                        phases.append(self._create_phase(cruise, possible_cruise_fixes))
                        possible_cruise_fixes = []
                        total_bearing_change = 0

        if cruise and possible_thermal_fixes:
            phases[-1].fixes.extend(possible_thermal_fixes)
        elif not cruise and possible_cruise_fixes:
            phases[-1].fixes.extend(possible_cruise_fixes)

        return phases
