# Phase 3 S8.3 evaluation

Package **5.2.0**, schema **lionsim-v5**, seed **42**. The 500-day evaluation is complete; the matched oracle is still in progress. The simulation distribution remains 5.0.0. No movement, event, schedule, latent, noise or plotting settings were changed in S8.3.

## Measurement definitions

Trip diagnostics use every hidden committed trip, including interrupted and day-end trips. Hidden start/end minutes align the initial bars with geometry; those boundaries and bars are analysis-only and never enter prediction features. GPS endpoints include both departure and the terminal boundary. Observed geometry uses the same causal trailing five-minute smoothing as S8.2, including past history before departure; true geometry uses unsmoothed true coordinates on identical boundaries. Mean trip speed includes waits. Undefined metrics remain null, and correlations report their valid pair counts.

The detour fraction is the fraction of **all trips** whose realized smoothed-observed maximum perpendicular distance from the endpoint chord is at least 0.4 km. Planned waypoint counts are not evidence of visible detours. Missing geometry is counted explicitly. Urgency–straightness includes Hunting ground, Waterhole, Shade and Den destinations; the other correlations use all destinations. Scalar per-trip records include day, ID, goal, status, start/end minutes and metrics, without retained trajectories.

Prediction features instead use the **observable inter-zone segmentation** documented in [PATH_FEATURES.md](PATH_FEATURES.md). That distinction can weaken learnability even when hidden-boundary correlations are strong.

## Fixed L4 experiment

L0–L3 are unchanged. L4 conditions on the L3 context plus last-trip straightness, last-three-hour mean speed and last-trip detour. Exactly three bins per cue include missingness:

| Cue | Missing | Low/no | High/yes |
| --- | --- | --- | --- |
| Last-trip straightness | no defined trip geometry | <0.9 | >=0.9 |
| Last-three-hour speed | no defined elapsed geometry | <1 km/h | >=1 km/h |
| Last-trip chord deviation | no defined trip geometry | <0.4 km | >=0.4 km |

`p_L4 = (cell class counts + 5 × p_L3) / (cell count + 5)`. Unseen cells equal L3. Large interpolation strength converges to L3. Five folds hold out whole days, using the same folds and report scopes at every level. Headline uses reports 1–5; final report is excluded. Means and population standard deviations are across folds.

The bins and k were fixed before evaluation. Single-cue variants (straightness, speed, detour) use the same folds and L3 prior. A no-path control repeats interpolation on the L3 cell without path information, measuring how much gain may arise from additional smoothing alone. These are diagnostics, not held-out model selection. No threshold search, coefficient fitting, feature selection or simulator retuning was performed.

## 500-day results

