# Phase-three calibration, package 5.4.0

The user requested addressing the S8.3 failures. This bounded attempt changes phase-three movement and L4 settings only. Acceptance thresholds, all phase-two behavior settings, event vocabulary/rules, schedule, latent sampling, GPS noise and feature definitions remain fixed. The 500-day seed-42 confirmation and matched oracle are complete. The confirmation fixes two failures but leaves three targets unmet.

## Changes and rationale

- Stronger urgency-dependent steering: attraction becomes `(1 - heading_persistence) * (0.25 + 2.0 * urgency)`.
- Discretionary detours yield to urgent goals: probability becomes `clip(2 * (boredom - 0.5) * (1 - urgency), 0, 1)`.
- At a new trip, rotate the inherited heading toward the first waypoint/goal by urgency times the shortest angular difference. There is no position jump or repeated realignment of active trips.
- Planned sideways offsets increase from 0.4–1.0 km to 0.6–1.0 km, improving visibility under unchanged five-minute observed-GPS smoothing.
- Speed multiplier becomes `0.85 + 0.4 * urgency`, retaining the existing 2–4 km/h cap. Larger base-speed candidates were rejected because saturation erased the urgency gradient.
- L4 fits straightness/speed tertiles separately for each report from training days only. Three numeric bins plus explicit missingness replace two numeric bins plus missingness; detour remains missing/no/yes at 0.4 km. Increase the L3 prior strength from 5 to 20 to reduce sparse-cell overconfidence. L0–L3 and target labels are unchanged.

Training bins use neither labels nor held-out observations. Folds report their exact cutpoints. Missing CSV fields remain missing; they are never imputed from hidden state. The old fixed-bin mode remains selectable for comparison.

## Declared experiments and limitations

[Initial plan and recorded extensions](calibration_phase3/PLAN.md) · [Candidate configurations and all check values](calibration_phase3/selection_results.json) · [L4 diagnostic folds](calibration_phase3/l4_training_bins_diagnostic.json)

The initial plan declared three candidates (A/B/C), tested on 100 seed-137 days. All failed the urgency/speed target after hitting the speed cap. A fourth, D, restored the original speed intercept; it still failed walking and several movement targets. A final E revision addressed short-trip heading carryover and detour visibility. Those two extensions are documented departures from the initial candidate cap, not a claim that every choice was predeclared. E was then checked on independent seed 271 before freezing package 5.4.0. No geometry or acceptance thresholds will be changed after examining seed-42 confirmation.

L4 was not used to select movement settings. The training-tertile/k=20 variant was declared before its seed-137 diagnostic; no threshold/k grid search was performed. The source seed-42 dataset had already been inspected during diagnosis, so confirmation should not be presented as a pristine never-seen benchmark. A new independent validation seed was included for that reason.

| Candidate | Seed | Walking h/day | Boredom/straightness | Urgency/straightness | Urgency/speed | Visible detour fraction | Observed/true straightness | L4 relative improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 137 | 6.041000 | -0.289775 | 0.065833 | 0.397681 | 0.059720 | 0.914589 | 0.012629 |
| A | 137 | 5.608167 | -0.308746 | 0.285810 | -0.083354 | 0.093674 | 0.945113 | -0.005848 |
| B | 137 | 5.655333 | -0.357697 | 0.246485 | -0.062160 | 0.107186 | 0.956227 | -0.006029 |
| C | 137 | 5.577000 | -0.321356 | 0.334676 | -0.190430 | 0.133742 | 0.956195 | -0.040167 |
| D_seed137 | 137 | 6.073167 | -0.363837 | 0.159189 | 0.238632 | 0.094945 | 0.943129 | -0.022508 |
| E_seed137 | 137 | 5.906500 | -0.370356 | 0.138526 | 0.317672 | 0.100376 | 0.932199 | -0.010177 |
| E_seed271 | 271 | 5.755167 | -0.303375 | 0.165122 | 0.361647 | 0.115924 | 0.936730 | -0.008688 |

