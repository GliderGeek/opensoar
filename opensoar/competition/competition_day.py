import datetime
from typing import List

from opensoar.competition.competitor import Competitor
from opensoar.task.task import Task


class CompetitionDay:
    """
    This class contains the competition day information, equal fo all competitors.
    """

    def __init__(self, name: str, date: datetime.date, plane_class: str, competitors: List[Competitor],
                 task: Task):
        """
        :param name: description of the competition day. used for storing igc files.
        :param date: date on which the competition day takes place. used for storing igc files.
        :param plane_class: competition class (e.g. club-class). used for storing igc files.
        :param competitors: contestants in the competition day.
        :param task:
        """

        if competitors is None:
            competitors = list()

        self.name = name
        self.competitors = competitors
        self.task = task
        self.date = date
        self.plane_class = plane_class

    def analyse_flights(self, classification_method: str, analysis_progress=None):
        """
        :param classification_method: method for detecting thermals. See FlightPhases for more info.
        :param analysis_progress: optional function to log the analysis progress. Should have the following signature:
                                  func(number_of_analyses, total_number_of_flights)
        :return:
        """

        if self.task is None:
            raise ValueError('Task not present')

        if self.task.multistart:
            raise ValueError('Multistart is not supported')

        number_of_analyzed_flights = 0
        for competitor in self.competitors:
            competitor.analyse(self.task, classification_method)

            if analysis_progress is not None:
                number_of_analyzed_flights += 1
                analysis_progress(number_of_analyzed_flights, len(self.competitors))
