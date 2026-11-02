# Phase 2 S1–S5 results

Simulator **4.4.1**, manifest schema **lionsim-v4**. Implementation complete; calibration targets are not all achieved.

Verified with **182 passing tests** and a **200-day, seed-42 run**: **33 PASS, 7 WARN, 0 FAIL**. All 200 days pass hard event validation.

```sh
python -m pytest -q
python -m lionsim.run --stats-only --stats-days 200 --seed 42
```

[Full statistics](../outputs/phase2_s5_verified/run_20261102_200914/stats_report.md) and [JSON details](../outputs/phase2_s5_verified/run_20261102_200914/stats_report.json).

Resume uses the saved version/configuration; completing an existing run simply rebuilds aggregates from its day checkpoints. Old seeds give different trajectories under this new distribution.

## Requested target checks

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| observed_true_path_ratio | **PASS** | 1.5293 | 1.6 |
| smoothed_rest_apparent_speed_kmh | **PASS** | 0.1836 | 0.8 |
| abandoned_trip_mean | **PASS** | 0.605 | 1 |
| traffic_abandonment_share | **PASS** | 0 | 0.25 |
| waterhole_day_fraction | **PASS** | 0.86 | [0.8, 0.88] |
| zone_entries_per_day | **WARN** | 7.435 | [8.0, 11.0] |
| zone_entry_share.Den | **WARN** | 0.0249 | [0.03, 0.35] |
| zone_entry_share.Shade | **PASS** | 0.1688 | [0.03, 0.35] |
| zone_entry_share.Kopje | **PASS** | 0.191 | [0.03, 0.35] |
| zone_entry_share.Waterhole | **PASS** | 0.1392 | [0.03, 0.35] |
| zone_entry_share.Hunting ground | **PASS** | 0.0948 | [0.03, 0.35] |
| zone_entry_share.Feeding spot | **PASS** | 0.0471 | [0.03, 0.35] |
| zone_entry_share.Plain | **PASS** | 0.3194 | [0.03, 0.35] |
| zone_entry_share.Road | **WARN** | 0.0148 | [0.02, 0.05] |
| hunt_attempt_day_fraction | **PASS** | 0.68 | [0.5, 0.7] |
| catch_day_fraction | **PASS** | 0.34 | [0.2, 0.4] |
| road_entry_day_fraction | **PASS** | 0.11 | [0.1, 0.18] |
| unique_sequence_fraction | **WARN** | 0.445 | {'minimum_inclusive': 0.5} |
| top_five_sequence_share | **PASS** | 0.345 | {'maximum_inclusive': 0.35} |
| mean_walking_speed_kmh | **PASS** | 3.5086 | [2.0, 4.0] |
| road_evening_fraction | **PASS** | 1 | 0.6 |
| road_tourist_window_fraction | **PASS** | 0 | 0.1 |
| road_tourist_correlation | **WARN** | -0.301 | -0.35 |
| events_per_day | **WARN** | 18.51 | [24.0, 32.0] |
| non_feast_late_entry_fraction | **PASS** | 0.9015 | 0.7 |
| feast_post_meal_entry_fraction | **PASS** | 0 | 0.15 |
| end_of_day_report_6 | **PASS** | 0.405 | [0.4, 0.6] |
| end_of_day_report_7 | **PASS** | 0.6 | [0.6, 0.8] |
| prey_density_vs_kopje_dwell | **PASS** | 0.8559 | 0.4 |
| prey_density_vs_first_chase_time | **PASS** | -0.6146 | -0.3 |
| start_hunger_vs_wake_time | **PASS** | -0.3749 | -0.3 |
| heat_vs_shade_entry_time | **PASS** | -0.6638 | -0.4 |
| hours_per_behaviour.resting | **PASS** | 16.3604 | [16.0, 20.0] |
| hours_per_behaviour.walking | **WARN** | 5.7937 | [3.0, 5.0] |
| hours_per_behaviour.hunting | **PASS** | 0.7523 | [0.2, 3.0] |
| hours_per_behaviour.grooming | **PASS** | 0.3949 | [0.1, 2.5] |
| hours_per_behaviour.eating | **PASS** | 0.5322 | [0.0, 1.5] |
| hours_per_behaviour.drinking | **PASS** | 0.1665 | [0.0, 1.0] |
| event_invariants | **PASS** | 0 | 0 |
| headline_l3_relative_improvement | **PASS** | 0.1325 | 0.03 |


## Cross-validated loss (nats)

Five interleaved folds of whole days; means ± population standard deviations across folds. Every day is tested once. Headline indices are 1–5.

| Scope | L0 | L1 | L2 | L3 |
| --- | ---: | ---: | ---: | ---: |
| Headline | 1.757037 ± 0.045988 | 1.098273 ± 0.074448 | 0.702174 ± 0.059147 | 0.609133 ± 0.064929 |
| All reports | 1.859618 ± 0.049785 | 1.164922 ± 0.065910 | 0.785726 ± 0.060286 | 0.698687 ± 0.068128 |
| 1 | 1.715940 ± 0.036120 | 0.924810 ± 0.090472 | 0.292440 ± 0.061871 | 0.125031 ± 0.050326 |
| 2 | 1.661242 ± 0.103524 | 1.123861 ± 0.056732 | 0.571107 ± 0.057797 | 0.492339 ± 0.086196 |
| 3 | 1.379664 ± 0.017682 | 0.641450 ± 0.067704 | 0.641450 ± 0.067704 | 0.623060 ± 0.095238 |
| 4 | 1.527141 ± 0.053219 | 1.216055 ± 0.133882 | 0.942244 ± 0.099636 | 0.884677 ± 0.120558 |
| 5 | 2.501195 ± 0.126422 | 1.585186 ± 0.128433 | 1.063628 ± 0.150934 | 0.920557 ± 0.165075 |
| 6 | 2.147147 ± 0.108797 | 1.427078 ± 0.092078 | 0.998206 ± 0.112520 | 0.910130 ± 0.133102 |
| 7 | 2.084994 ± 0.146983 | 1.236011 ± 0.145499 | 0.991005 ± 0.109101 | 0.935014 ± 0.128944 |

