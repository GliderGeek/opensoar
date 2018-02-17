from typing import List

from opensoar.task.trip import Trip
from opensoar.thermals.flight_phases import FlightPhases


class Competitor:

    def __init__(self, trace: List, competition_id: str=None, airplane: str=None, ranking: int=None, pilot: str=None,
                 igc_url=None):

        self.trace = trace
        self.competition_id = competition_id
        self._airplane = airplane
        self.ranking = ranking
        self._pilot = pilot
        self.igc_url = igc_url

        # to be set by analyse method
        self._trip = None
        self._phases = None

    def analyse(self, task):

        if self.trace is None or len(self.trace) == 0:
            raise ValueError('No trace present')

        self._trip = Trip(task, self.trace)

        # competitor should have at least started
        if self._trip.fixes >= 1:
            self._phases = FlightPhases(self._trip, self.trace)
