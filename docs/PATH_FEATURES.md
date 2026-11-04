# Phase 3 S8.2: observed path-shape features

Package **5.1.0**, schema **lionsim-v5**. This step appends ten columns to
`targets.csv` and its compact day checkpoints. Movement and event generation
remain the 5.0.0 distribution. Daily JSON, report payloads, GPS tables and PNG
appearance do not change. L0–L3 still ignore these columns; L4 belongs to S8.3.

## Inputs and causality

[features_path.py](../lionsim/features_path.py) accepts observed `t_iso`, `x_km`
and `y_km`, public entry events, report time and configuration. It does not read
true coordinates, hidden trip IDs/boundaries, goal states or day-level latents.

For each report, discard fixes after its timestamp before filling missing
coordinates and computing a trailing **five-minute moving average**. The current
fix is included and the fix exactly five minutes earlier is excluded: with the
simulator's one-minute cadence, this is the current fix plus four previous fixes.
Initial warmup uses the available prefix. Missing coordinates are forward-filled
only from earlier fixes; leading missing coordinates remain unavailable. The
simulation already exports finite, forward-filled observed fixes in ordinary use.
Duplicate observed timestamps are rejected. Fixes exactly at report time are
allowed; no future fix is used for interpolation.

The recent-window scope selects smoothed fixes from `[report time − 180 minutes,
report time]`. A smoothed fix at the window's start may use earlier history from
its own trailing five minutes; it never uses future data. Mean speed uses the
actual elapsed time between available first and last fixes, including pauses.

## Observable completed trips

A hidden committed trip has information unavailable to a future predictor.
Instead, the last-trip scope uses an **observable inter-zone trip approximation**:

1. The initial source zone comes from the first smoothed observed fix and the map.
   Subsequent source zones come from public ENTER events.
2. After the source has appeared within its zone or departure margin, detect two
   consecutive minute fixes more than 0.05 km outside it. The trip starts at the
   fix immediately preceding that confirmed departure. If the initial fix was
   unzoned, use displacement from that initial fix for the first departure.
3. The next public entry into a different zone completes the trip. Its end is the
   last GPS fix at or before the event timestamp. The event itself must already
   be visible at report time.
4. Use the most recently completed observable trip. An ongoing trip, traffic
   wait or unzoned pause cannot replace it without a new observed entry.

Smoothing can lag behind an entry. Requiring the source to be observed first
prevents that lag from falsely starting the next departure. A brief visit that
never appears in the smoothed source zone may have no measurable departure.
An incidental intermediate-zone entry can split a hidden committed trip into
observable segments. These are deliberate limits of an observable input feature,
not claims that hidden and observable segmentation are identical. Ground-truth
trip correlations in S8.3 will need to distinguish this approximation explicitly.

## CSV columns

Each metric is emitted twice, with prefixes `last_trip_` and `last_3h_`:

| Metric suffix | Definition / units |
| --- | --- |
| `straightness` | Start-to-end chord length divided by accumulated smoothed path length, in 0–1. |
| `mean_speed_kmh` | Smoothed path length / actual elapsed hours, including stops. |
| `turn_circular_variance` | `1 − abs(mean(exp(i * turning_angle)))`, in 0–1, across consecutive nonzero displacement headings. |
| `max_perpendicular_distance_km` | Maximum perpendicular distance to the infinite line containing the start-to-end chord. If the chord has zero length, use maximum radial distance from its point. |
| `area_covered_km2` | Number of distinct occupied 0.25 × 0.25 km cells multiplied by 0.0625 km². Cells are aligned to map origin, use sampled smoothed fixes, and are not clipped using true positions. |

All original target columns keep their order; these ten follow them. Report 8
still has no target row. Missing metrics are **null in checkpoints and blank in
CSV**, never sentinel numbers:

- No completed trip: all five last-trip values are null.
- Empty path: all metrics are null.
- One fix: occupied area is defined; motion/turn/chord metrics are null.
- Stationary path with at least two fixes: speed and deviation are zero, area is
  one cell; straightness and turning variance are undefined/null.
- A moving closed path has straightness zero, rather than an undefined ratio.
- Turning variance requires at least two nonzero displacement vectors. It
  measures variability of turning angles, not their mean magnitude.

## Settings and compatibility

Only these five new `features_path` settings were added; no simulation knobs
changed:

| Setting | Default |
| --- | ---: |
| `smoothing_minutes` | 5 |
| `window_minutes` | 180 |
| `grid_cell_km` | 0.25 |
| `departure_margin_km` | 0.05 |
| `departure_confirmation_minutes` | 2 |

The `last_3h_` prefix describes the default 180-minute window; an explicit window
override changes its extent and is recorded in the manifest configuration.

Package 5.1.0 prevents resuming older versions with incomplete target columns.
Within a run, missing feature keys, invalid numeric values or missing report rows
cause only the affected day to regenerate. Valid nulls are retained. Atomic
checkpoint/CSV writing and bounded day chunks remain unchanged.

## Verification

Full suite: **224 tests passed in 56.13s**. The targeted feature/resume/oracle
suite passed 25 tests. Existing settings and simulator/style/report/event/PNG
modules were compared against the completed S8.1 commit and are unchanged.

The [feature tests](../tests/test_features_path.py) check known straight, bent,
closed and stationary geometry; trailing smoothing; report-time boundaries;
future-coordinate/event mutation and truncation; true/hidden/latent independence;
observable departure/completion; three-hour selection; invalid settings; and
CSV equality across uninterrupted, resumed and multi-worker runs, including
repair of a missing feature in one checkpoint.

```sh
python -m pytest -x -q tests/test_features_path.py tests/test_config.py
python -m pytest -x -q tests/test_features_path.py tests/test_resume.py tests/test_oracle.py
python -m pytest -q
```

S8.3 has been [measured](PHASE3_S83_RESULTS.md), S8.4 [figures](STYLE_EXAMPLES.md) are delivered, and the later [5.4.0 calibration](PHASE3_CALIBRATION_RESULTS.md) retains these exact feature definitions. L4 now fits per-report numeric tertiles from training days only, with explicit missingness; feature extraction itself is unchanged.
