import requests
from bs4 import BeautifulSoup
import os
import time
import requests
import operator
import os
from abc import ABC, abstractmethod
from typing import List
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
        self._html_soup = None  # to be set when the page is evaluated

    @property
    def igc_directory(self):
        return self._igc_directory

    def set_igc_directory(self, target_directory, competition_name, plane_class, date):
        self._igc_directory = os.path.join(target_directory, competition_name, plane_class,
                                           date.strftime('%d-%m-%Y'))

    def _get_html_soup(self) -> BeautifulSoup:
        """
        Get a BeautifulSoup object from the URL.
        
        Returns:
            BeautifulSoup object containing the parsed HTML
        """
        
        if not self._html_soup:
            try:
                # Use requests with verify=True for secure connections
                # In production, you should ALWAYS verify SSL certificates
                response = requests.get(self.url, timeout=30)
                response.raise_for_status()  # Raise exception for 4XX/5XX status codes
                
                # Parse the HTML with BeautifulSoup
                self._html_soup = BeautifulSoup(response.text, "html.parser")
                
            except requests.exceptions.SSLError:
                # Only if absolutely necessary, you can disable verification
                # But this should be a last resort and logged as a security concern
                print("SSL verification failed. Attempting with verification disabled.")
                response = requests.get(self.url, verify=False, timeout=30)
                response.raise_for_status()
                self._html_soup = BeautifulSoup(response.text, "html.parser")
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching URL {self.url}: {e}")
                raise
                
        return self._html_soup

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
        
        Args:
            igc_url: URL to download the IGC file
            competition_id: Competition ID used to name the file
            
        Returns:
            str: Path to the downloaded file
        """
        
        # Make directory if necessary
        if not os.path.exists(self._igc_directory):
            os.makedirs(self._igc_directory)
            
        file_path = self.igc_file_path(competition_id)
        
        # Attempt to download the file
        max_retries = 3
        retry_count = 0
        
        while not os.path.exists(file_path) and retry_count < max_retries:
            try:
                response = requests.get(igc_url, timeout=30)
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                # Write the content to the file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
                # Verify file was created
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File was not created at {file_path}")
                    
            except (requests.exceptions.RequestException, FileNotFoundError) as e:
                print(f"Download attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                time.sleep(1)  # Longer delay between retries
        
        if not os.path.exists(file_path):
            raise RuntimeError(f"Failed to download file from {igc_url} after {max_retries} attempts")
        
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
