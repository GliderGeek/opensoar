import os
from abc import ABC, abstractmethod
from typing import List
from urllib.request import URLopener
from urllib.request import urlopen
import time

from bs4 import BeautifulSoup

from opensoar.competition.competition_day import CompetitionDay
from opensoar.competition.competitor import Competitor


class DailyResultsPage(ABC):

    def __init__(self, url, target_directory):

        if url.startswith('http://') or url.startswith('https://'):
            self.url = url
        else:
            self.url = f'http://{url}'

        self.competitors = self._get_competitors()
        self.competition_day = self._get_competition_day(self.competitors)

        self._igc_directory = os.path.join(target_directory, self.competition_day.name,
                                           self.competition_day.plane_class,
                                           self.competition_day.date.strftime('%d-%m-%Y'))

    @property
    def igc_directory(self):
        return self._igc_directory

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

    def download_flights(self, download_progress=None):
        """
        Download from igc_url property inside each entry in competitors list.
        Adds the file location as a property to the competitor

        :param download_progress: optional function to log the download progress.
        Function should have two inputs: number_of_downloads, total_number_of_flights
        :return:
        """

        # make directory if necessary
        if not os.path.exists(self._igc_directory):
            os.makedirs(self._igc_directory)

        flights_downloaded = 0
        for competitor in self.competitors:

            file_name = f'{competitor.competition_id}.igc'
            file_url = competitor.igc_url

            file_path = os.path.join(self._igc_directory, file_name)
            competitor.file_path = file_path
            while not os.path.exists(file_path):
                URLopener().retrieve(file_url, file_path)
                time.sleep(0.1)

            flights_downloaded += 1

            if download_progress is not None:
                download_progress(flights_downloaded, len(self.competitors))

    @abstractmethod
    def _get_competitors(self) -> List[Competitor]:
        """Fallback to base class"""

    @abstractmethod
    def _get_competition_day(self, competitors) -> CompetitionDay:
        """Fallback to base class"""