A–D table losses use their original fixed-bin/k=5 reports; E uses the declared training-tertile/k=20 method. Thus movement diagnostics are comparable, while L4 method differences must be kept explicit. The separate L4 diagnostic artifact applies the same new method to baseline/B/D data.

E passes every hard movement/event guardrail on both validation seeds, restores positive urgency/speed, and improves visible detour incidence. Urgency/straightness still fails on both seeds; boredom/straightness is not robust across seeds; L4 still worsens small-sample headline loss. This is an improvement candidate, not evidence that all requested failures are fixed.

## Configuration delta from 5.2.0

| Setting | Before | After |
| --- | --- | --- |
| `movement_style.attraction_intercept` | 0.6 | 0.25 |
| `movement_style.attraction_urgency_weight` | 0.8 | 2.0 |
| `movement_style.speed_urgency_weight` | 0.3 | 0.4 |
| `movement_style.detour_probability_scale` | 0.7 | 2.0 |
| `movement_style.detour_urgency_weight` | new | 1.0 |
| `movement_style.departure_alignment_weight` | new | 1.0 |
| `movement_style.detour_offset_km_range` | [0.4, 1.0] | [0.6, 1.0] |
| `learnability.l4_interpolation_k` | 5.0 | 20.0 |
| `learnability.l4_binning` | new | training_tertiles |

Package **5.4.0**, schema **lionsim-v5**. Old runs require their original package/configuration. The published [style example PNG](style_examples.png) and [days 1–3 images](STYLE_EXAMPLES.md) remain explicitly historical 5.2.0 illustrations, not regenerated 5.4.0 output.

## Final 500-day seed-42 confirmation

**39 PASS, 12 WARN, 0 FAIL**. The walking and detour-frequency failures are fixed in this confirmation. Three phase-three targets remain unmet; **the simulator is not fully accepted**. All 500 days pass event invariants.

| Requested target / guardrail | 5.2.0 | 5.4.0 | Current status |
| --- | ---: | ---: | --- |
| guardrail_walking_hours | 6.095500 | 5.928967 | **PASS** |
| trip_boredom_straightness | -0.294315 | -0.319508 | **WARN** |
| trip_urgency_straightness | 0.068929 | 0.182882 | **WARN** |
| trip_urgency_speed | 0.329792 | 0.318465 | **PASS** |
| trip_detour_fraction | 0.069017 | 0.101836 | **PASS** |
| trip_observed_true_straightness | 0.905918 | 0.933494 | **PASS** |
| headline_l4_relative_improvement | -0.020815 | -0.019439 | **WARN** |
| guardrail_zone_entries | 7.432000 | 7.326000 | **PASS** |
| guardrail_walking_speed | 3.412427 | 3.508532 | **PASS** |
| guardrail_abandoned_trips | 0.594000 | 0.626000 | **PASS** |
| guardrail_event_rules | 1.000000 | 1.000000 | **PASS** |

Trip population: **3977**, by final status {'arrived': 3648, 'day_end': 24, 'interrupted': 305}; missing detour geometry: 0. Correlation denominators: boredom_straightness=3977, urgency_straightness=1903, urgency_speed=3977, observed_true_straightness=3977.

### L4 results