**37 PASS, 13 WARN, 1 FAIL**. This evaluation does **not** meet S8.3 acceptance. The hard failure is mean walking **6.0955 h/day >6.0**. All 500 days pass event invariants. There are **4028 committed trips**: 3712 arrived, 300 interrupted and 16 ended at the day boundary. Missing detour geometry: 0.

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| observed_true_path_ratio | **PASS** | 1.512156 | 1.6 |
| smoothed_rest_apparent_speed_kmh | **PASS** | 0.183534 | 0.8 |
| abandoned_trip_mean | **PASS** | 0.594000 | 1.0 |
| traffic_abandonment_share | **PASS** | 0.000000 | 0.25 |
| waterhole_day_fraction | **PASS** | 0.834000 | [0.8, 0.88] |
| zone_entries_per_day | **WARN** | 7.432000 | [8.0, 11.0] |
| zone_entry_share.Den | **WARN** | 0.026642 | [0.03, 0.35] |
| zone_entry_share.Shade | **PASS** | 0.167653 | [0.03, 0.35] |
| zone_entry_share.Kopje | **PASS** | 0.194564 | [0.03, 0.35] |
| zone_entry_share.Waterhole | **PASS** | 0.143972 | [0.03, 0.35] |
| zone_entry_share.Hunting ground | **PASS** | 0.093111 | [0.03, 0.35] |
| zone_entry_share.Feeding spot | **PASS** | 0.035522 | [0.03, 0.35] |
| zone_entry_share.Plain | **PASS** | 0.321851 | [0.03, 0.35] |
| zone_entry_share.Road | **WARN** | 0.016685 | [0.02, 0.05] |
| hunt_attempt_day_fraction | **PASS** | 0.650000 | [0.5, 0.7] |
| catch_day_fraction | **PASS** | 0.258000 | [0.2, 0.4] |
| road_entry_day_fraction | **PASS** | 0.124000 | [0.1, 0.18] |
| unique_sequence_fraction | **WARN** | 0.316000 | {'minimum_inclusive': 0.5} |
| top_five_sequence_share | **PASS** | 0.280000 | {'maximum_inclusive': 0.35} |
| mean_walking_speed_kmh | **PASS** | 3.412427 | [2.0, 4.0] |
| road_evening_fraction | **PASS** | 0.983871 | 0.6 |
| road_tourist_window_fraction | **PASS** | 0.016129 | 0.1 |
| road_tourist_correlation | **WARN** | -0.345827 | -0.35 |
| events_per_day | **WARN** | 18.300000 | [24.0, 32.0] |
| non_feast_late_entry_fraction | **PASS** | 0.916442 | 0.7 |
| feast_post_meal_entry_fraction | **PASS** | 0.000000 | 0.15 |
| end_of_day_report_6 | **WARN** | 0.320000 | [0.4, 0.6] |
| end_of_day_report_7 | **WARN** | 0.554000 | [0.6, 0.8] |
| prey_density_vs_kopje_dwell | **PASS** | 0.840458 | 0.4 |
| prey_density_vs_first_chase_time | **PASS** | -0.613093 | -0.3 |
| start_hunger_vs_wake_time | **PASS** | -0.316108 | -0.3 |
| heat_vs_shade_entry_time | **PASS** | -0.765307 | -0.4 |
| hours_per_behaviour.resting | **PASS** | 16.153633 | [16.0, 20.0] |
| hours_per_behaviour.walking | **WARN** | 6.095500 | [3.0, 5.0] |
| hours_per_behaviour.hunting | **PASS** | 0.785300 | [0.2, 3.0] |
| hours_per_behaviour.grooming | **PASS** | 0.401900 | [0.1, 2.5] |
| hours_per_behaviour.eating | **PASS** | 0.389767 | [0.0, 1.5] |
| hours_per_behaviour.drinking | **PASS** | 0.173900 | [0.0, 1.0] |
| event_invariants | **PASS** | 0.000000 | 0 |
| trip_boredom_straightness | **WARN** | -0.294315 | {'min': None, 'max': -0.35} |
| trip_urgency_straightness | **WARN** | 0.068929 | {'min': 0.3, 'max': None} |
| trip_urgency_speed | **PASS** | 0.329792 | {'min': 0.25, 'max': None} |
| trip_observed_true_straightness | **PASS** | 0.905918 | {'min': 0.85, 'max': None} |
| trip_detour_fraction | **WARN** | 0.069017 | {'min': 0.1, 'max': 0.3} |
| guardrail_walking_hours | **FAIL** | 6.095500 | {'min': None, 'max': 6.0} |
| guardrail_zone_entries | **PASS** | 7.432000 | {'min': 7.0, 'max': None} |
| guardrail_walking_speed | **PASS** | 3.412427 | {'min': None, 'max': 4.0} |
| guardrail_abandoned_trips | **PASS** | 0.594000 | {'min': None, 'max': 1.0} |
| guardrail_event_rules | **PASS** | 1.000000 | {'min': 1, 'max': None} |
| headline_l3_relative_improvement | **PASS** | 0.069509 | 0.03 |
| headline_l4_relative_improvement | **WARN** | -0.020815 | 0.02 |

| Trip correlation | Paired trips | Pearson r |
| --- | ---: | ---: |
| boredom_straightness | 4028 | -0.294315 |
| urgency_straightness | 1926 | 0.068929 |
| urgency_speed | 4028 | 0.329792 |
| observed_true_straightness | 4028 | 0.905918 |

### Counting losses

| Scope | L0 | L1 | L2 | L3 | L4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Headline | 1.759284 ± 0.021502 | 1.144494 ± 0.031713 | 0.649003 ± 0.024606 | 0.603892 ± 0.043267 | 0.616462 ± 0.056023 |
| All reports | 1.850572 ± 0.010816 | 1.235966 ± 0.029658 | 0.731646 ± 0.015762 | 0.693535 ± 0.028412 | 0.713280 ± 0.034509 |
| 1 | 1.609548 ± 0.021272 | 0.874228 ± 0.033304 | 0.183351 ± 0.015577 | 0.099819 ± 0.029093 | 0.095764 ± 0.041721 |
| 2 | 1.713426 ± 0.051681 | 1.088971 ± 0.058452 | 0.471089 ± 0.064451 | 0.425857 ± 0.083363 | 0.428754 ± 0.095039 |
| 3 | 1.416505 ± 0.031913 | 0.732722 ± 0.063290 | 0.732722 ± 0.063290 | 0.737170 ± 0.075154 | 0.743636 ± 0.076229 |
| 4 | 1.578117 ± 0.073497 | 1.315404 ± 0.056415 | 0.938490 ± 0.066696 | 0.886849 ± 0.068777 | 0.917087 ± 0.091468 |
| 5 | 2.478822 ± 0.036030 | 1.711144 ± 0.062311 | 0.919366 ± 0.035049 | 0.869766 ± 0.059935 | 0.897068 ± 0.069449 |
| 6 | 2.063774 ± 0.078962 | 1.604358 ± 0.050057 | 0.908241 ± 0.047459 | 0.876744 ± 0.049119 | 0.904694 ± 0.070599 |
| 7 | 2.093816 ± 0.036732 | 1.324936 ± 0.074223 | 0.968266 ± 0.043256 | 0.958537 ± 0.057627 | 1.005955 ± 0.063779 |

