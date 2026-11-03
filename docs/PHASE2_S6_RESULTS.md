# Phase 2 S6 final evaluation

Package **4.5.0**, manifest schema **lionsim-v4**, seed **42**. S6 changes reporting and output selection; trajectories retain the S5 (4.4.1) distribution. No behavior or noise knobs were tuned in this phase.

## 100-day hidden-state oracle

Completed five chunks of 20 days, **100 rollouts per each of seven reports** (70,000 continuations). Headline reports are 1–5. Baselines and oracle use the same 100 days and five day-disjoint folds. Means ± population standard deviations across folds, in nats; lower is better.

| Scope | L0 | L1 | L2 | L3 | oracle |
| --- | ---: | ---: | ---: | ---: | ---: |
| headline | 1.796986 ± 0.074812 | 1.146523 ± 0.129483 | 0.813254 ± 0.134579 | 0.674973 ± 0.152751 | 0.440580 ± 0.117099 |
| all_reports | 1.868136 ± 0.060393 | 1.170343 ± 0.101689 | 0.873345 ± 0.090954 | 0.746831 ± 0.104448 | 0.412754 ± 0.087810 |

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| headline.oracle_l0_ratio | **WARN** | 0.245177 | [0.25, 0.5] |
| headline.oracle_l2_relative_improvement | **PASS** | 0.458250 | 0.1 |
| all_reports.oracle_l0_ratio | **WARN** | 0.220944 | [0.25, 0.5] |
| all_reports.oracle_l2_relative_improvement | **PASS** | 0.527387 | 0.1 |

Headline: oracle/L0 below target: simulator is too deterministic; consider increasing learnability.softmax_temperature to randomize future goal choices, then remeasure (no change applied). All reports: oracle/L0 below target: simulator is too deterministic; consider increasing learnability.softmax_temperature to randomize future goal choices, then remeasure (no change applied).

The proposed softmax-temperature increase is an experiment to test, not an applied fix or a guarantee. It changes future goal choices, while already committed schedules remain conditioned state. Recheck oracle loss, entry counts, road timing and walking budget together before accepting it.

The finite-sample Laplace floor is **0.076227 nats**. The oracle knows latent drives and commitments unavailable to observable-history models; low oracle loss does not mean an event-only predictor can attain it. The 100-day oracle and 500-day baseline tables below are different evaluations and must not be compared across sample sizes.

[Oracle Markdown](../outputs/phase2_s6_oracle/run_20261102_202029/oracle_report.md) · [Timestamped probabilities and counts](../outputs/phase2_s6_oracle/run_20261102_202029/oracle_report.json)

## 500-day final statistics

