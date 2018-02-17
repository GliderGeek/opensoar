import datetime
from typing import List

from OpenSoar.competition.competitor import Competitor
from OpenSoar.task.task import Task


class CompetitionDay:

    def __init__(self, name: str, date: datetime.date, plane_class: str, competitors: List[Competitor],
                 task: Task = None):

        if competitors is None:
            competitors = list()

        self.name = name
        self.competitors = competitors
        self.task = task
        self.date = date
        self.plane_class = plane_class

    def analyse_flights(self):

        if self.task is None:
            raise ValueError('Task not present')

        for competitor in self.competitors:
            competitor.analyse(self.task)
