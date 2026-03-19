# Initial Implementation Plan

## Goal
Build a Python CLI using gpxpy to import GPX tracks, extract segments by time or location, move start and end anchor for loop routes, and export modified GPX output without rerouting.

## Core Constraints
- No rerouting.
- All operations must stay on the original point sequence.
- Output geometry is a subsequence or cyclic rotation of the original track.
- Optional cut-boundary interpolation is allowed only on existing adjacent edges.

## Commands
- extract
- shift-start
- move-loop-anchor

## Design Notes
- Support multi-track selection with --track-index.
- Preserve timestamps and elevation when present.
- Preserve key metadata where possible.
- Store ongoing design decisions in planning-docs/decision-log.md.