Completed five chunks of 100 days: **32 PASS, 8 WARN, 0 FAIL**. All hard day invariants pass. Exactly **27 text-free PNGs** were produced: eight report paths and one contact sheet for each of days 1–3; no images on days 4–500 and no per-minute files.

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| observed_true_path_ratio | **PASS** | 1.535032 | 1.6 |
| smoothed_rest_apparent_speed_kmh | **PASS** | 0.183551 | 0.8 |
| abandoned_trip_mean | **PASS** | 0.602000 | 1.0 |
| traffic_abandonment_share | **PASS** | 0.000000 | 0.25 |
| waterhole_day_fraction | **PASS** | 0.820000 | [0.8, 0.88] |
| zone_entries_per_day | **WARN** | 7.392000 | [8.0, 11.0] |
| zone_entry_share.Den | **WARN** | 0.028139 | [0.03, 0.35] |
| zone_entry_share.Shade | **PASS** | 0.168290 | [0.03, 0.35] |
| zone_entry_share.Kopje | **PASS** | 0.198864 | [0.03, 0.35] |
| zone_entry_share.Waterhole | **PASS** | 0.137716 | [0.03, 0.35] |
| zone_entry_share.Hunting ground | **PASS** | 0.091450 | [0.03, 0.35] |
| zone_entry_share.Feeding spot | **PASS** | 0.041937 | [0.03, 0.35] |
| zone_entry_share.Plain | **PASS** | 0.316829 | [0.03, 0.35] |
| zone_entry_share.Road | **WARN** | 0.016775 | [0.02, 0.05] |
| hunt_attempt_day_fraction | **PASS** | 0.650000 | [0.5, 0.7] |
| catch_day_fraction | **PASS** | 0.302000 | [0.2, 0.4] |
| road_entry_day_fraction | **PASS** | 0.124000 | [0.1, 0.18] |
| unique_sequence_fraction | **WARN** | 0.308000 | {'minimum_inclusive': 0.5} |
| top_five_sequence_share | **PASS** | 0.334000 | {'maximum_inclusive': 0.35} |
| mean_walking_speed_kmh | **PASS** | 3.501875 | [2.0, 4.0] |
| road_evening_fraction | **PASS** | 0.983871 | 0.6 |
| road_tourist_window_fraction | **PASS** | 0.016129 | 0.1 |
| road_tourist_correlation | **WARN** | -0.343800 | -0.35 |
| events_per_day | **WARN** | 18.198000 | [24.0, 32.0] |
| non_feast_late_entry_fraction | **PASS** | 0.902579 | 0.7 |
| feast_post_meal_entry_fraction | **PASS** | 0.000000 | 0.15 |
| end_of_day_report_6 | **WARN** | 0.370000 | [0.4, 0.6] |
| end_of_day_report_7 | **PASS** | 0.610000 | [0.6, 0.8] |
| prey_density_vs_kopje_dwell | **PASS** | 0.850040 | 0.4 |
| prey_density_vs_first_chase_time | **PASS** | -0.586484 | -0.3 |
| start_hunger_vs_wake_time | **PASS** | -0.316108 | -0.3 |
| heat_vs_shade_entry_time | **PASS** | -0.739135 | -0.4 |
| hours_per_behaviour.resting | **PASS** | 16.505533 | [16.0, 20.0] |
| hours_per_behaviour.walking | **WARN** | 5.759367 | [3.0, 5.0] |
| hours_per_behaviour.hunting | **PASS** | 0.726367 | [0.2, 3.0] |
| hours_per_behaviour.grooming | **PASS** | 0.402933 | [0.1, 2.5] |
| hours_per_behaviour.eating | **PASS** | 0.458267 | [0.0, 1.5] |
| hours_per_behaviour.drinking | **PASS** | 0.147533 | [0.0, 1.0] |
| event_invariants | **PASS** | 0.000000 | 0 |
| headline_l3_relative_improvement | **PASS** | 0.074182 | 0.03 |

## Per-report counting-model losses, 500 days

| Scope | L0 | L1 | L2 | L3 |
| --- | ---: | ---: | ---: | ---: |
| Headline | 1.798765 ± 0.019263 | 1.149248 ± 0.038733 | 0.667712 ± 0.047714 | 0.618180 ± 0.066480 |
| All reports | 1.879851 ± 0.011242 | 1.208672 ± 0.026798 | 0.725866 ± 0.029825 | 0.684630 ± 0.042481 |
| 1 | 1.684835 ± 0.031892 | 0.897274 ± 0.045248 | 0.174047 ± 0.020589 | 0.093949 ± 0.037177 |
| 2 | 1.717494 ± 0.054908 | 1.145513 ± 0.075437 | 0.527427 ± 0.082343 | 0.499462 ± 0.118160 |
| 3 | 1.475607 ± 0.024366 | 0.789557 ± 0.118956 | 0.789557 ± 0.118956 | 0.793954 ± 0.145505 |
| 4 | 1.597862 ± 0.047949 | 1.295120 ± 0.079906 | 0.959462 ± 0.071420 | 0.914497 ± 0.108005 |
| 5 | 2.518027 ± 0.066980 | 1.618777 ± 0.065109 | 0.888066 ± 0.070708 | 0.789037 ± 0.093252 |
| 6 | 2.124123 ± 0.065078 | 1.478991 ± 0.085939 | 0.835984 ± 0.044520 | 0.800311 ± 0.045608 |
| 7 | 2.041013 ± 0.082771 | 1.235473 ± 0.042960 | 0.906516 ± 0.032372 | 0.901202 ± 0.044817 |

