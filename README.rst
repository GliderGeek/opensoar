OpenSoar
=========
[![Build Status](https://travis-ci.org/GliderGeek/PySoar.svg?branch=master)](https://travis-ci.org/GliderGeek/PySoar)

The OpenSoar python library is meant to provide open source tooling for glider flight analysis. This may vary from 
thermal detection to competition scoring.

Reading in files with aerofiles
================================

![https://github.com/Turbo87/aerofiles](https://raw.githubusercontent.com/Turbo87/aerofiles/master/img/logo.png)

OpenSoar only performs analyses after the files have been read in. The [aerofiles library](https://github.com/Turbo87/aerofiles) provides the functionality
to read the files.

Example race task
=================

```python
from aerofiles.igc import Reader
from opensoar.competition.soaringspot import get_info_from_comment_lines
from opensoar.task.trip import Trip

with open('example.igc', 'r') as f:
    parsed_igc_file = Reader().read(f)

# example.igc comes from soaringspot and contains task inforamtion
task, _, _ = get_info_from_comment_lines(parsed_igc_file)
_, trace = parsed_igc_file['fix_records']

trip = Trip(task, trace)
task_distance_covered = sum(trip.distances)
```

Plan
====
A lot of functionality regarding analysis and competition scoring is currently present in the
[PySoar](https://github.com/GliderGeek/PySoar) project. It is the aim to take these functionalities, generalize them
and bundle them in this library.
