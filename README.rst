OpenSoar
========

.. image:: https://img.shields.io/pypi/v/opensoar.svg
    :target: https://pypi.org/project/opensoar/
    :alt: pypi version and link
    
.. image:: https://readthedocs.org/projects/opensoar/badge/?version=latest
    :target: http://opensoar.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

The OpenSoar python library is meant to provide open source tooling for glider flight analysis. This may vary from 
thermal detection to competition scoring.

Installation
=============
::

    pip install opensoar


Reading in files with aerofiles
================================

.. image:: https://raw.githubusercontent.com/Turbo87/aerofiles/master/img/logo.png
    :target: https://github.com/Turbo87/aerofiles

OpenSoar only performs analyses after the files have been read in. The `aerofiles library <https://github.com/Turbo87/aerofiles>`_ provides the functionality
to read the files.

Example race task
==================
::

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
    

Releasing
==========

- add version number in changelog
- change `__version__` in opensoar/version.py
- merge to master
- push tag, ci publishes to pypi
