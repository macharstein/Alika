# Phase 3 S8.1: movement style

Introduced in package **5.0.0**, manifest schema **lionsim-v5**. Packages 5.0–5.2 used the initial distribution; **5.4.0** applies the explicitly requested [bounded calibration](PHASE3_CALIBRATION_RESULTS.md). The accepted phase-two commit
`3de4f5a` is tagged **v4.5.0**. S8.1 adds trip-dependent walking style and its
tests. S8.2 is now documented in [path features](PATH_FEATURES.md); S8.3 evaluation and S8.4 figures are delivered; see their results for remaining acceptance failures.
Existing phase-two settings are unchanged. New paths change event timings and
sequences naturally; no event-state-machine rules or day-level latent sampling
were retuned. The old phase-two statistics are not measurements of v5.

## Frozen trip parameters

A trip starts when the lion leaves an activity for a committed goal outside its
current zone. Its bars are sampled before that minute's future car events.
Urgency, boredom and mood are clipped to 0–1 and held fixed until arrival or
interruption. Selecting an already occupied goal is a local activity, not a
zero-distance trip. IDs start at 1 within each independent day.

| Goal | Urgency at departure |
| --- | --- |
| Hunting ground, Feeding spot | Hunger |
| Shade, Waterhole | Temperature |
| Den | 1 − energy |
| Plain, Kopje, Road | 0.2 |

All new coefficients are in `movement_style` in [default_config.json](../default_config.json):

- Goal attraction: `(1 - movement.heading_persistence) * (0.25 + 2.0 * urgency)`.
- Turning-noise parameter: `randomness.walk_heading_sd_degrees * (clip(1 + 0.8 * boredom - 0.5 * urgency, 0.5, 2.0) + low_mood_increment)`, where the increment is 0.2 for mood <0.4 and zero otherwise.
- Speed multiplier: `0.85 + 0.4 * urgency`. It scales the existing state-dependent patrol pace; the existing patrol speed range still bounds the result.
- Detour probability: `2.0 * (boredom - 0.5) * (1 - urgency)` when boredom >0.5, zero otherwise. Probability is bounded to 0–1 for custom coefficients. One or two intermediate waypoints are drawn uniformly when a detour is selected.

At departure, the heading rotates toward the first waypoint (or goal) by `departure_alignment_weight * urgency` times the shortest angular difference; the default weight is 1. Position does not change, and continuing trips do not realign. The original 5.2.0 coefficients were attraction 0.6/0.8, speed 0.85/0.3, detour scale 0.7 without urgency suppression or departure alignment, and 0.4–1.0 km offsets. All phase-two settings remain unchanged.

The old turn integration scales requested-heading noise by
`1 - heading_persistence`. Trip attraction changes the correction toward the
bearing independently, retaining that noise scale. This prevents greater urgency
from inadvertently amplifying noise alongside the stronger pull toward the goal.
These parameters are frozen; the underlying physiological patrol pace can still
change as energy and temperature evolve.

## Detours and continuation

Intermediate anchors divide the departure-to-target chord evenly. Each waypoint
is 0.6–1.0 km sideways from it. Placement prefers a single side, tries both sides
with up to 32 bounded samples per waypoint, and prefers at least 0.05 km clearance
from unrelated zones. Source and goal zones are exempt from that exclusion.
Points outside the map are rejected, never clipped inward to hide a too-small
offset. If exclusion is unavoidable, use an in-map candidate. If neither side
fits, omit the waypoint. These geometric fallbacks can reduce the accepted count.
Only waypoint positions are checked for unrelated-zone clearance; connecting
segments may cross zones under the existing movement/event rules.

Waypoints are consumed within 0.05 km; each step stays within the speed bound,
with no teleportation. Arrival at the actual goal zone remains governed by the
existing hysteresis and may finish a trip before all planned waypoints are used.
Road goals use the existing nearest-boundary target, frozen at departure.

