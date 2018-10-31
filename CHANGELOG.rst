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
