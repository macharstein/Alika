UPDATE SPEC 3 for `lionsim`: STATE-DEPENDENT MOVEMENT STYLE (read with docs/UPDATE_SPEC.md; same header rules, PROGRESS.md, git checkpoints, --resume safety).

CONTEXT: version 4.5.0 (schema lionsim-v4) is calibrated and accepted. Do NOT retune existing statistics. Do not change tokens, schedule, day-level latents, event logic, the hunt cutoff, reports, or the look of the PNGs. Tag the current commit v4.5.0 first, then bump the schema to lionsim-v5 and note in README that old seeds give different data.

=== S8.1 MOVEMENT STYLE ===
For each trip (from leaving a behaviour until arrival at the goal), compute at trip start:
- urgency in 0..1: hunger for Hunting ground and Feeding spot goals; temperature for Shade and Waterhole goals; (1 - energy) for Den goals; 0.2 for boredom-driven goals (Plain, Kopje, Road)
- boredom and mood at trip start
Then set movement parameters (all coefficients in default_config.json under "movement_style"):
- goal_attraction = base * (0.6 + 0.8*urgency)
- turn_sd = base * clip(1 + 0.8*boredom - 0.5*urgency, 0.5, 2.0), plus 0.2 extra multiplier when mood < 0.4
- speed multiplier = 0.85 + 0.3*urgency
- detours: if boredom > 0.5, with probability 0.7*(boredom - 0.5) per trip insert 1 or 2 intermediate waypoints placed 0.4 to 1.0 km sideways from the straight line to the goal (coarse wandering that must stay visible above GPS noise); keep waypoints inside the map and outside other zones' exclusion where possible
Keep stalking and chase movement as they are. Log per trip in the hidden-state files: trip_id, goal, urgency, boredom, mood, detour_count, planned and realized straightness.

=== S8.2 OBSERVABLE PATH-SHAPE FEATURES ===
New module features_path.py, computed from the SMOOTHED OBSERVED GPS (5-minute moving average, never true positions) for the last completed trip and for the last 3 hours before each report: straightness (chord / path length), mean speed, circular variance of turning angles, maximum perpendicular distance from the chord (detour proxy), area covered (0.25 km grid cells). Add them as columns in targets.csv. Use only data up to the report time.

=== S8.3 TARGETS (500-day run, seed 42) ===
- corr(boredom at trip start, observed straightness) <= -0.35 over all trips
- corr(urgency, observed straightness) >= +0.30 over trips to Hunting ground, Waterhole, Shade, Den
- corr(urgency, mean trip speed) >= +0.25
- fraction of trips with a detour of at least 0.4 km: 0.10 to 0.30
- corr(straightness from smoothed observed path, straightness from true path) >= 0.85
- Baseline ladder: add L4 = L3 + path-shape cues (3 bins each: last-trip straightness, last-3h mean speed, last-trip detour yes/no), same interpolation as L3, 5-fold CV by day. Target: L4 at least 2% better than L3 on headline reports 1 to 5. If not reached, report which cue came closest and what was tried; do not overfit parameters just to pass.
GUARDRAILS (must still hold): walking <= 6.0 h/day; zone entries/day >= 7.0; mean walking speed <= 4.0 km/h; abandoned trips <= 1.0/day; all event rules pass; no target that passed in v4.5.0 turns FAIL (list every WARN/PASS change); oracle/L0 >= 0.20 (path shape must not make the world deterministic).

=== S8.4 FIGURE ===
Produce docs/style_examples.png: two panels on the same black-background map, one low-urgency high-boredom trip (wandering) and one high-urgency low-boredom trip (direct), white path over coloured zones, no extra text. Also render the usual PNGs for days 1 to 3.

=== S8.5 TESTS ===
Fixed seeds and loose tolerances: expected path-length ratio increases with boredom and decreases with urgency; detour waypoints stay inside the map; features use smoothed observed GPS only and ignore data after the report time; L4 runs and equals L3 when k is very large; schema bumped; same seed reproduces the same data.