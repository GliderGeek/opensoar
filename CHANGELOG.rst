Changelog
==========

unreleased
------------------------
Added
~~~~~~
Changed
~~~~~~~~
Deprecated
~~~~~~~~~~~~
Removed
~~~~~~~~~
Fixed
~~~~~~~~
Security
~~~~~~~~~

v0.1.7
------------------------
Fixed
~~~~~~~~
* wrong version number in package
v0.1.6
------------------------
Changed
~~~~~~~~
* removed pinning from requirements to keep up to date
Fixed
~~~~~~~~
* obtaining IGC download URLs for soaringspot
* ranking and plane_model are nog longer switched in competition day

v0.1.5
------------------------
Changed
~~~~~~~~
* updated pygeodesy dependency

v0.1.4
------------------------
Fixed
~~~~~~~~
* relative urls for igc files using different base. (solves dev.soaringspot)

v0.1.3
------------------------
Fixed
~~~~~~~~
* fix bug in handling AAT task for scoringStrepla

v0.1.2
------------------------
* fix bug where moved_turnpoint caused failing task
* skip flights which cannot be parsed

v0.1.1
------------------------
* do not skip HC competitors
* add flag skip_failed_analyses in CompetitionDay.analyze_flights()

v0.1.0: initial release
------------------------
* competition module: CompetitionDay, Competitor, SoaringSpotDaily, StreplaDaily
* task module: AAT, RaceTask, Trip, Waypoint
* thermals module: FlightPhases, PySoarThermalDetector
