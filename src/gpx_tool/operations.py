from __future__ import annotations

from datetime import datetime
from typing import List

import gpxpy.gpx

from .core import cumulative_distances, is_closed_loop, nearest_point_index


def extract_by_indices(
    points: List[gpxpy.gpx.GPXTrackPoint],
    start_idx: int,
    end_idx: int,
    allow_wrap: bool = False,
) -> List[gpxpy.gpx.GPXTrackPoint]:
    if start_idx < 0 or end_idx < 0:
        raise ValueError("Start and end indices must be non-negative")
    if start_idx >= len(points) or end_idx >= len(points):
        raise ValueError("Start or end index is out of range")

    if start_idx <= end_idx:
        return list(points[start_idx : end_idx + 1])

    if not allow_wrap:
        raise ValueError("Start position is after end position. Use --allow-wrap for loop-like extraction.")

    return list(points[start_idx:]) + list(points[: end_idx + 1])


def extract_by_time(
    points: List[gpxpy.gpx.GPXTrackPoint],
    start_time: datetime,
    end_time: datetime,
) -> List[gpxpy.gpx.GPXTrackPoint]:
    if start_time >= end_time:
        raise ValueError("Start time must be earlier than end time")

    indexed_times = [(idx, point.time) for idx, point in enumerate(points) if point.time is not None]
    if len(indexed_times) != len(points):
        raise ValueError("Time extraction requires timestamps on all points")

    start_idx = None
    end_idx = None

    for idx, ts in indexed_times:
        if ts >= start_time and start_idx is None:
            start_idx = idx
        if ts <= end_time:
            end_idx = idx

    if start_idx is None:
        raise ValueError("Start time is after track end")
    if end_idx is None:
        raise ValueError("End time is before track start")
    if start_idx > end_idx:
        raise ValueError("Provided time range has no overlap with selected track")

    return list(points[start_idx : end_idx + 1])


def extract_by_distance(
    points: List[gpxpy.gpx.GPXTrackPoint],
    start_meters: float,
    end_meters: float,
) -> List[gpxpy.gpx.GPXTrackPoint]:
    if start_meters < 0 or end_meters < 0:
        raise ValueError("Distances must be >= 0")
    if start_meters >= end_meters:
        raise ValueError("Start distance must be smaller than end distance")

    distances = cumulative_distances(points)
    total = distances[-1]

    if end_meters > total:
        raise ValueError(f"End distance {end_meters:.2f}m exceeds track length {total:.2f}m")

    start_idx = 0
    end_idx = len(points) - 1

    for idx, value in enumerate(distances):
        if value >= start_meters:
            start_idx = idx
            break

    for idx, value in enumerate(distances):
        if value <= end_meters:
            end_idx = idx
        else:
            break

    if start_idx > end_idx:
        raise ValueError("Distance range has no overlap with selected track")

    return list(points[start_idx : end_idx + 1])


def extract_by_locations(
    points: List[gpxpy.gpx.GPXTrackPoint],
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    allow_wrap: bool = False,
) -> List[gpxpy.gpx.GPXTrackPoint]:
    start_idx, _ = nearest_point_index(points, start_lat, start_lon)
    end_idx, _ = nearest_point_index(points, end_lat, end_lon)
    return extract_by_indices(points, start_idx, end_idx, allow_wrap=allow_wrap)


def shift_start(
    points: List[gpxpy.gpx.GPXTrackPoint],
    anchor_lat: float,
    anchor_lon: float,
    tolerance_meters: float,
    loop_threshold_meters: float = 5.0,
    require_loop: bool = False,
) -> List[gpxpy.gpx.GPXTrackPoint]:
    """Rotate a track so the nearest existing point becomes the new start.

    `tolerance_meters` limits how far the requested anchor may be from the
    nearest recorded GPX point. `loop_threshold_meters` defines when the first
    and last point are close enough to treat the track as a loop.
    """
    if tolerance_meters <= 0:
        raise ValueError("Tolerance must be > 0")
    if loop_threshold_meters <= 0:
        raise ValueError("Loop threshold must be > 0")

    closed = is_closed_loop(points, threshold_meters=loop_threshold_meters)
    if require_loop and not closed:
        raise ValueError(
            "move-loop-anchor requires a closed loop track within the configured --loop-threshold"
        )

    work_points = list(points)
    had_duplicate_close_point = False

    if closed and len(work_points) >= 2:
        first = work_points[0]
        last = work_points[-1]
        # Some loop GPX files repeat the first point as the final point.
        # Drop that duplicate before rotation, then restore closure afterward.
        if first.latitude == last.latitude and first.longitude == last.longitude:
            had_duplicate_close_point = True
            work_points = work_points[:-1]

    idx, distance = nearest_point_index(work_points, anchor_lat, anchor_lon)
    if distance > tolerance_meters:
        raise ValueError(
            f"No track point within tolerance. Nearest point is {distance:.2f}m away; increase --tolerance."
        )

    # This is a pure point-order rotation, not a reroute. The output stays on
    # the original recorded geometry.
    rotated = list(work_points[idx:]) + list(work_points[:idx])

    if closed and had_duplicate_close_point:
        first = rotated[0]
        rotated.append(
            gpxpy.gpx.GPXTrackPoint(
                latitude=first.latitude,
                longitude=first.longitude,
                elevation=first.elevation,
                time=first.time,
            )
        )

    return rotated
