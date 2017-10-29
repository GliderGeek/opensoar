from OpenSoar.utilities.helper_functions import triple_iterator, calculate_bearing_change, calculate_distance, \
    seconds_time_difference


class PySoarThermalDetector:

    MINIMUM_BEARING_CHANGE_RATE = 1e-2
    CRUISE_THRESHOLD_BEARINGRATE = 4  # deg/s
    CRUISE_THRESHOLD_BEARINGTOT = 225  # deg
    THERMAL_THRESHOLD_DISTANCE = 1000  # m
    THERMAL_THRESHOLD_BEARINGRATE_AVG = 2  # deg/s
    THERMAL_THRESHOLD_BEARINGRATE = 4  # deg/s

    def __init__(self):
        pass

    def analyse(self, trace):

        cruise = True
        bearing_change_tot = 0
        possible_thermal_start = None
        possible_cruise_start = None
        sharp_thermal_entry_found = False
        possible_turn_dir = 'left'
        temp_bearing_change = 0
        cruise_distance = 0

        phases = [dict(start_fix=trace[0], end_fix=None, cruise=cruise)]

        for fix_minus2, fix_minus1, fix in triple_iterator(trace):

            time_minus2 = fix_minus2['time']
            time_minus1 = fix_minus1['time']
            time = fix['time']

            bearing_change = calculate_bearing_change(fix_minus2, fix_minus1, fix)
            delta_t = (0.5 * seconds_time_difference(time_minus1, time) +
                       0.5 * seconds_time_difference(time_minus2, time_minus1))
            bearing_change_rate = bearing_change / delta_t

            if cruise:

                if (possible_turn_dir == 'left' and bearing_change_rate < self.MINIMUM_BEARING_CHANGE_RATE) or \
                        (possible_turn_dir == 'right' and bearing_change_rate > -self.MINIMUM_BEARING_CHANGE_RATE):

                    bearing_change_tot += bearing_change

                    if possible_thermal_start is None:
                        possible_thermal_start = fix
                    elif (not sharp_thermal_entry_found) and abs(
                            bearing_change_rate) > self.CRUISE_THRESHOLD_BEARINGRATE:
                        sharp_thermal_entry_found = True
                        possible_thermal_start = fix

                else:  # sign change
                    bearing_change_tot = bearing_change
                    possible_turn_dir = 'left' if bearing_change_rate < 0 else 'right'

                if abs(bearing_change_tot) > self.CRUISE_THRESHOLD_BEARINGTOT:
                    print('here')
                    cruise = False
                    phases[-1]['end_fix'] = possible_thermal_start
                    phases.append(dict(start_fix=possible_thermal_start, end_fix=None, cruise=False))
                    possible_thermal_start = None
                    sharp_thermal_entry_found = False
                    bearing_change_tot = 0

            else:  # thermal
                if abs(bearing_change_rate) > self.THERMAL_THRESHOLD_BEARINGRATE:
                    if possible_cruise_start is not None:
                        cruise_distance = 0
                        temp_bearing_change = 0
                else:  # possible cruise
                    if cruise_distance == 0:
                        possible_cruise_start = fix
                        temp_bearing_change += bearing_change
                        temp_bearing_rate_avg = 0
                    else:
                        temp_bearing_change += bearing_change
                        temp_bearing_rate_avg = temp_bearing_change / (time - possible_cruise_start['time'])

                    if fix is possible_cruise_start:
                        cruise_distance = 0
                    else:
                        cruise_distance = calculate_distance(possible_cruise_start, fix)

                    if (cruise_distance > self.THERMAL_THRESHOLD_DISTANCE and
                            abs(temp_bearing_rate_avg) < self.THERMAL_THRESHOLD_BEARINGRATE_AVG):

                        cruise = True
                        phases[-1]['end_fix'] = possible_cruise_start
                        phases.append(dict(start_fix=possible_cruise_start, end_fix=None, cruise=True))

                        possible_cruise_start = None
                        cruise_distance = 0
                        temp_bearing_change = 0
                        bearing_change_tot = 0

        phases[-1]['end_fix'] = trace[-1]
        return phases
