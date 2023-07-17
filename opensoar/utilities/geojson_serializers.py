from typing import List

from geojson import Point, LineString, Polygon, Feature, FeatureCollection
from opensoar.utilities.helper_functions import calculate_destination


def circle_polygon(lat, lng, radius):
    from shapely.geometry import Point as ShapelyPoint
    from pyproj import Transformer
    from shapely.ops import transform

    local_azimuthal_projection = "+proj=aeqd +R=6371000 +units=m +lat_0={} +lon_0={}".format(
        lat, lng
    )
    wgs84_to_aeqd = Transformer.from_proj('+proj=longlat +datum=WGS84 +no_defs', local_azimuthal_projection)
    aeqd_to_wgs84 = Transformer.from_proj(local_azimuthal_projection,  '+proj=longlat +datum=WGS84 +no_defs')
    # Get polygon with lat lon coordinates
    point_transformed = ShapelyPoint(wgs84_to_aeqd.transform(lng, lat))

    buffer = point_transformed.buffer(radius)
    circle = transform(aeqd_to_wgs84.transform, buffer)

    # todo: why nested list necessary?
    circle_coordinates = [[(lon, lat) for lon, lat in circle.exterior.coords]]
    polygon_feature = Feature(geometry=Polygon(circle_coordinates))
    return polygon_feature


def task_to_geojson_features(task) -> List[dict]:
    # TODO: have proper cutouts from sectors

    features = []
    task_line_coords = []
    for i, waypoint in enumerate(task.waypoints):
        lon = waypoint.longitude
        lat = waypoint.latitude
        task_line_coords.append((lon, lat))

        if waypoint.is_line:
            angle1 = (waypoint.orientation_angle + 90) % 360
            angle2 = (waypoint.orientation_angle - 90 + 360) % 360
            waypoint_fix = {"lon": waypoint.longitude, "lat": waypoint.latitude}
            end_of_line1 = calculate_destination(waypoint_fix, waypoint.r_max, angle1)
            end_of_line2 = calculate_destination(waypoint_fix, waypoint.r_max, angle2)
            line1 = LineString([(waypoint_fix['lon'], waypoint_fix['lat']), (end_of_line1['lon'], end_of_line1['lat'])])
            line2 = LineString([(waypoint_fix['lon'], waypoint_fix['lat']), (end_of_line2['lon'], end_of_line2['lat'])])
            features.append(Feature(geometry=line1))
            features.append(Feature(geometry=line2))
        else:
            features.append(circle_polygon(lat, lon, waypoint.r_max))
            if waypoint.r_min is not None:
                features.append(circle_polygon(lat, lon, waypoint.r_min))

            if waypoint.angle_max == 180:
                # do not plot lines when full circle
                continue

            # + 180 because orientation is outward
            angle1 = (waypoint.orientation_angle + 180 - waypoint.angle_max + 360) % 360
            angle2 = (waypoint.orientation_angle + 180 + waypoint.angle_max) % 360
            waypoint_fix = {"lon": waypoint.longitude, "lat": waypoint.latitude}
            end_of_line1 = calculate_destination(waypoint_fix, waypoint.r_max, angle1)
            end_of_line2 = calculate_destination(waypoint_fix, waypoint.r_max, angle2)

            line1 = LineString([(waypoint_fix['lon'], waypoint_fix['lat']), (end_of_line1['lon'], end_of_line1['lat'])])
            line2 = LineString([(waypoint_fix['lon'], waypoint_fix['lat']), (end_of_line2['lon'], end_of_line2['lat'])])
            features.append(Feature(geometry=line1))
            features.append(Feature(geometry=line2))

    # task polyline
    features.append(Feature(geometry=LineString(task_line_coords)))
    return features


def trip_to_geojson_features(trip, color: str) -> List[dict]:
    """
    :param trip:
    :param color: hex string with leading hashtag (e.g. "#062123")
    :return:
    """

    features = []

    for sector in trip.sector_fixes:
        sector_fix_coords = []
        for fix in sector:
            sector_fix_coords.append((fix['lon'], fix['lat']))
        features.append(Feature(geometry=LineString(sector_fix_coords), properties={"stroke": color}))

    for fix in trip.fixes:
        features.append(Feature(geometry=Point([fix['lon'], fix['lat']]), properties={"marker-color": color}))

    outlanding_fix = trip.outlanding_fix
    if outlanding_fix is not None:
        features.append(Feature(geometry=Point([outlanding_fix['lon'], outlanding_fix['lat']]), properties={"marker-color": color}))

    return features


def trace_to_geojson_features(trace) -> List[dict]:
    trace_line = Feature(geometry=LineString([(entry['lon'], entry['lat']) for entry in trace]))
    return [trace_line]


def generate_geojson(features) -> dict:
    """This dict can be written to .json file"""
    return FeatureCollection(features)