Headline L3 improves on L2 by **7.42%**. Calibration misses remain warnings; thresholds were not relaxed. Sequence uniqueness is sample-size dependent, so its 500-day fraction is not directly interchangeable with the earlier 200-day fraction.

[Full final statistics](../outputs/phase2_s6_final/run_20261103_085841/stats_report.md) · [JSON](../outputs/phase2_s6_final/run_20261103_085841/stats_report.json)

## Changed settings and assumptions

No simulation settings changed during S6. Two evaluation defaults were added under `targets`:

| Setting | Value | Reason |
| --- | --- | --- |
| `oracle_l0_ratio_range` | `[0.25, 0.50]` | Requested oracle balance range, checked separately for headline and all reports. |
| `oracle_l2_improvement_min` | `0.10` | Requested headroom below L2, checked in both scopes. |

`--image-days K` now explicitly enables images for the first K days in stats/oracle mode; the default remains zero. Image artifacts participate in atomic checkpoints and are repaired on resume. `--no-images` still wins. No new image configuration value is needed because the existing CLI selection controls this.

The complete S1–S5 knob changes and trial history are retained below; values are unchanged in S6.

| Setting | Before | Final | Reason / meaning |
| --- | --- | --- | --- |
| `randomness.wake_time_sd_minutes` | 30.0 | 20.0 | Keep independent variation while making the up-to-30m hunger shift measurable. |
| `randomness.gps_noise_sd_m` | 15.0 | 8.0 | Requested 15→8m reduction to control observed-path inflation. |
| `goal.distance_penalty_per_km` | 0.3 | 0.8 | Favor nearby voluntary daytime destinations to reserve walking time for night patrols. |
| `movement.road_surface_speed_bonus_kmh` | new | 0.2 | Speed bonus on the Road, still clipped to configured patrol-speed bounds. |
| `movement.patrol_cruise_fraction` | new | 0.5 | Reduce travel time without removing state-dependent speed variation or exceeding the 2–4 km/h bounds; initial 0.35 was increased to 0.50 after the walking-budget check. |
| `road_response.traffic_wait_enabled` | new | true | Use a stationary delay for aversion; false retains a retreat waypoint while preserving the same destination. |
| `road_response.traffic_delay_minutes_range` | new | [4, 10] | Uniform delay after an already-heard aversive car; resume the saved trip/activity afterward. |
| `statistics.rest_smoothing_minutes` | new | 5 | Trailing mean-position smoothing width; only complete all-resting windows contribute apparent speeds. |
| `learnability.behaviour.night_nap_max_cycles` | 3 | 4 | Requested allowance of at most four cycles; the model does not force four naps. |
| `learnability.behaviour.afternoon_water_probability` | 0.65 | 0.75 | Initially 0.65→0.85 for water reachability; reduced to 0.75 after protected water trips and night visits raised water coverage to 94%. |
| `learnability.behaviour.evening_road_probability` | new | 0.9 | Maximum one-off evening road choice chance, multiplied by boredom and an observed-traffic discount. |
| `learnability.behaviour.road_volume_reference_count` | new | 14 | Initial value 9 increased to 14 after Road visits remained rare; applies only to already-observed car counts. |
| `learnability.behaviour.road_volume_decay` | new | 0.18 | Exponential road-goal penalty per observed car above the reference count. |
| `learnability.behaviour.road_daytime_multiplier` | new | 0.01 | Initial 0.05 reduced to 0.01 after tourist-window Road entries exceeded the requested limit. |
| `learnability.behaviour.road_evening_start` | new | "19:00" | Earliest favored evening road choice; must also be after tourist end. |
| `learnability.behaviour.road_evening_end` | new | "23:00" | Latest favored evening road-goal decision, exclusive; travel may finish later. |
| `learnability.behaviour.night_patrol_entry_weights` | new | [0.1, 0.35, 0.55] | Probabilities of planning 1, 2 or 3 night destinations on non-catch days; actual incidental crossings are also measured. |
| `learnability.behaviour.night_patrol_distance_penalty` | new | 0.8 | Per-km logit penalty for long night legs, favoring nearby territory. |
| `learnability.behaviour.night_repeat_zone_weight` | new | 0.25 | Relative weight for a previously visited night destination. |
| `learnability.behaviour.daytime_travel_budget_minutes` | new | 120 | After this much pre-night walking, finish current trips but decline new voluntary daytime wandering; water, shade and hunt schedules still apply. |
| `learnability.behaviour.water_trip_grace_minutes` | new | 30 | Maximum hunt-start grace for completing an already committed water journey; hunt cutoff remains unchanged. |
| `learnability.behaviour.morning_scout_probability` | new | 0.9 | Probability of a morning scouting trip to Kopje after initial grooming. |
| `learnability.behaviour.scout_base_minutes` | new | 20.0 | Minimum mean Kopje scouting dwell before heading toward Plain. |
| `learnability.behaviour.scout_prey_extra_minutes` | new | 75.0 | Additional scouting dwell from low to high prey signal; observable in the next entry gap. |
| `learnability.behaviour.scout_jitter_sd_minutes` | new | 8.0 | Independent noise in scouting dwell; scheduled heat departures may interrupt scouting. |
| `learnability.behaviour.prey_reference_range` | new | [0.5, 1.5] | Fixed normalization for prey-linked dwell and hunt timing; separate from latent sampling bounds. |
| `learnability.behaviour.hunger_wake_shift_minutes` | new | 30.0 | Maximum earlier waking shift at hunger=1; original 05:00–07:00 clip is preserved. |
| `learnability.behaviour.prey_hunt_delay_max_minutes` | new | 45 | Maximum departure delay beyond hunt start at low prey; high prey has no added delay. |
| `learnability.behaviour.night_pause_minutes_range` | new | [65, 115] | Total stop between night legs; safe-zone short catnaps use the original duration range, followed by quiet rest for the remainder. |
| `learnability.cv_folds` | new | 5 | Deterministic interleaved folds of whole days; use fewer folds only when fewer days exist. |
| `learnability.headline_reports` | new | [1, 2, 3, 4, 5] | Report indices contributing to headline losses; all usable reports are also evaluated. |
| `learnability.l3_interpolation_k` | new | 5.0 | Positive L2 prior pseudo-count in (cell class count + k*p_L2)/(cell total + k). |
| `learnability.shade_hour_cut` | new | 11 | Three shade-history bins: not_yet, observed before this hour, observed at/after this hour. |

