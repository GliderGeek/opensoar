import datetime
from typing import List

from opensoar.competition.competitor import Competitor
from opensoar.task.task import Task


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

    def analyse_flights(self, analysis_progress=None):
        """
        :param analysis_progress: optional function to log the analysis progress.
        Function should have two inputs: number_of_analyses, total_number_of_flights
        :return:
        """

        if self.task is None:
            raise ValueError('Task not present')

        number_of_analyzed_flights = 0
        for competitor in self.competitors:
            competitor.analyse(self.task)

            if analysis_progress is not None:
                number_of_analyzed_flights += 1
                analysis_progress(number_of_analyzed_flights, len(self.competitors))