| Scope | L0 | L1 | L2 | L3 | L4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Headline | 1.789918 ± 0.017379 | 1.158206 ± 0.016691 | 0.669495 ± 0.010151 | 0.623510 ± 0.018691 | 0.635631 ± 0.023113 |
| All reports | 1.863659 ± 0.009056 | 1.239613 ± 0.013090 | 0.741209 ± 0.009681 | 0.698623 ± 0.017656 | 0.707460 ± 0.021247 |
| 1 | 1.663947 ± 0.023212 | 0.879494 ± 0.041226 | 0.192340 ± 0.031390 | 0.117729 ± 0.043224 | 0.115784 ± 0.047088 |
| 2 | 1.687748 ± 0.065664 | 1.110871 ± 0.029913 | 0.536737 ± 0.024942 | 0.486767 ± 0.027703 | 0.497676 ± 0.031727 |
| 3 | 1.412986 ± 0.029295 | 0.729684 ± 0.062798 | 0.729684 ± 0.062798 | 0.739016 ± 0.077395 | 0.759635 ± 0.084709 |
| 4 | 1.631418 ± 0.043545 | 1.354896 ± 0.043556 | 0.979855 ± 0.044738 | 0.930709 ± 0.061370 | 0.950722 ± 0.072945 |
| 5 | 2.553492 ± 0.079127 | 1.716085 ± 0.067244 | 0.908860 ± 0.009113 | 0.843331 ± 0.023621 | 0.854336 ± 0.031704 |
| 6 | 2.047420 ± 0.031795 | 1.583497 ± 0.024978 | 0.894161 ± 0.036983 | 0.838336 ± 0.049884 | 0.834786 ± 0.051650 |
| 7 | 2.048602 ± 0.085013 | 1.302763 ± 0.074853 | 0.946826 ± 0.044730 | 0.934476 ± 0.046712 | 0.939279 ± 0.051111 |

| Fixed diagnostic | Headline loss ± fold std | Relative improvement over L3 |
| --- | ---: | ---: |
| straightness | 0.635926 ± 0.023835 | -1.9913% |
| speed | 0.632219 ± 0.021320 | -1.3967% |
| detour | 0.628070 ± 0.020753 | -0.7313% |
| no_path_control | 0.629030 ± 0.021022 | -0.8853% |

The best single cue is detour, still **0.7313% worse** than L3; combined L4 is **1.9439% worse**, missing the 2% improvement target. A no-path smoothing control also worsens loss. Training-only bins and stronger regularization do not establish useful additional predictive information here. The target remains WARN; no parameters were changed after seeing confirmation results.

### Every status change

Versus **5.2.0**, only walking changes FAIL→PASS and detour frequency changes WARN→PASS. No previously passing check is demoted. Versus accepted **4.5.0**, the only change is report-7 END_OF_DAY share PASS→WARN (0.61→0.57); all eight original WARNs remain WARN, and no previous PASS becomes FAIL.

[Accepted-baseline comparison](../outputs/phase3_calibrated_stats/run_20261103_221518/baseline_comparison.json) · [Previous-version comparison](../outputs/phase3_calibrated_stats/run_20261103_221518/previous_version_comparison.json)