Intermediate change retained for audit: the first S4 draft used 65–115m catnaps. The final model restores the original 20–60m draw (minimum 25m) and assigns the remaining stop to quiet rest. That final duration range matches phase-one defaults, so it does not appear in the difference table above.

Legacy `train_fraction` and `l3_min_cell_count` remain loadable but are inactive. The old 70/30 split and hard L3 backoff were replaced by CV and interpolation. No ML libraries were added.


## Reproduction and verification

Each resume command processes only the next chunk; repeat it four times after each initial command. Use the run directory printed by the corresponding first invocation.

```sh
python -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42 --workers 4 --chunk-size 20 --out outputs/phase2_s6_oracle
python -m lionsim.run --resume outputs/phase2_s6_oracle/run_20261102_202029 --workers 4 --chunk-size 20
python -m lionsim.run --stats-only --stats-days 500 --seed 42 --workers 4 --chunk-size 100 --image-days 3 --out outputs/phase2_s6_final
python -m lionsim.run --resume outputs/phase2_s6_final/run_20261103_085841 --workers 4 --chunk-size 100
python -m pytest -q
```

Full verification: **185 tests passed in 37.96s**. Artifact audit confirmed all 600 checkpoints, 70,000 continuations, exact target agreement between oracle and statistics days, unchanged S5 targets for days 1–200, and 27 decodable PNGs. The day-1 contact sheet was visually checked for text-free zones and paths. Matplotlib emitted nonfatal sandbox font-cache warnings; all images were generated successfully.

Existing tests cover exact oracle continuation, day-disjoint folds, headline weighting, interpolation, image-limit/resume repair, fixed-seed behavior and event invariants. S7 remains the next separate spec task; S6 does not change its scope.
