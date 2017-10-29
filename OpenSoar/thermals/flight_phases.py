from OpenSoar.thermals.pysoar_thermal_detector import PySoarThermalDetector


class FlightPhases:

    def __init__(self, classification_method, trace, trip=None):
        """
        Container to combine the different flight phases (thermal and cruise) with helper methods for easy access.
        :param classification_method:
        :param trace: 
        :param trip: 
        """

        if classification_method == 'pysoar':
            self._thermal_detector = PySoarThermalDetector()
        else:
            raise ValueError('Classification method {} not supported'.format(classification_method))

        self._trace = trace
        self._trip = trip
        self._phases = self._thermal_detector.analyse(self._trace)

    def thermals(self, leg=None):
        """only return thermals"""

        if leg is not None:
            self._check_leg(leg)

        pass

    def cruises(self, leg=None):
        """only return cruises"""

        if leg is not None:
            self._check_leg(leg)

        pass

    def all_phases(self, leg=None):
        """return complete list with phases"""

        if leg is not None:
            self._check_leg(leg)

        return self._phases

    def thermal_fixes(self, leg=None):
        """return list with thermals. each thermal is a list of GPS fixes"""

        if leg is not None:
            self._check_leg(leg)

        pass

    def cruise_fixes(self, leg=None):
        """return list of cruises. each cruise is a list of GPS fixes"""

        if leg is not None:
            self._check_leg(leg)

        pass

    def _check_leg(self, leg):
        if self._trip is None:
            raise ValueError('No trip information present')
        else:
            if leg >= self._trip.completed_legs:
                raise ValueError('Trip only contains {} legs'.format(self._trip.completed_legs))
