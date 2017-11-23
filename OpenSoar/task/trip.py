class Trip(object):

    def __init__(self, task, trace):

        # to be filled inside task.apply_rules
        self.fixes = list()
        self.start_fixes = list()
        self.outlanding_fix = None
        self.refined_start_time = None
        self.distances = list()

        task.apply_rules(trace, self)

    def outlanding_leg(self):
        if self.outlanded():
            return len(self.fixes) - 1
        else:
            return None

    def outlanded(self):
        return self.outlanding_fix is not None