### Complete check table

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| observed_true_path_ratio | **PASS** | 1.517572 | 1.6 |
| smoothed_rest_apparent_speed_kmh | **PASS** | 0.183637 | 0.8 |
| abandoned_trip_mean | **PASS** | 0.626000 | 1.0 |
| traffic_abandonment_share | **PASS** | 0.000000 | 0.25 |
| waterhole_day_fraction | **PASS** | 0.850000 | [0.8, 0.88] |
| zone_entries_per_day | **WARN** | 7.326000 | [8.0, 11.0] |
| zone_entry_share.Den | **WARN** | 0.025389 | [0.03, 0.35] |
| zone_entry_share.Shade | **PASS** | 0.169806 | [0.03, 0.35] |
| zone_entry_share.Kopje | **PASS** | 0.192192 | [0.03, 0.35] |
| zone_entry_share.Waterhole | **PASS** | 0.147147 | [0.03, 0.35] |
| zone_entry_share.Hunting ground | **PASS** | 0.092547 | [0.03, 0.35] |
| zone_entry_share.Feeding spot | **PASS** | 0.043407 | [0.03, 0.35] |
| zone_entry_share.Plain | **PASS** | 0.312039 | [0.03, 0.35] |
| zone_entry_share.Road | **WARN** | 0.017472 | [0.02, 0.05] |
| hunt_attempt_day_fraction | **PASS** | 0.650000 | [0.5, 0.7] |
| catch_day_fraction | **PASS** | 0.300000 | [0.2, 0.4] |
| road_entry_day_fraction | **PASS** | 0.128000 | [0.1, 0.18] |
| unique_sequence_fraction | **WARN** | 0.316000 | {'minimum_inclusive': 0.5} |
| top_five_sequence_share | **PASS** | 0.312000 | {'maximum_inclusive': 0.35} |
| mean_walking_speed_kmh | **PASS** | 3.508532 | [2.0, 4.0] |
| road_evening_fraction | **PASS** | 0.984375 | 0.6 |
| road_tourist_window_fraction | **PASS** | 0.000000 | 0.1 |
| road_tourist_correlation | **WARN** | -0.346103 | -0.35 |
| events_per_day | **WARN** | 18.288000 | [24.0, 32.0] |
| non_feast_late_entry_fraction | **PASS** | 0.908571 | 0.7 |
| feast_post_meal_entry_fraction | **PASS** | 0.000000 | 0.15 |
| end_of_day_report_6 | **WARN** | 0.364000 | [0.4, 0.6] |
| end_of_day_report_7 | **WARN** | 0.570000 | [0.6, 0.8] |
| prey_density_vs_kopje_dwell | **PASS** | 0.818524 | 0.4 |
| prey_density_vs_first_chase_time | **PASS** | -0.609108 | -0.3 |
| start_hunger_vs_wake_time | **PASS** | -0.316108 | -0.3 |
| heat_vs_shade_entry_time | **PASS** | -0.773450 | -0.4 |
| hours_per_behaviour.resting | **PASS** | 16.308533 | [16.0, 20.0] |
| hours_per_behaviour.walking | **WARN** | 5.928967 | [3.0, 5.0] |
| hours_per_behaviour.hunting | **PASS** | 0.728167 | [0.2, 3.0] |
| hours_per_behaviour.grooming | **PASS** | 0.400033 | [0.1, 2.5] |
| hours_per_behaviour.eating | **PASS** | 0.447700 | [0.0, 1.5] |
| hours_per_behaviour.drinking | **PASS** | 0.186600 | [0.0, 1.0] |
| event_invariants | **PASS** | 0.000000 | 0 |
| trip_boredom_straightness | **WARN** | -0.319508 | {'min': None, 'max': -0.35} |
| trip_urgency_straightness | **WARN** | 0.182882 | {'min': 0.3, 'max': None} |
| trip_urgency_speed | **PASS** | 0.318465 | {'min': 0.25, 'max': None} |
| trip_observed_true_straightness | **PASS** | 0.933494 | {'min': 0.85, 'max': None} |
| trip_detour_fraction | **PASS** | 0.101836 | {'min': 0.1, 'max': 0.3} |
| guardrail_walking_hours | **PASS** | 5.928967 | {'min': None, 'max': 6.0} |
| guardrail_zone_entries | **PASS** | 7.326000 | {'min': 7.0, 'max': None} |
| guardrail_walking_speed | **PASS** | 3.508532 | {'min': None, 'max': 4.0} |
| guardrail_abandoned_trips | **PASS** | 0.626000 | {'min': None, 'max': 1.0} |
| guardrail_event_rules | **PASS** | 1.000000 | {'min': 1, 'max': None} |
| headline_l3_relative_improvement | **PASS** | 0.068686 | 0.03 |
| headline_l4_relative_improvement | **WARN** | -0.019439 | 0.02 |

[Statistics JSON](../outputs/phase3_calibrated_stats/run_20261103_221518/stats_report.json) · [Human report](../outputs/phase3_calibrated_stats/run_20261103_221518/stats_report.md)

## Final matched 100-day oracle

Completed **100 days ×7 usable reports ×100 rollouts =70,000 continuations**. All observed targets, path features and compact statistics match the same first 100 days of the 500-day run exactly. All 600 statistics/oracle day records pass event invariants. No minute trajectories or PNGs were saved.

