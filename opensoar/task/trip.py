from opensoar.utilities.helper_functions import seconds_time_difference


class Trip:
    """
    Realised
    """

    def __init__(self, task, trace):

        task_result = task.apply_rules(trace)

        self.fixes = task_result[0]
        self.refined_start_time = task_result[1]
        self.outlanding_fix = task_result[2]
        self.distances = task_result[3]
        self.finish_time = task_result[4]

    def completed_legs(self):
        return len(self.fixes) - 1

    def started_legs(self):
        if self.outlanded():
            return len(self.fixes)
        else:
            return len(self.fixes) - 1

    def outlanding_leg(self):
        if self.outlanded():
            return len(self.fixes) - 1
        else:
            return None

    def outlanded(self):
        return self.outlanding_fix is not None

    def fix_on_leg(self, fix, leg):
        """
        Return whether fix takes place within certain leg, excluding the boundaries
        :param fix: 
        :param leg: 
        :return: 
        """
        larger_than_minimum = not self.fix_before_leg(fix, leg)
        smaller_than_maximum = not self.fix_after_leg(fix, leg)
        return larger_than_minimum and smaller_than_maximum

    def fix_before_leg(self, fix, leg):
        return seconds_time_difference(fix['time'], self.fixes[leg]['time']) >= 0

    def fix_after_leg(self, fix, leg):
        if leg + 1 <= self.completed_legs():
            return seconds_time_difference(self.fixes[leg + 1]['time'], fix['time']) >= 0
        elif self.outlanded() and leg == self.outlanding_leg():
            return False
        else:  # leg > self.completed_legs() + 1
            raise ValueError('Leg not started')