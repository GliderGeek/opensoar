import datetime
from typing import List

from OpenSoar.competition.competitor import Competitor
from OpenSoar.task.task import Task


class CompetitionDay:

    def __init__(self, competitors: List[Competitor], task: Task, date: datetime.date):

        self._competitors = competitors
        self._task = task
        self._date = date

    def analyse_flights(self):
        for competitor in self._competitors:
            competitor.analyse(self._task)
