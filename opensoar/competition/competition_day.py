import datetime
from typing import List

from opensoar.competition.competitor import Competitor
from opensoar.task.task import Task


# TODO: This is a temporary fix for deepcopy issues with TimeZoneFix
# Issue reference: https://github.com/Turbo87/aerofiles/issues/318
# Remove this once aerofiles is updated with a proper fix
from aerofiles.util.timezone import TimeZoneFix

# TimeZoneFix from aerofiles doesn't support deepcopy properly
# Add a __deepcopy__ method to fix serialization issues
def _deepcopy_timezone_fix(self, memo):
    """Create a proper deep copy of a TimeZoneFix instance."""
    return TimeZoneFix(self.fix)

# Apply monkeypatch
TimeZoneFix.__deepcopy__ = _deepcopy_timezone_fix


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

    def analyse_flights(self, classification_method: str, analysis_progress=None, skip_failed_analyses: bool=False):
        """
        :param classification_method: method for detecting thermals. See FlightPhases for more info.
        :param analysis_progress: optional function to log the analysis progress. Should have the following signature:
                                  func(number_of_analyses, total_number_of_flights)
        :param skip_failed_analyses: if True, exceptions are caught during a failed analysis. a list is return with the
                                     competition ids of all failed analyses.
        :return:
        """

        if self.task is None:
            raise ValueError('Task not present')

        if self.task.multistart:
            raise ValueError('Multistart is not supported')

        number_of_analyzed_flights = 0

        failed_comp_ids = []
        for competitor in self.competitors:

            if skip_failed_analyses:
                try:
                    competitor.analyse(self.task, classification_method)
                except Exception:
                    failed_comp_ids.append(competitor.competition_id)
            else:
                competitor.analyse(self.task, classification_method)

            if analysis_progress is not None:
                number_of_analyzed_flights += 1
                analysis_progress(number_of_analyzed_flights, len(self.competitors))

        return failed_comp_ids
