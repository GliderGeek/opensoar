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
        possible_thermal_start = None
        possible_cruise_start = None
        sharp_thermal_entry_found = False
        turn_direction = 'left'
        total_bearing_change = 0

        phases = [dict(start_fix=trace[0], end_fix=None, cruise=cruise)]

        for fix_minus2, fix_minus1, fix in triple_iterator(trace):

            time_minus2 = fix_minus2['time']
            time_minus1 = fix_minus1['time']
            time = fix['time']

            bearing_change = calculate_bearing_change(fix_minus2, fix_minus1, fix)
            delta_t = (0.5 * seconds_time_difference(time_minus1, time) +
                       0.5 * seconds_time_difference(time_minus2, time))
            bearing_change_rate = bearing_change / delta_t  # todo: investigate this approximation.

            if cruise:

                continuing_left = turn_direction == 'left' and bearing_change_rate < self.MINIMUM_BEARING_CHANGE_RATE
                continuing_right = turn_direction == 'right' and bearing_change_rate > -self.MINIMUM_BEARING_CHANGE_RATE

                if continuing_left or continuing_right:

                    total_bearing_change += bearing_change

                    if possible_thermal_start is None:
                        possible_thermal_start = fix
                    elif (not sharp_thermal_entry_found) and abs(
                            bearing_change_rate) > self.CRUISE_THRESHOLD_BEARINGRATE:
                        sharp_thermal_entry_found = True
                        possible_thermal_start = fix

                else:  # sign change
                    total_bearing_change = bearing_change
                    sharp_thermal_entry_found = False
                    possible_thermal_start = None
                    turn_direction = 'left' if bearing_change_rate < 0 else 'right'

                if abs(total_bearing_change) > self.CRUISE_THRESHOLD_BEARINGTOT:
                    cruise = False
                    phases[-1]['end_fix'] = possible_thermal_start
                    phases.append(dict(start_fix=possible_thermal_start, end_fix=None, cruise=False))
                    possible_thermal_start = None
                    sharp_thermal_entry_found = False
                    total_bearing_change = 0

            else:  # thermal
                if abs(bearing_change_rate) > self.THERMAL_THRESHOLD_BEARINGRATE:
                    if possible_cruise_start is not None:
                        possible_cruise_start = None
                else:  # possible cruise
                    if possible_cruise_start is None:
                        possible_cruise_start = fix
                        total_bearing_change = bearing_change
                    else:
                        total_bearing_change += bearing_change

                    delta_t = seconds_time_difference(possible_cruise_start['time'], time)
                    cruise_distance = calculate_distance(possible_cruise_start, fix)
                    temp_bearing_rate_avg = 0 if delta_t == 0 else total_bearing_change / delta_t

                    if (cruise_distance > self.THERMAL_THRESHOLD_DISTANCE and
                            abs(temp_bearing_rate_avg) < self.THERMAL_THRESHOLD_BEARINGRATE_AVG):

                        cruise = True
                        phases[-1]['end_fix'] = possible_cruise_start
                        phases.append(dict(start_fix=possible_cruise_start, end_fix=None, cruise=True))

                        possible_cruise_start = None
                        total_bearing_change = 0

        phases[-1]['end_fix'] = trace[-1]
        return phases