| Scope | L0 | L1 | L2 | L3 | L4 | Oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| headline | 1.791712 ± 0.051933 | 1.198991 ± 0.081029 | 0.893279 ± 0.068240 | 0.758115 ± 0.086363 | 0.758331 ± 0.096353 | 0.446648 ± 0.064629 |
| all_reports | 1.878440 ± 0.034893 | 1.295863 ± 0.060387 | 0.980091 ± 0.036751 | 0.865020 ± 0.040340 | 0.864337 ± 0.047762 | 0.438350 ± 0.046150 |

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| headline.oracle_l0_ratio | **WARN** | 0.249285 | [0.25, 0.5] |
| headline.oracle_l2_relative_improvement | **PASS** | 0.499991 | 0.1 |
| headline.guardrail_oracle_l0 | **PASS** | 0.249285 | 0.2 |
| all_reports.oracle_l0_ratio | **WARN** | 0.233359 | [0.25, 0.5] |
| all_reports.oracle_l2_relative_improvement | **PASS** | 0.552746 | 0.1 |
| all_reports.guardrail_oracle_l0 | **PASS** | 0.233359 | 0.2 |

Both phase-three oracle/L0 >=0.20 guardrails pass. The older 0.25–0.50 calibration checks still WARN; no oracle check changes status versus 5.2.0 or accepted 4.5.0. The Laplace floor is 0.076227 nats.

**Sample-size limitation:** the oracle run’s incidental 100-day walking mean is **6.062167 h/day**, so its own statistics report flags that walking guardrail FAIL. The required 500-day mean is **5.928967**, PASS. The improvement is established for the specified 500-day population, not every smaller sample or every individual day. The three unresolved phase-three targets remain unresolved.

[Oracle JSON](../outputs/phase3_calibrated_oracle/run_20261103_221518/oracle_report.json) · [Oracle human report](../outputs/phase3_calibrated_oracle/run_20261103_221518/oracle_report.md)

## Final verification and remaining work

**236 tests passed in 61.50s**. New tests cover urgency suppression, one-time departure alignment without teleportation, training-only quantiles/held-out isolation, missing CSV fields and large-k L4 convergence. Existing snapshot, seed, event, report, feature causality, image and resume checks pass. Earlier targeted increments passed 69, 55, 70 and 82 tests respectively.

Audit verified 500 stats checkpoints, 100 oracle checkpoints, 3,500 stats targets and 70,000 continuations; target/feature/stat records agree across matching days. Every target threshold and phase-two setting is unchanged. Event/report/observed-feature/plotting modules are byte-for-byte unchanged from the pre-calibration commit. No ML dependencies were added.

**Fixed in the 500-day confirmation:** walking-hours hard guardrail and visible-detour frequency. **Still unmet:** boredom–straightness, selected-goal urgency–straightness, and L4 ≥2% improvement. A bounded attempt has been delivered; this is not full calibration acceptance. Further work should diagnose why trip-shape cues add little information conditional on observed history, using new independent validation data rather than tuning the same seed-42 confirmation.

## Reproduction

```sh
python -m lionsim.run --stats-only --stats-days 100 --seed 137 --config docs/calibration_phase3/E_departure_repair.json --workers 4 --no-images --out outputs/phase3_calibration_137/E
python -m lionsim.run --stats-only --stats-days 100 --seed 271 --config docs/calibration_phase3/E_departure_repair.json --workers 4 --no-images --out outputs/phase3_calibration_271/E
python -m lionsim.run --stats-only --stats-days 500 --seed 42 --chunk-size 100 --workers 4 --no-images --out outputs/phase3_calibrated_stats
python -m lionsim.run --resume outputs/phase3_calibrated_stats/run_20261103_221518 --chunk-size 100 --workers 4
python -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42 --chunk-size 20 --workers 6 --no-images --out outputs/phase3_calibrated_oracle
python -m lionsim.run --resume outputs/phase3_calibrated_oracle/run_20261103_221518 --chunk-size 20 --workers 6
python -m pytest -q
```

Repeat resume commands until each manifest is complete. Older A–D trials used their recorded 5.3.x package/configuration; their manifests and checks are retained. Never compare the 100-day oracle with 500-day baseline losses; its own baselines use the same 100 days and folds.
