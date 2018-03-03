from collections import namedtuple

from opensoar.thermals.pysoar_thermal_detector import PySoarThermalDetector

Phase = namedtuple('Phase', 'is_cruise fixes')


class FlightPhases:

    def __init__(self, classification_method, trace, trip=None):
        """
        Container to combine the different flight phases (thermal and cruise) with helper methods for easy access.
        :param classification_method: currently only 'pysoar' supported
        :param trace: 
        :param trip: optional parameter for obtain thermals per leg
        """

        if classification_method == 'pysoar':
            self._thermal_detector = PySoarThermalDetector()
        else:
            raise ValueError('Classification method {} not supported'.format(classification_method))

        self._trip = trip
        self._phases = self._thermal_detector.analyse(trace)

    def thermals(self, leg=None):
        """Only thermals"""
        if leg is not None:

            self._check_leg(leg)

            thermals = list()
            for phase in self._phases:
                if not phase.is_cruise:
                    phase_in_leg = self._get_phase_within_leg(phase, leg)
                    if phase_in_leg is not None:
                        thermals.append(phase_in_leg)

            return thermals
        else:
            return [phase for phase in self._phases if not phase.is_cruise]

    def cruises(self, leg=None):
        """Only cruises"""

        if leg is not None:
            self._check_leg(leg)

            cruises = list()
            for phase in self._phases:
                if phase.is_cruise:
                    phase_in_leg = self._get_phase_within_leg(phase, leg)
                    if phase_in_leg is not None:
                        cruises.append(phase_in_leg)

            return cruises
        else:
            return [phase for phase in self._phases if phase.is_cruise]

    def all_phases(self, leg=None):
        """Complete list with phases"""

        if leg is not None:
            self._check_leg(leg)

            phases = list()
            for phase in self._phases:
                phase_in_leg = self._get_phase_within_leg(phase, leg)
                if phase_in_leg is not None:
                    phases.append(phase_in_leg)

            return phases
        else:
            return self._phases

    def _check_leg(self, leg):
        if self._trip is None:
            raise ValueError('No trip specified')
        else:
            if leg >= self._trip.completed_legs():
                raise ValueError('Trip only contains {} legs'.format(self._trip.completed_legs()))

    def _get_phase_within_leg(self, phase, leg):
        """
        Get part of phase that falls within a specified leg
        :param leg: 
        :return: 
        """

        phase_start_in_leg = self._trip.fix_on_leg(phase.fixes[0], leg)
        phase_end_in_leg = self._trip.fix_on_leg(phase.fixes[-1], leg)

        if not phase_start_in_leg and not phase_end_in_leg:
            return None
        elif phase_start_in_leg and phase_end_in_leg:
            return phase
        elif phase_start_in_leg and not phase_end_in_leg:
            end_fix = self._trip.fixes[leg + 1]
            phase_end_index = phase.fixes.index(end_fix)
            return Phase(phase.is_cruise, phase.fixes[0:phase_end_index+1])
        else:  # not phase_start_in_leg and phase_end_in_leg:
            start_fix = self._trip.fixes[leg]
            phase_start_index = phase.fixes.index(start_fix)
            return Phase(phase.is_cruise, phase.fixes[phase_start_index::])
