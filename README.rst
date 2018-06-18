OpenSoar
========

.. image:: https://travis-ci.org/GliderGeek/PySoar.svg?branch=master
    :target: https://travis-ci.org/GliderGeek/PySoar
    :alt: Build status

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
    
