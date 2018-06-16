from collections import namedtuple
from typing import Union, List

from opensoar.thermals.pysoar_thermal_detector import PySoarThermalDetector

Phase = namedtuple('Phase', 'is_cruise fixes')


class FlightPhases:
    """
    Container to combine the different flight phases (thermal and cruise) with helper methods for easy access.
    """

    def __init__(self, classification_method: str, trace: list, trip=None):
        """
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

    def thermals(self, leg: Union[int, str]=None) -> List[Phase]:
        """
        Obtain only thermal phases.

        :param leg: can be 0, 1, 2 or 'all'. Obtain only thermals within specified leg or all legs.
        :return:
        """

        if leg is not None:

            self._check_leg(leg)

            thermals = list()
            for phase in self._phases:
                if phase.is_cruise:
                    continue

                if leg == 'all':
                    thermal = self._get_phase_within_trip(phase)
                else:
                    thermal = self._get_phase_within_leg(phase, leg)

                if thermal is not None:
                    thermals.append(thermal)

            return thermals
        else:
            return [phase for phase in self._phases if not phase.is_cruise]

    def cruises(self, leg: Union[int, str]=None) -> List[Phase]:
        """
        Obtain only cruise phases.

        :param leg:can be 0, 1, ... or 'all'. Obtain only cruises within specified leg or all legs.
        :return:
        """

        if leg is not None:
            self._check_leg(leg)

            cruises = list()
            for phase in self._phases:

                if not phase.is_cruise:
                    continue

                if leg == 'all':
                    cruise = self._get_phase_within_trip(phase)
                else:
                    cruise = self._get_phase_within_leg(phase, leg)

                if cruise is not None:
                    cruises.append(cruise)

            return cruises
        else:
            return [phase for phase in self._phases if phase.is_cruise]

    def all_phases(self, leg: Union[int, str]=None) -> List[Phase]:
        """
        Obtain all phases (cruise and thermal).

        :param leg: obtain only phases within specified leg (using int for leg),
                    or obtain only phases within trip (using leg='all')
        :return:
        """

        if leg is not None:

            self._check_leg(leg)

            phases = list()
            for phase in self._phases:

                if leg == 'all':
                    phase_ = self._get_phase_within_trip(phase)
                else:
                    phase_ = self._get_phase_within_leg(phase, leg)

                if phase_ is not None:
                    phases.append(phase_)

            return phases
        else:
            return self._phases

    def _check_leg(self, leg):
        if self._trip is None:
            raise ValueError('No trip specified')
        else:

            if type(leg) == str:
                if leg != 'all':
                    raise NotImplementedError
            elif type(leg) == int:
                if leg > self._trip.started_legs() - 1:
                    raise ValueError('Trip only contains {} legs'.format(self._trip.started_legs()))
            else:
                raise NotImplementedError

    def _get_phase_within_leg(self, phase: Phase, leg: int) -> Phase:

        """
        Get part of phase that falls within a specified leg
        :param leg: 
        :return: 
        """

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

        phase_start_index = phase.fixes.index(start_fix)
        phase_end_index = phase.fixes.index(end_fix)
        return Phase(phase.is_cruise, phase.fixes[phase_start_index:phase_end_index + 1])

    def _get_phase_within_trip(self, phase):

        """
        Get part of phase that falls within the trip.

        :param phase:
        :return: phase. None if completely outside trip
        """

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

        start_fix = self._trip.fixes[first_leg] if use_trip_start_fix else phase.fixes[first_leg]

        if use_trip_end_fix:
            if self._trip.outlanded() and last_leg == self._trip.outlanding_leg():
                end_fix = self._trip.outlanding_fix
            else:
                end_fix = self._trip.fixes[last_leg + 1]
        else:
            end_fix = phase.fixes[-1]

        phase_start_index = phase.fixes.index(start_fix)
        phase_end_index = phase.fixes.index(end_fix)
        return Phase(phase.is_cruise, phase.fixes[phase_start_index:phase_end_index + 1])
