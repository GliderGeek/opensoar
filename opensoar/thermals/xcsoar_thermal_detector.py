from enum import Enum

from opensoar.thermals.thermal_detector import ThermalDetector
from opensoar.utilities.helper_functions import triple_iterator, calculate_bearing_change, seconds_time_difference, \
    seconds_time_difference_fixes


class FLYINGSTATE(Enum):
    CRUISE = 1
    POSSIBLE_THERMAL = 2
    THERMAL = 3
    POSSIBLE_CRUISE = 4


def lowpass(y_last, x_in, fact):
    return (1.0 - fact) * y_last + fact * x_in


class XCSoarThermalDetector(ThermalDetector):

    CRUISE_THERMAL_SWITCH = 15
    THERMAL_CRUISE_SWITCH = 10
    MIN_TURN_RATE = 4  # deg/s

    def __init__(self):
        super().__init__()

    def calculate_turn_rate_smoothed(self, fix_minus2, fix_minus1, fix, turn_rate_smoothed):

        time_minus2 = fix_minus2['time']
        time_minus1 = fix_minus1['time']
        time = fix['time']

        bearing_change = calculate_bearing_change(fix_minus2, fix_minus1, fix)
        delta_t = (0.5 * seconds_time_difference(time_minus1, time) +
                   0.5 * seconds_time_difference(time_minus2, time))

        turn_rate = bearing_change / delta_t

        # turn_rate cannot be smaller than -50 or larger than +50
        turn_rate = -50 if turn_rate < -50 else turn_rate
        turn_rate = 50 if turn_rate > 50 else turn_rate

        turn_rate_smoothed = lowpass(turn_rate_smoothed, turn_rate, 0.3)
        return turn_rate_smoothed

    def analyse(self, trace):

        # To prevent circular import with flight_phases
        from .flight_phases import Phase

        # start with cruise
        flying_state = FLYINGSTATE.CRUISE

        phases = [Phase(True, trace[0:2])]
        possible_thermal_fixes = []
        possible_cruise_fixes = []
        turn_rate_smoothed = 0

        # todo fill phases
        # todo: check subtracting datetimes like this

        for fix_minus2, fix_minus1, fix in triple_iterator(trace):

            if not fix_minus2['time'] < fix_minus1['time'] < fix['time']:
                continue

            turn_rate_smoothed = self.calculate_turn_rate_smoothed(fix_minus2, fix_minus1, fix, turn_rate_smoothed)
            circling = abs(turn_rate_smoothed) > self.MIN_TURN_RATE

            if flying_state == FLYINGSTATE.CRUISE:
                if circling:
                    flying_state = FLYINGSTATE.POSSIBLE_THERMAL
                    possible_thermal_fixes = [fix]
                else:
                    phases[-1].fixes.append(fix)
            elif flying_state == FLYINGSTATE.POSSIBLE_THERMAL:
                if circling:
                    possible_thermal_fixes.append(fix)
                    possible_thermal_duration = seconds_time_difference_fixes(possible_thermal_fixes[0],
                                                                              possible_thermal_fixes[-1])
                    if possible_thermal_duration > self.CRUISE_THERMAL_SWITCH:
                        flying_state = FLYINGSTATE.THERMAL
                        phases[-1].fixes.append(possible_thermal_fixes[0])
                        phases.append(Phase(is_cruise=False, fixes=possible_thermal_fixes))
                        possible_thermal_fixes = []
                else:
                    flying_state = FLYINGSTATE.CRUISE
                    phases[-1].fixes.extend(possible_thermal_fixes)
                    possible_thermal_fixes = []
            elif flying_state == FLYINGSTATE.THERMAL:
                if not circling:
                    flying_state = FLYINGSTATE.POSSIBLE_CRUISE
                    possible_cruise_fixes = [fix]
                else:
                    phases[-1].fixes.append(fix)
            elif flying_state == FLYINGSTATE.POSSIBLE_CRUISE:
                if circling:
                    flying_state = FLYINGSTATE.THERMAL
                    phases[-1].fixes.extend(possible_cruise_fixes)
                    possible_cruise_fixes = []
                else:
                    possible_cruise_fixes.append(fix)
                    possible_cruise_duration = seconds_time_difference_fixes(possible_cruise_fixes[0],
                                                                             possible_cruise_fixes[-1])
                    if possible_cruise_duration > self.THERMAL_CRUISE_SWITCH:
                        flying_state = FLYINGSTATE.CRUISE
                        phases[-1].fixes.append(possible_cruise_fixes[0])
                        phases.append(Phase(is_cruise=True, fixes=possible_cruise_fixes))
                        possible_cruise_fixes = []
            else:
                raise ValueError

        return phases
