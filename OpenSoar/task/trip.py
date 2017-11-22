class Trip(object):

    def __init__(self, task, trace, enl_indices):
        # why enl_indices? isn't this captured inside aerofiles highlevel reader?
        # todo: check in aerofiles with enl plane where enl info in stored
        # todo: determine information flow of these values. probably not enl_indices


        """
        :param task: 
        :param trace: 
        :param enl_indices: 
        """

        # to be filled inside task.apply_rules
        self.fixes = list()
        self.start_fixes = list()
        self.outlanding_fix = None
        self.refined_start_time = None
        self.distances = list()

        task.apply_rules(trace, self, enl_indices)

    def outlanding_leg(self):
        if self.outlanded():
            return len(self.fixes) - 1
        else:
            return None

    def outlanded(self):
        return self.outlanding_fix is not None
