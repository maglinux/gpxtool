from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Iterable, List, Optional

import gpxpy
import gpxpy.gpx


@dataclass
class LoadedTrack:
    gpx: gpxpy.gpx.GPX
    track: gpxpy.gpx.GPXTrack
    points: List[gpxpy.gpx.GPXTrackPoint]


def parse_time(value: str) -> datetime:
    # Allow ISO timestamps with trailing Z.
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO timestamp: {value}") from exc


def parse_latlon(value: str) -> tuple[float, float]:
    try:
        lat_raw, lon_raw = value.split(",", 1)
        lat = float(lat_raw.strip())
        lon = float(lon_raw.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid coordinate '{value}'. Expected format: LAT,LON") from exc

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude out of range: {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude out of range: {lon}")
    return lat, lon


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius = 6371008.8
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2.0) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius * c


def load_track(input_path: Path, track_index: int = 0) -> LoadedTrack:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as handle:
        gpx = gpxpy.parse(handle)

    if not gpx.tracks:
        raise ValueError("GPX file has no tracks")

    if track_index < 0 or track_index >= len(gpx.tracks):
        raise ValueError(f"Track index {track_index} out of range. File contains {len(gpx.tracks)} track(s).")

    track = gpx.tracks[track_index]
    points = flatten_points(track)

    if len(points) < 2:
        raise ValueError("Selected track must contain at least 2 points")

    return LoadedTrack(gpx=gpx, track=track, points=points)


def flatten_points(track: gpxpy.gpx.GPXTrack) -> List[gpxpy.gpx.GPXTrackPoint]:
    points: List[gpxpy.gpx.GPXTrackPoint] = []
    for segment in track.segments:
        points.extend(segment.points)
    return points


def points_have_timestamps(points: Iterable[gpxpy.gpx.GPXTrackPoint]) -> bool:
    return all(point.time is not None for point in points)


def cumulative_distances(points: List[gpxpy.gpx.GPXTrackPoint]) -> List[float]:
    distances = [0.0]
    total = 0.0
    for idx in range(1, len(points)):
        prev = points[idx - 1]
        cur = points[idx]
        step = prev.distance_2d(cur) or 0.0
        total += step
        distances.append(total)
    return distances


def nearest_point_index(points: List[gpxpy.gpx.GPXTrackPoint], lat: float, lon: float) -> tuple[int, float]:
    nearest_idx = -1
    nearest_distance = float("inf")

    for idx, point in enumerate(points):
        distance = haversine_meters(lat, lon, point.latitude, point.longitude)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_idx = idx

    if nearest_idx < 0:
        raise ValueError("Could not locate nearest point")

    return nearest_idx, nearest_distance


def is_closed_loop(points: List[gpxpy.gpx.GPXTrackPoint], threshold_meters: float = 5.0) -> bool:
    """Return True when track start and end are within the loop threshold.

    The threshold is measured in meters and is intended to absorb normal GPS
    recording drift. A route does not need to end on the exact same coordinate
    as it started to count as a loop.
    """
    start = points[0]
    end = points[-1]
    return haversine_meters(start.latitude, start.longitude, end.latitude, end.longitude) <= threshold_meters


def clone_point(point: gpxpy.gpx.GPXTrackPoint) -> gpxpy.gpx.GPXTrackPoint:
    return gpxpy.gpx.GPXTrackPoint(
        latitude=point.latitude,
        longitude=point.longitude,
        elevation=point.elevation,
        time=point.time,
    )


def build_output_gpx(source: LoadedTrack, new_points: List[gpxpy.gpx.GPXTrackPoint]) -> gpxpy.gpx.GPX:
    if len(new_points) < 2:
        raise ValueError("Output must contain at least 2 points")

    output = gpxpy.gpx.GPX()
    output.name = source.gpx.name
    output.description = source.gpx.description
    output.author_name = source.gpx.author_name

    track = gpxpy.gpx.GPXTrack(name=source.track.name, description=source.track.description)
    segment = gpxpy.gpx.GPXTrackSegment()
    segment.points = [clone_point(p) for p in new_points]
    track.segments.append(segment)
    output.tracks.append(track)
    return output


def write_gpx(gpx: gpxpy.gpx.GPX, output_path: Path) -> None:
    xml = gpx.to_xml(version="1.1")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml, encoding="utf-8")

    # Validate by reparsing to ensure generated XML is valid GPX.
    with output_path.open("r", encoding="utf-8") as handle:
        gpxpy.parse(handle)
