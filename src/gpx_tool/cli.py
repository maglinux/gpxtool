from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .core import build_output_gpx, load_track, parse_latlon, parse_time, points_have_timestamps, write_gpx
from .operations import extract_by_distance, extract_by_locations, extract_by_time, shift_start


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpx-tool",
        description="GPX command-line tool for cut/rotate operations without rerouting",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extract a segment from an input track")
    extract.add_argument("--input", "-i", required=True, help="Input GPX file")
    extract.add_argument("--output", "-o", required=True, help="Output GPX file")
    extract.add_argument("--track-index", type=int, default=0, help="Track index in GPX file (default: 0)")
    extract.add_argument("--allow-wrap", action="store_true", help="Allow extraction that wraps end-to-start")

    extract_mode = extract.add_mutually_exclusive_group(required=True)
    extract_mode.add_argument("--by-time", action="store_true", help="Extract using start/end timestamps")
    extract_mode.add_argument("--by-distance", action="store_true", help="Extract using start/end distance meters")
    extract_mode.add_argument("--by-location", action="store_true", help="Extract using start/end nearest locations")

    extract.add_argument("--start-time", help="ISO timestamp (for --by-time)")
    extract.add_argument("--end-time", help="ISO timestamp (for --by-time)")

    extract.add_argument("--start-distance", type=float, help="Start distance in meters (for --by-distance)")
    extract.add_argument("--end-distance", type=float, help="End distance in meters (for --by-distance)")

    extract.add_argument("--start-location", help="LAT,LON (for --by-location)")
    extract.add_argument("--end-location", help="LAT,LON (for --by-location)")

    shift = subparsers.add_parser("shift-start", help="Shift track start to nearest anchor point")
    shift.add_argument("--input", "-i", required=True, help="Input GPX file")
    shift.add_argument("--output", "-o", required=True, help="Output GPX file")
    shift.add_argument("--track-index", type=int, default=0, help="Track index in GPX file (default: 0)")
    shift.add_argument("--anchor-lat", type=float, required=True, help="Anchor latitude")
    shift.add_argument("--anchor-lon", type=float, required=True, help="Anchor longitude")
    shift.add_argument("--tolerance", type=float, default=10.0, help="Max nearest-point distance in meters")
    shift.add_argument(
        "--loop-threshold",
        type=float,
        default=5.0,
        help="Distance in meters used to decide whether the first and last point form a loop (default: 5)",
    )

    loop_anchor = subparsers.add_parser(
        "move-loop-anchor",
        help="Move start/end anchor for closed loop tracks only",
    )
    loop_anchor.add_argument("--input", "-i", required=True, help="Input GPX file")
    loop_anchor.add_argument("--output", "-o", required=True, help="Output GPX file")
    loop_anchor.add_argument("--track-index", type=int, default=0, help="Track index in GPX file (default: 0)")
    loop_anchor.add_argument("--anchor-lat", type=float, required=True, help="Anchor latitude")
    loop_anchor.add_argument("--anchor-lon", type=float, required=True, help="Anchor longitude")
    loop_anchor.add_argument("--tolerance", type=float, default=10.0, help="Max nearest-point distance in meters")
    loop_anchor.add_argument(
        "--loop-threshold",
        type=float,
        default=5.0,
        help="Distance in meters used to decide whether the first and last point form a loop (default: 5)",
    )

    return parser


def _run_extract(args: argparse.Namespace) -> None:
    loaded = load_track(Path(args.input), track_index=args.track_index)

    if args.by_time:
        if not args.start_time or not args.end_time:
            raise ValueError("--by-time requires --start-time and --end-time")
        if not points_have_timestamps(loaded.points):
            raise ValueError(
                "Track has missing timestamps. Use --by-distance with --start-distance/--end-distance as fallback."
            )
        start = parse_time(args.start_time)
        end = parse_time(args.end_time)
        selected = extract_by_time(loaded.points, start, end)

    elif args.by_distance:
        if args.start_distance is None or args.end_distance is None:
            raise ValueError("--by-distance requires --start-distance and --end-distance")
        selected = extract_by_distance(loaded.points, args.start_distance, args.end_distance)

    elif args.by_location:
        if not args.start_location or not args.end_location:
            raise ValueError("--by-location requires --start-location and --end-location")
        start_lat, start_lon = parse_latlon(args.start_location)
        end_lat, end_lon = parse_latlon(args.end_location)
        selected = extract_by_locations(
            loaded.points,
            start_lat,
            start_lon,
            end_lat,
            end_lon,
            allow_wrap=args.allow_wrap,
        )

    else:
        raise ValueError("No extraction mode selected")

    out_gpx = build_output_gpx(loaded, selected)
    write_gpx(out_gpx, Path(args.output))

    print(f"Extracted {len(selected)} point(s) to {args.output}")


def _run_shift(args: argparse.Namespace, require_loop: bool) -> None:
    loaded = load_track(Path(args.input), track_index=args.track_index)
    shifted = shift_start(
        loaded.points,
        anchor_lat=args.anchor_lat,
        anchor_lon=args.anchor_lon,
        tolerance_meters=args.tolerance,
        loop_threshold_meters=args.loop_threshold,
        require_loop=require_loop,
    )
    out_gpx = build_output_gpx(loaded, shifted)
    write_gpx(out_gpx, Path(args.output))

    mode = "loop-anchor" if require_loop else "shift-start"
    print(f"Applied {mode} with {len(shifted)} point(s) written to {args.output}")


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "extract":
            _run_extract(args)
        elif args.command == "shift-start":
            _run_shift(args, require_loop=False)
        elif args.command == "move-loop-anchor":
            _run_shift(args, require_loop=True)
        else:
            parser.error("Unknown command")
    except Exception as exc:  # noqa: BLE001
        parser.exit(status=2, message=f"Error: {exc}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
