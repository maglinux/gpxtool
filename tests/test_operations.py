from __future__ import annotations

from datetime import datetime, timedelta, timezone

import gpxpy.gpx

from gpx_tool.operations import (
    extract_by_distance,
    extract_by_indices,
    extract_by_time,
    shift_start,
)


def make_points(count: int = 6) -> list[gpxpy.gpx.GPXTrackPoint]:
    start = datetime(2026, 3, 19, 10, 0, tzinfo=timezone.utc)
    points: list[gpxpy.gpx.GPXTrackPoint] = []
    for i in range(count):
        points.append(
            gpxpy.gpx.GPXTrackPoint(
                latitude=52.0 + i * 0.001,
                longitude=13.0 + i * 0.001,
                elevation=100 + i,
                time=start + timedelta(minutes=i),
            )
        )
    return points


def test_extract_by_indices_forward() -> None:
    pts = make_points()
    out = extract_by_indices(pts, 1, 3)
    assert len(out) == 3
    assert out[0] is pts[1]
    assert out[-1] is pts[3]


def test_extract_by_indices_wrap() -> None:
    pts = make_points()
    out = extract_by_indices(pts, 4, 1, allow_wrap=True)
    assert len(out) == 4
    assert out[0] is pts[4]
    assert out[-1] is pts[1]


def test_extract_by_time() -> None:
    pts = make_points()
    out = extract_by_time(pts, pts[1].time, pts[3].time)
    assert len(out) == 3
    assert out[0] is pts[1]
    assert out[-1] is pts[3]


def test_extract_by_distance() -> None:
    pts = make_points()
    out = extract_by_distance(pts, 0, 200)
    assert len(out) >= 2


def test_shift_start_loop_anchor() -> None:
    pts = make_points()
    # Close the loop with duplicated start point.
    pts.append(
        gpxpy.gpx.GPXTrackPoint(
            latitude=pts[0].latitude,
            longitude=pts[0].longitude,
            elevation=pts[0].elevation,
            time=pts[0].time,
        )
    )

    anchor = pts[3]
    out = shift_start(pts, anchor.latitude, anchor.longitude, tolerance_meters=5.0, require_loop=True)

    assert out[0].latitude == anchor.latitude
    assert out[0].longitude == anchor.longitude
    assert out[0].latitude == out[-1].latitude
    assert out[0].longitude == out[-1].longitude


def test_move_loop_anchor_respects_configured_loop_threshold() -> None:
    pts = make_points(4)
    pts.append(
        gpxpy.gpx.GPXTrackPoint(
            latitude=pts[0].latitude,
            longitude=pts[0].longitude + 0.00001,
            elevation=pts[0].elevation,
            time=pts[0].time,
        )
    )

    anchor = pts[2]

    out = shift_start(
        pts,
        anchor.latitude,
        anchor.longitude,
        tolerance_meters=5.0,
        loop_threshold_meters=10.0,
        require_loop=True,
    )

    assert out[0].latitude == anchor.latitude
    assert out[0].longitude == anchor.longitude
