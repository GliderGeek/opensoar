from typing import List

from OpenSoar.task.trip import Trip
from OpenSoar.thermals.flight_phases import FlightPhases


class Competitor:

    def __init__(self, trace: List, competition_id: str=None, airplane: str=None, ranking: int=None, pilot: str=None):
        self._trace = trace
        self._competition_id = competition_id
        self._airplane = airplane
        self._ranking = ranking
        self._pilot = pilot

        # to be set by analyse method
        self._trip = None
        self._phases = None

    def analyse(self, task):
        self._trip = Trip(task, self._trace)

        # competitor should have at least started
        if self._trip.fixes >= 1:
            self._phases = FlightPhases(self._trip, self._trace)
