# gpx-tool

Python command-line tool for GPX track modifications based on gpxpy.

## What it does
- Imports GPX tracks.
- Extracts segments by time, distance, or nearest locations.
- Shifts start for any route.
- Moves start/end anchor for loop routes with a dedicated command.
- Exports the result to a new GPX file.

## No-reroute guarantee
All operations stay on the original route point sequence.
The tool does not use map matching, road snapping, or external routing.

## Install

```bash
pip install -e .
```

## Terminal usage on MacOS or Linux

From a terminal in the project folder:

```bash
cd /path/to/gpx-tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Run the CLI help:

```bash
gpx-tool --help
```

If your shell cannot find `gpx-tool`, run it via Python module mode:

```bash
python -m gpx_tool.cli --help
```

Typical command flow:

```bash
# 1) Extract by time
gpx-tool extract \
  --input route.gpx \
  --output segment.gpx \
  --by-time \
  --start-time 2026-03-19T08:00:00+00:00 \
  --end-time 2026-03-19T09:00:00+00:00

# 2) Shift start for any track shape
gpx-tool shift-start \
  --input route.gpx \
  --output shifted.gpx \
  --anchor-lat 52.5200 \
  --anchor-lon 13.4050 \
  --tolerance 15

# 3) Move loop anchor for closed loops
gpx-tool move-loop-anchor \
  --input loop.gpx \
  --output loop-shifted.gpx \
  --anchor-lat 52.5200 \
  --anchor-lon 13.4050 \
  --tolerance 15
```

Deactivate the virtual environment when done:

```bash
deactivate
```

## Commands

### shift-start vs move-loop-anchor

- `shift-start` works for any track shape (open or closed). It rotates the track so the nearest point to your anchor becomes the first point.
- `move-loop-anchor` is loop-only. It requires a closed track and is intended to move the loop's start/end marker together to a new anchor position.
- If your GPX is not a closed loop, use `shift-start`.
- `--tolerance` is measured in meters. It defines the maximum allowed distance between your requested anchor location and the nearest existing GPX point.
- A track is treated as a loop when the first and last GPX points are within 5 meters of each other by default.
- You can change that rule with `--loop-threshold`, which is also measured in meters.
- Both modes follow the no-reroute guarantee: they only reorder existing points and do not generate a new path.

### Extract by time

```bash
gpx-tool extract \
  --input route.gpx \
  --output segment.gpx \
  --by-time \
  --start-time 2026-03-19T08:00:00+00:00 \
  --end-time 2026-03-19T09:00:00+00:00
```

### Extract by distance

```bash
gpx-tool extract \
  --input route.gpx \
  --output segment.gpx \
  --by-distance \
  --start-distance 500 \
  --end-distance 4500
```

### Extract by location

```bash
gpx-tool extract \
  --input route.gpx \
  --output segment.gpx \
  --by-location \
  --start-location 52.5172,13.3929 \
  --end-location 52.5159,13.3777
```

### Shift route start

```bash
gpx-tool shift-start \
  --input route.gpx \
  --output shifted.gpx \
  --anchor-lat 52.5200 \
  --anchor-lon 13.4050 \
  --loop-threshold 5 \
  --tolerance 15
```

### Move loop anchor (closed routes)

```bash
gpx-tool move-loop-anchor \
  --input loop.gpx \
  --output loop-shifted.gpx \
  --anchor-lat 52.5200 \
  --anchor-lon 13.4050 \
  --loop-threshold 5 \
  --tolerance 15
```

## Notes
- Use --track-index for GPX files that contain multiple tracks.
- Time extraction requires timestamps on all selected points.
- If timestamps are missing, use distance extraction as fallback.
- `--tolerance 15` means the tool accepts a nearest existing track point up to 15 meters away from the anchor you provided.
- If the nearest point is farther away than the tolerance, the command fails instead of guessing or rerouting.
- `--loop-threshold 5` means a route counts as a loop if its first and last points are no more than 5 meters apart.
