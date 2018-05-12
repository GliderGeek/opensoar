from opensoar.utilities.helper_functions import triple_iterator, calculate_bearing_change, calculate_distance, \
    seconds_time_difference


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

    def __init__(self):
        pass

    def analyse(self, trace):

        # To prevent circular import with flight_phases
        from opensoar.thermals.flight_phases import Phase

        cruise = True
        possible_thermal_fixes = list()
        possible_cruise_fixes = list()
        sharp_thermal_entry_found = False
        turning_left = True
        total_bearing_change = 0

        # Start with first phase
        phases = [Phase(cruise, trace[0:2])]

        for fix_minus2, fix_minus1, fix in triple_iterator(trace):

            time_minus2 = fix_minus2['time']
            time_minus1 = fix_minus1['time']
            time = fix['time']

            bearing_change = calculate_bearing_change(fix_minus2, fix_minus1, fix)
            delta_t = (0.5 * seconds_time_difference(time_minus1, time) +
                       0.5 * seconds_time_difference(time_minus2, time))
            bearing_change_rate = bearing_change / delta_t

            if cruise:

                continuing_left = turning_left and bearing_change_rate < self.MINIMUM_BEARING_CHANGE_RATE
                continuing_right = not turning_left and bearing_change_rate > -self.MINIMUM_BEARING_CHANGE_RATE

                if continuing_left or continuing_right:

                    total_bearing_change += bearing_change

                    if len(possible_thermal_fixes) == 0:
                        possible_thermal_fixes = [fix]
                    else:
                        if not sharp_thermal_entry_found and abs(bearing_change_rate) > self.CRUISE_THRESHOLD_BEARINGRATE:
                            sharp_thermal_entry_found = True
                            phases[-1].fixes.extend(possible_thermal_fixes)
                            possible_thermal_fixes = [fix]
                        else:
                            possible_thermal_fixes.append(fix)

                else:  # sign change
                    total_bearing_change = bearing_change
                    sharp_thermal_entry_found = False

                    if len(possible_thermal_fixes) == 0:
                        phases[-1].fixes.append(fix)
                    else:
                        phases[-1].fixes.extend([*possible_thermal_fixes, fix])
                        possible_thermal_fixes = list()

                    turning_left = bearing_change_rate < 0

                if abs(total_bearing_change) > self.CRUISE_THRESHOLD_BEARINGTOT:
                    cruise = False
                    phases[-1].fixes.append(possible_thermal_fixes[0])
                    phases.append(Phase(cruise, possible_thermal_fixes))

                    possible_thermal_fixes = list()
                    sharp_thermal_entry_found = False
                    total_bearing_change = 0

            else:  # thermal

                if abs(bearing_change_rate) > self.THERMAL_THRESHOLD_BEARINGRATE:
                    if len(possible_cruise_fixes) != 0:
                        phases[-1].fixes.extend([*possible_cruise_fixes, fix])
                        possible_cruise_fixes = list()
                    else:
                        phases[-1].fixes.append(fix)

                else:  # possible cruise

                    if len(possible_cruise_fixes) == 0:
                        possible_cruise_fixes = [fix]
                        total_bearing_change = bearing_change
                    else:
                        possible_cruise_fixes.append(fix)
                        total_bearing_change += bearing_change

                    delta_t = seconds_time_difference(possible_cruise_fixes[0]['time'], time)
                    cruise_distance = calculate_distance(possible_cruise_fixes[0], fix)
                    temp_bearing_rate_avg = 0 if delta_t == 0 else total_bearing_change / delta_t

                    if (cruise_distance > self.THERMAL_THRESHOLD_DISTANCE and
                            abs(temp_bearing_rate_avg) < self.THERMAL_THRESHOLD_BEARINGRATE_AVG):

                        cruise = True
                        phases[-1].fixes.append(possible_cruise_fixes[0])
                        phases.append(Phase(cruise, possible_cruise_fixes))
                        possible_cruise_fixes = list()
                        total_bearing_change = 0

        # add possible fixes at the end
        if cruise:
            if len(possible_thermal_fixes) != 0:
                phases[-1].fixes.extend(possible_thermal_fixes)
        else:
            if len(possible_cruise_fixes) != 0:
                phases[-1].fixes.extend(possible_cruise_fixes)

        return phases
