from typing import List, Union

from opensoar.task.trip import Trip
from opensoar.thermals.flight_phases import FlightPhases


class Competitor:
    """
    All the information of one entry in a CompetitionDay. This encompasses information about the pilot,
    the plane and the gps trace.
    """

    def __init__(self, trace: List, competition_id: str=None, plane_model: str=None, ranking: Union[int, str]=None,
                 pilot_name: str=None):

        """

        :param trace:
        :param competition_id:
        :param plane_model:
        :param ranking: may also be 'HC' when competitor flies hors concours.
        :param pilot_name:
        """

        self.trace = trace
        self.competition_id = competition_id
        self._plane_model = plane_model
        self.ranking = ranking
        self._pilot_name = pilot_name

        # to be set by analyse method
        self._trip = None
        self._phases = None

    @property
    def trip(self):
        return self._trip

    @property
    def pilot_name(self):
        return self._pilot_name

    @property
    def plane_model(self):
        return self._plane_model

    @property
    def phases(self):
        return self._phases

    def analyse(self, task, classification_method: str):

        if self.trace is None or len(self.trace) == 0:
            raise ValueError('No trace present')

        self._trip = Trip(task, self.trace)

        # competitor should have at least started
        if len(self._trip.fixes) >= 1:
            self._phases = FlightPhases(classification_method, self.trace, self._trip)