Headline L3 improves on L2 by **13.25%** (target ≥3%). All four S5 correlation targets pass. No held-out labels choose bins or fit interpolation strength.

## All changed knobs versus phase-one final defaults

The model was developed and inspected on seed 42; these diagnostics are not an untouched external validation set. Defaults were chosen to implement the requested mechanisms, then four S4 adjustments were made explicitly after measurement. No target bounds were loosened to hide misses.

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

## Reference target changes

These ranges implement the new spec, rather than retroactively grading against the old targets.

| Setting | Before | Phase-two target |
| --- | --- | --- |
| `targets.zone_entries_per_day` | [6.0, 12.0] | [8.0, 11.0] |
| `targets.road_entry_day_fraction` | [0.1, 0.25] | [0.1, 0.18] |
| `targets.unique_sequence_fraction_min` | 0.3 | 0.5 |
| `targets.top_five_sequence_share_max` | 0.5 | 0.35 |
| `targets.hours_per_behaviour.walking` | [1.0, 5.0] | [3.0, 5.0] |
| `targets.observed_true_path_ratio_max` | new | 1.6 |
| `targets.smoothed_rest_speed_max_kmh` | new | 0.8 |
| `targets.abandoned_trip_mean_max` | new | 1.0 |
| `targets.traffic_abandonment_share_max` | new | 0.25 |
| `targets.waterhole_day_fraction` | new | [0.8, 0.88] |
| `targets.road_entry_share` | new | [0.02, 0.05] |
| `targets.road_tourist_correlation_max` | new | -0.35 |
| `targets.road_evening_fraction_min` | new | 0.6 |
| `targets.road_tourist_window_fraction_max` | new | 0.1 |
| `targets.events_per_day` | new | [24.0, 32.0] |
| `targets.non_feast_late_entry_fraction_min` | new | 0.7 |
| `targets.feast_post_meal_entry_fraction_max` | new | 0.15 |
| `targets.end_of_day_report_6_range` | new | [0.4, 0.6] |
| `targets.end_of_day_report_7_range` | new | [0.6, 0.8] |
| `targets.prey_kopje_dwell_correlation_min` | new | 0.4 |
| `targets.prey_first_chase_correlation_max` | new | -0.3 |
| `targets.hunger_wake_correlation_max` | new | -0.3 |
| `targets.heat_shade_entry_correlation_max` | new | -0.4 |
| `targets.headline_l3_improvement_min` | new | 0.03 |

## Mechanisms and limits

- Traffic aversion schedules a delayed wait after a car has passed, preserving destination/activity. Its activation is logged as `delayed_by_traffic`, separately from abandonment reasons. Optional retreat waypoints also preserve the destination.
- Evening Road choices use boredom and observed same-day car counts, never pre-generated future car counts. Hunt/feeding commitments remain protected. Trips target the nearest road boundary, and the surface speed bonus stays within the configured bounds.
- Non-catch nights plan 1–3 destinations among Plain, Kopje, Den, Waterhole and an eligible Road transit. Incidental crossings can add entries; all actual entries are counted. Safe-zone short naps and quiet rest spread those visits through the night. Catch nights remain asleep after feeding.
- The daytime walking budget stops new voluntary trips, not a committed trip in progress. Required water/shade/hunt travel can exceed that budget. Water-bound hot lions continue toward a cooling destination; hunt-start grace for finishing water travel is bounded.
- Morning Kopje scouting increases with prey density; its observed gap includes travel to the next entered zone and can be shortened by a heat schedule. Hunger advances initial waking; prey advances hunt readiness within the unchanged evening window. Heat effects remain intact.
- GPS smoothing uses consecutive trailing five-fix means and only windows wholly within sleeping/quiet-rest intervals. The pooled observed/true path ratio and apparent speeds are diagnostics, not changes to the exported minute cadence.
- S5 trials: implemented the scouting route, 30m hunger shift with 20m wake noise, and up-to-45m prey-dependent hunt delay. The first measured S5 run already exceeded the 3% headline improvement target; no subsequent L3-specific tuning was performed.

Remaining warnings are genuine: entry/event density and sequence diversity are low, Den/Road shares are low, traffic–Road correlation is weaker than requested, and walking still exceeds five hours. S5 scouting improved the cross-time signal but increased walking from the S4-only result. No extra events, quotas or relaxed thresholds were used to hide that tradeoff.

## Boundary of this delivery

S1–S5 implementation and their relevant tests are complete. S6’s 100-day × 100-rollout oracle, new oracle targets and 500-day final run with first-three-day images have **not** been run or claimed complete. S7 has not been taken as a separate phase; relevant regressions were included with each increment.