Traffic waits and short road responses keep the trip ID, starting bars and plan.
Their actual displacement contributes to realized straightness; established
traffic-response movement is unchanged. A different goal or non-travel activity
ends the trip as interrupted. Confirmed arrival ends it as arrived. Trips still
active at 05:00 end as day_end. A rest-origin road curiosity response keeps its
existing response logic; a committed return trip receives style when walking
resumes. Stalking, chases and local night play retain their old movement methods.

## Hidden-state fields

These columns are written only to `hidden_state.parquet` or `hidden_state.csv.gz`
through the existing atomic file writer. Daily JSON, reports, targets.csv, GPS
columns and PNG styling are unchanged. As before, normal runs retain hidden
files; stats/oracle modes require `--keep-files` to retain them.

| Columns | Meaning |
| --- | --- |
| `trip_id`, `trip_goal` | Daily trip identity and original committed goal. Null outside trips. |
| `trip_start_minute`, `trip_end_minute` | Minute offsets from 05:00. End is populated only on the final trip row and is the exclusive end of its recorded movement intervals. |
| `trip_urgency`, `trip_boredom`, `trip_mood` | Frozen departure state, distinct from the changing per-minute bars. |
| `trip_detour_count` | Accepted intermediate waypoint count, not the number of subsequently completed detours. |
| `trip_goal_attraction`, `trip_turn_sd_degrees`, `trip_speed_multiplier` | Frozen movement parameters applied during goal travel. |
| `trip_planned_straightness` | Departure-to-target chord divided by planned polyline length through accepted waypoints. |
| `trip_path_length_km` | Cumulative true displacement through the end of this minute, including traffic diversions and settling. |
| `trip_realized_straightness` | Departure-to-current chord divided by cumulative true path length, bounded to 0–1; null if no distance has been traveled. |
| `trip_status` | `in_progress`, followed by `arrived`, `interrupted` or `day_end` on the final row. |

Planned straightness is null for a zero-length plan. Realized straightness uses
true geometry for analysis only; observable GPS features belong to S8.2. Earlier
rows retain their prefix straightness rather than receiving a completed trip's
future value. Final status/end time are attached to the last trip interval when
the next boundary establishes arrival or interruption. Snapshots deep-copy the
trip, its waypoint progress, cumulative distance and diagnostic rows.

## Tests and scope

Original S8.1 verification: **212 tests passed in 41.10s** (historical, not calibration acceptance). All previous defaults and the plotting, report and event modules were compared against the v4.5.0 tag and remain unchanged.

[Tests](../tests/test_movement_style.py) cover urgency mapping, formulas, low mood,
configuration validation, detour probability and map-edge placement, path-length
ratio increasing with boredom/decreasing with urgency, speed direction, frozen
state during traffic waits, interruption, independent waypoint snapshots, exact
continuation, true-path diagnostic arithmetic, hidden-file isolation, unchanged
daily latents/traffic/report schedule, stalking/chase equivalence, seed reproduction
and v5 manifest/resume guards. Existing oracle, event, PNG and behavior suites
remain in place.

The directional test uses 40 fixed seeds per controlled condition with loose
mean-difference bounds. It holds the start/goal and within-trip physiology fixed;
it is not a substitute for the later 500-day correlation and guardrail evaluation.
One older twelve-day traffic test no longer assumes that this specific seed batch
contains a response-free day; it still requires multiple response days, ordinary
activity within each day, and valid event rules. No production parameters were
changed to make that test pass.

```sh
python -m pytest -x -q tests/test_movement_style.py tests/test_config.py
python -m pytest -x -q tests/test_oracle.py tests/test_road_dynamics.py tests/test_behaviour_scenarios.py
python -m pytest -q
```

Old seeds produce different data under v5. Resume rejects older schemas/versions;
use the v4.5.0 tag to reproduce the accepted phase-two baseline. No new ML
libraries or dependencies were added.