**L4 worsens headline loss by 2.0815%**, missing the required 2% improvement. The closest single cue is **detour**, which still worsens loss by 2.0112%. The combined cue is therefore not demonstrated useful for next-zone prediction in this experiment. This is distinct from showing that movement geometry reflects hidden drives.

| Diagnostic | Headline loss ± fold std | Relative improvement over L3 |
| --- | ---: | ---: |
| straightness | 0.617038 ± 0.056277 | -2.1769% |
| speed | 0.616477 ± 0.056908 | -2.0840% |
| detour | 0.616038 ± 0.056721 | -2.0112% |
| no_path_control | 0.617152 ± 0.057563 | -2.1958% |

L4 unseen-training-cell fraction: 0.084286. The no-path control also worsens loss; these diagnostics do not establish a path-information gain. All four diagnostics were declared before evaluation. No subsequent parameters were tried to force the target.

### Accepted v4.5.0 comparison

**No previously passing target becomes FAIL.** There is exactly one status change:

| Check | Before | After | Before value | After value |
| --- | --- | --- | ---: | ---: |
| end_of_day_report_7 | PASS | WARN | 0.61 | 0.554 |

All eight original WARN checks remain WARN. This status-comparison guardrail passing does not erase the new walking guardrail failure or the report-7 regression.

[Full statistics JSON](../outputs/phase3_s83_stats/run_20261103_141337/stats_report.json) · [Human report](../outputs/phase3_s83_stats/run_20261103_141337/stats_report.md) · [Reference comparison JSON](../outputs/phase3_s83_stats/run_20261103_141337/baseline_comparison.json) · [Archived accepted checks](phase2_v450_checks.json)

## Reproduce and resume

```sh
python -m lionsim.run --stats-only --stats-days 500 --seed 42 --chunk-size 100 --workers 4 --no-images --out outputs/phase3_s83_stats
python -m lionsim.run --resume outputs/phase3_s83_stats/run_20261103_141337 --chunk-size 100 --workers 4
python -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42 --chunk-size 20 --workers 6 --no-images --out outputs/phase3_s83_oracle
python -m lionsim.run --resume outputs/phase3_s83_oracle/run_20261103_141338 --chunk-size 20 --workers 6
python -m lionsim.trip_statistics outputs/phase3_s83_stats/run_20261103_141337 --reference docs/phase2_v450_checks.json
```

Repeat the resume command until each manifest is complete. The two runs intentionally differ in sample size; oracle comparisons use baselines fitted to its same 100 days, never the 500-day table. No PNGs were requested: S8.4 remains the next task.

## Configuration additions

Only new settings were added in S8.3; all prior defaults and simulation modules are unchanged from completed S8.2. Package version protects the new statistics checkpoint contract; statistics schema is `statistics-v3`, while the manifest stays v5.

| Setting | Value | Purpose |
| --- | ---: | --- |
| learnability.l4_interpolation_k | 5 | Strength of L3 prior |
| learnability.l4_straightness_cut | 0.9 | Fixed low/high straightness cut |
| learnability.l4_speed_cut_kmh | 1.0 | Fixed low/high three-hour speed cut |
| features_path.detour_threshold_km | 0.4 | Visible detour definition and L4 cut |
| targets.headline_l4_improvement_min | 0.02 | Relative improvement over L3 |
| targets.trip_boredom_straightness_max | -0.35 | All-trip correlation upper limit |
| targets.trip_urgency_straightness_min | 0.30 | Selected-goal correlation lower limit |
| targets.trip_urgency_speed_min | 0.25 | All-trip correlation lower limit |
| targets.trip_detour_fraction_range | [0.10, 0.30] | Realized detour fraction |
| targets.trip_observed_true_straightness_min | 0.85 | GPS geometry fidelity |
| targets.guardrail_walking_hours_max | 6.0 | Hard daily walking limit |
| targets.guardrail_entries_min | 7.0 | Hard mean entry minimum |
| targets.guardrail_speed_max_kmh | 4.0 | Hard pooled walking-speed limit |
| targets.guardrail_abandoned_max | 1.0 | Hard mean abandonment limit |
| targets.guardrail_oracle_l0_min | 0.20 | Hard minimum oracle/L0 in both scopes |

Old calibration ranges retain PASS/WARN semantics; unavailable statistics and hard guardrail violations are FAIL. The accepted-reference check requires no formerly passing target to become FAIL, and lists every status change, including PASS→WARN. It does not silently reinterpret WARN as PASS. The archived reference includes its original commit, seed, day count and source path.
