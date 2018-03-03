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

    def __init__(self, url):
        if url.startswith('http://') or url.startswith('https://'):
            self.url = url
        else:
            self.url = f'http://{url}'

        self._igc_directory = None  # to be set in subclass

    @property
    def igc_directory(self):
        return self._igc_directory

    def set_igc_directory(self, target_directory, competition_name, plane_class, date):
        self._igc_directory = os.path.join(target_directory, competition_name, plane_class,
                                           date.strftime('%d-%m-%Y'))

    def _get_html_soup(self):
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

    def igc_file_name(self, competition_id):
        return f'{competition_id}.igc'

    def igc_file_path(self, competition_id):
        file_name = self.igc_file_name(competition_id)
        return os.path.join(self._igc_directory, file_name)

    def download_flight(self, igc_url, competition_id):
        # make directory if necessary
        if not os.path.exists(self._igc_directory):
            os.makedirs(self._igc_directory)

        file_path = self.igc_file_path(competition_id)
        while not os.path.exists(file_path):
            URLopener().retrieve(igc_url, file_path)
            time.sleep(0.1)

        return file_path

    @abstractmethod
    def generate_competition_day(self, target_directory, download_progress=None) -> CompetitionDay:
        """Fallback to base class. This function downloads the igc files and constructs a CompetitionDay"""

    @staticmethod
    def _select_task(tasks: List[Task]):
        """There might be different and duplicate tasks. The task is selected is most frequently present in the list."""

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