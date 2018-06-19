import operator
import os
from abc import ABC, abstractmethod
from typing import List
from urllib.request import URLopener
from urllib.request import urlopen
import time

from bs4 import BeautifulSoup

from opensoar.competition.competition_day import CompetitionDay
from opensoar.task.task import Task


class DailyResultsPage(ABC):
    """
    Abstract Base Class for daily result pages. Specific implementation example: soaringspot.
    """

    def __init__(self, url):
        if url.startswith('http://') or url.startswith('https://'):
            self.url = url
        else:
            self.url = 'http://{}'.format(url)

        self._igc_directory = None  # to be set in subclass

    @property
    def igc_directory(self):
        return self._igc_directory

    def set_igc_directory(self, target_directory, competition_name, plane_class, date):
        self._igc_directory = os.path.join(target_directory, competition_name, plane_class,
                                           date.strftime('%d-%m-%Y'))

    def _get_html_soup(self) -> BeautifulSoup:
        # fix problem with SSL certificates
        # https://stackoverflow.com/questions/30551400/disable-ssl-certificate-validation-in-mechanize#35960702
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            # Legacy Python that doesn't verify HTTPS certificates by default
            pass
        else:
            # Handle target environment that doesn't support HTTPS verification
            ssl._create_default_https_context = _create_unverified_https_context

        # get entire html of page
        html = urlopen(self.url).read()

        return BeautifulSoup(html, "html.parser")

    def igc_file_name(self, competition_id: str) -> str:
        """
        Create igc file name from competition_id

        :param competition_id:
        :return:
        """
        return '{}.igc'.format(competition_id)

    def igc_file_path(self, competition_id: str) -> str:
        """
        Construct file_path from competition_id

        :param competition_id:
        :return:
        """
        file_name = self.igc_file_name(competition_id)
        return os.path.join(self._igc_directory, file_name)

    def download_flight(self, igc_url: str, competition_id: str) -> str:
        """
        Download flight and return file_path

        :param igc_url:
        :param competition_id:
        :return:
        """

        # make directory if necessary
        if not os.path.exists(self._igc_directory):
            os.makedirs(self._igc_directory)

        file_path = self.igc_file_path(competition_id)
        while not os.path.exists(file_path):
            URLopener().retrieve(igc_url, file_path)
            time.sleep(0.1)

        return file_path

    @abstractmethod
    def generate_competition_day(self, target_directory: str, download_progress=None, start_time_buffer: int = 0,
                                 include_hc_competitors: bool=True) -> CompetitionDay:
        """
        Construct a CompetitionDay. Information is pulled from the overview table and
        from the igc files, which are automatically downloaded.

        :param include_hc_competitors: optional argument for including contestants which fly 'Hors Concours',
                                       which means that they don't officially participate in the competition.
        :param target_directory: directory in which the igc files are saved
        :param download_progress: optional progress function. Should have the following signature:
                                  func(downloads, total_number_of_flights)
        :param start_time_buffer: optional relaxation on the start time in seconds. E.g. start_time_buffer = 10 means
                                  that a contestant can cross the start line 10 seconds before the official opening time
        :return:
        """

    @staticmethod
    def _select_task(tasks: List[Task]) -> Task:
        """There might be different and duplicate tasks. The task selected is most frequently present in the list."""

        unique_tasks = list()
        number_of_times_present = list()
        for task in tasks:
            if task in unique_tasks:
                index = unique_tasks.index(task)
                number_of_times_present[index] += 1
            else:
                unique_tasks.append(task)
                number_of_times_present.append(1)

        max_index, max_value = max(enumerate(number_of_times_present), key=operator.itemgetter(1))
        return tasks[max_index]