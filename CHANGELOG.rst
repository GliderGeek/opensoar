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

v2.0.1 - 2025/03/07
------------------------
Added
~~~~~~~~
* Include pilot name and plane in soaringspot competitor info

Changed
~~~~~~~~
* Optionally include DNF and DNS soaringspot competitor info

v2.0.0 - 2025/03/07
------------------------
Fixed
~~~~~~~~
* IGC files with duplicate fixes no longer cause errors

Changed
~~~~~~~~
* Using timezone aware fixes throughout the library
* Input times are now timezone aware
* Output times are now timezone aware

Removed
~~~~~~~~~
* Several time helper functions `utilities.helper_functions` 


v1.1.3 - 2024/08/18
------------------------
Fixed
~~~~~~~~
* Fixed starttime UTC correction with negative timezone values

v1.1.2 - 2024/02/04
------------------------
Fixed
~~~~~~~~
* allow for soaringspot files without task info
* allow for soaring competitors with empty competition ID

v1.1.1 - 2023/08/25
------------------------
Added
~~~~~~
* extra geojson serializer for trip
Fixed
~~~~~~~~
* automatic sector orientations should point inward

v1.1.0 - 2023/05/20
------------------------
Added
~~~~~~
* geojson serializers
Fixed
~~~~~~~~
* AAT inside sector determination

v1.0.0 - 2023/01/09
------------------------
Changed
~~~~~~~~
* Replace TravisCI with github actions for automated tests and publish
* Replace pygeodesy with pyproj for speed-up
Removed
~~~~~~~~~
* StreplaDaily support: site no longer online
* `calculate_distance` and `calculate_bearing` (replaced by `calculate_distance_bearing`)
Fixed
~~~~~~~~
* is -> == on literals

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
