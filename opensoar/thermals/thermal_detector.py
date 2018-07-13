from abc import ABC, abstractmethod


class ThermalDetector(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def analyse(self, trace):
        """Analyse a trace and return a list with the phases (cruise and thermal)"""
