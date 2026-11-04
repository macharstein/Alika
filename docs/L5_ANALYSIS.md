# Phase 4: observed heading and next-zone prediction

Simulator **5.4.0 / lionsim-v5 is frozen**. This update changes only analysis,
configuration validation for new analysis settings, and appended target exports.
All original target columns, statistics, simulator parameters and event logic remain
unchanged. Older 5.4.0 manifests without heading settings retain their original
CSV schema on resume. New runs identify the appended schema as `heading-v1`.

## Features and assumptions

`features_heading.heading_at_report` truncates observed `x_km`, `y_km` before
forward filling and trailing five-minute smoothing. No true coordinates, hidden
state, events or future fixes enter these features. Positions at t and t−W use
causal as-of fixes. W=20 minutes; movement requires displacement >=0.15 km.
`speed_recent` is **km/min**, not km/h. Insufficient history produces null geometry,
a false moving flag, goal `none` and `heading_window_complete=false`.

`in_zone` uses the current smoothed observed position, with `transit` outside all
zones. Moving trajectories imply the closest bearing within 30 degrees, excluding
the current zone; angle ties choose the nearer centre, then alphabetical name.
Stationary goals are `none`; unmatched moving bearings are `ambiguous`. Distances
to implied goals use zone **centres**, with fixed inclusive <=1.5 km and >1.5 km
bins; undefined distances/bins are null. Distance and speed are diagnostic exports;
the specified L5 cell uses only report index, implied goal and moving flag.

## Counting evaluation

Run `python -m lionsim.l5_analysis RUN_DIR` after simulation completes. It reads
saved minute GPS, hidden goals and targets, and writes `l5_report.json` and
`l5_report.md` without changing existing statistics. Five folds use the exact day
lists in the existing L0–L4 baseline. Counts use training days only. Existing L3
Laplace smoothing and history cuts remain unchanged; new heading cuts are fixed
in advance, not estimated on test examples.

L5 uses `(counts + k * p_L3)/(n + k)`, k=20, with the literal spec cell
`(report_index, implied_goal, moving)`. L5_shuffled permutes only implied goals
within each report index, independently for training and test, using NumPy
SeedSequence(shuffle_seed=2026, fold, split, report). It preserves goal marginals
and leaves moving flags unchanged. L5_truegoal replaces only the cue with the
exact hidden `goal` at the report minute (after transitions, before movement).
This **LEAKY analysis-only** control is isolated from model-facing exports and
never saved in targets.csv. Its counting loss is an empirical benchmark and may
not beat L3; if so, the gap-closed fraction is undefined. Otherwise the fraction
is reported without clipping, including negative values or values above 100%.

Losses are natural-log multiclass losses, mean and population SD across five folds.
Subset fractions use their corresponding headline/all/per-index denominator;
empty subsets have null losses and zero contributing folds. Goal inference
accuracy includes ambiguous moving cues as errors. Sensitivity W=10,20,30 is
labelled **post hoc**, never used to select the main result.

The declared headline rule is WORTH INCLUDING for >=5% gain over L3 **and** >=3%
over shuffled; MARGINAL for >=2% and <5% over L3; NOT HELPFUL otherwise. A gain
>=5% that fails the shuffle condition is therefore NOT HELPFUL.

## Reproduce the fresh-seed experiment

```sh
python -m lionsim.run --stats-only --stats-days 500 --seed 2026 --keep-files --no-images --workers 4 --chunk-size 100 --out outputs/phase4_l5
python -m lionsim.run --resume RUN_DIR --workers 4 --chunk-size 100
# Repeat the resume command three more times to complete 500 days.
python -m lionsim.l5_analysis RUN_DIR
```

Use 2027 if an existing output manifest already used seed 2026. `--keep-files` is
necessary even in stats-only mode because this analysis requires the already-saved
minute tables. No images are produced. Simulation checkpoints survive interruptions;
analysis also caches one day at a time and skips matching input hashes on rerun.
`l5_analysis_checkpoints/` contains explicitly marked **LEAKY analysis material**,
not training features. Report JSON records input hashes, settings and day folds.
Do not tune after reading results; any post-result defect correction must disclose
both runs and use at most the one permitted rerun.
