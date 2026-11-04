UPDATE SPEC 4 for `lionsim`: L5 TEST (does the lion's current position and heading help predict the next zone?). Read with docs/UPDATE_SPEC.md (same header rules, PROGRESS.md, git checkpoints, --resume safety).

CONTEXT: simulator 5.4.0 (schema lionsim-v5) is frozen. Do NOT change simulator behaviour, event logic, parameters, or any existing statistic. This spec only adds analysis code: new path features at report time, a new baseline L5, controls, and a report. Use the minute-level observed GPS that is already saved. No ML libraries (counting models with numpy/pandas only).

=== A1. NEW FEATURES (features_heading.py) ===
Computed at each report time, using ONLY the SMOOTHED OBSERVED GPS (5-minute moving average) up to the report time. Never use true positions, hidden state, or anything after the report time.
- window W minutes (default 20) of recent motion
- displacement d = position(t) - position(t - W); speed_recent = |d| / W
- moving flag: |d| >= min_displacement_km (default 0.15), else stationary
- in_zone: current zone (by observed position) or "transit" if between zones
- implied_goal: if moving, compute the bearing of d, and for every zone except the current zone compute the bearing from the current position to the zone centre; implied_goal is the zone with the smallest angular difference, provided the difference is <= max_angle_deg (default 30), ties broken by nearest zone; otherwise "ambiguous". If stationary, implied_goal = "none".
- distance_to_implied_goal_km (null if none or ambiguous), binned into 2 bins (<= 1.5 km, > 1.5 km)
Put W, min_displacement_km, max_angle_deg under "heading_features" in default_config.json. Add the columns to targets.csv (never overwrite existing columns).

=== A2. BASELINE L5 ===
L5 = L3 plus the heading cue. Cell = (report index, implied_goal, moving flag). Use interpolation on top of L3: p_L5 = (n_cell_class + k * p_L3) / (n_cell + k), k configurable (default 20), cut points and counts from training days only, 5-fold CV by day, the same folds as L0 to L4, Laplace smoothing as before. Report for headline reports (1 to 5) and all reports, and per report index.

=== A3. CONTROLS AND DIAGNOSTICS ===
a) L5_shuffled: same as L5 but with the implied_goal values permuted among the examples of the same report index (training and test separately, fixed seed). This isolates the information gain from the cost of extra cells.
b) L5_truegoal (analysis only, clearly labelled LEAKY, never used as a model input): replace implied_goal by the lion's true current goal zone from the hidden-state files. This is an upper bound on what goal knowledge could add.
c) Subsets: report L3, L5, L5_shuffled, L5_truegoal separately for examples where the lion is moving at the report time and where it is stationary, and the fraction of examples in each.
d) Goal inference accuracy: among moving examples, how often implied_goal equals the true goal; also the confusion matrix (counts) of implied versus true goal.
e) Sensitivity: repeat L5 for W in {10, 20, 30} minutes. Label this table "post hoc"; the main result uses the declared defaults only.

=== A4. DECISION RULE (print in the report) ===
- relative improvement of L5 over L3 on headline reports (CV mean), and over L5_shuffled
- "WORTH INCLUDING" if L5 is at least 5% better than L3 AND at least 3% better than L5_shuffled
- "MARGINAL" if the improvement is between 2% and 5%
- "NOT HELPFUL" otherwise
Also state, in one sentence, how much of the gap between L3 and L5_truegoal the heading-based cue closes.

=== A5. RUN ===
Use a fresh seed that has not been used before (default 2026; if it exists in outputs, use 2027), 500 days, stats-only, chunks of 100 with --resume, no images, --workers 4. Write l5_report.json and l5_report.md to the run folder. Do not tune any parameter after seeing the results; if a defect is found, fix it, rerun once, and describe both runs.

=== A6. TESTS ===
Fixed seeds and loose tolerances: features use only data up to the report time (truncate the GPS after the report and check identical features); implied_goal is "none" when stationary; a synthetic straight walk toward a known zone gives that zone as implied_goal; L5 equals L3 when k is very large; the shuffle preserves marginal counts per report; folds are by day with no overlap; l5_truegoal is never imported by any model-facing export module; existing tests still pass.
