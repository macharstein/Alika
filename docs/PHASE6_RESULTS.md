# Phase 6 delivery and acceptance status

**Implemented and measured; not fully accepted.** Version6.0.0 / lionsim-v6.
Final regression: **270 tests passed in73.90s**.
Full mechanisms, assumptions and reproduction commands: [PHASE6_WEATHER.md](PHASE6_WEATHER.md).

One declared seed3003 measurement:500 days in100-day resume chunks, plus100
oracle days in20-day resume chunks,100 rollouts per usable report (70,000 total),
four workers, no images. **No production code-defect retry or post-result tuning.**
All500 event validations pass; all100 original oracle days match the measurement
exactly in targets, summary and daily statistics. No day_type in targets.csv.
The17-token vocabulary, report schedule, hunt cutoff and PNG renderer are unchanged.

Source/settings frozen before measurement at `f57fe4c` (implementation `dfc21f2`).
[Artifact/configuration hashes](phase6_provenance.json) identify the outputs.
The old comparison is the saved v5.4.0 seed2026 run, with no re-simulation.
Historical example PNGs remain unchanged; only fixed rendering-test fixtures were
updated for the new trajectories. No Git tag or dataset plan was created.

**Declared checks:26 PASS,4 WARN,3 FAIL.** The failures are low zone entries and
low events/day, plus the aggregate check for a new hard failure. That third check
counts the same zone-entry failure, not a third independent behavioural defect.
Zone entries actually increased7.328→7.382/day, but the explicitly revised hard
minimum increased7.0→7.5. The requirement for no new hard-failure status is unmet.
No previously passing correlation deteriorated to WARN/FAIL.

The original statistics report also retains older diagnostic targets; its separate
count is40 PASS,10 WARN,1 FAIL. These should not be confused with the33 declared
phase-six checks below. All candidate knobs are suggestions only and were not applied.

Outputs:
- [Measurement statistics](../outputs/phase6_stats/run_20261104_212135/stats_report.md)
- [Declared comparison JSON](../outputs/phase6_stats/run_20261104_212135/phase6_report.json)
- [Oracle report](../outputs/phase6_oracle/run_20261104_212226/oracle_report.md)

---

# Phase 6 measurement: weather, day types and randomness

Simulator6.0.0 / lionsim-v6; seed3003; 500 days; oracle100 days x100 continuations at each of seven reports.
One frozen measurement, no post-result tuning. Candidate knobs below are suggestions only, not applied changes.

Checks: {'PASS': 26, 'WARN': 4, 'FAIL': 3}.

| Target | Observed | Min | Max | Status |
|---|---:|---:|---:|---|
| zone_unique_fraction_N200_ratio | 1.29200 | 1.25000 | N/A | PASS |
| zone_distinct_N500_ratio | 1.37748 | 1.30000 | N/A | PASS |
| zone_top5_share_N500 | 0.25800 | N/A | 0.25000 | WARN |
| event_unique_fraction_N200 | 0.77875 | 0.85000 | N/A | WARN |
| oracle_over_L0_headline_100_days | 0.28503 | 0.28000 | 0.45000 | PASS |
| L2_improvement_over_L1 | 0.31342 | 0.15000 | N/A | PASS |
| L3_improvement_over_L2 | 0.05294 | 0.03000 | N/A | PASS |
| event_invariant_failures | 0.00000 | 0.00000 | 0.00000 | PASS |
| hunt_cutoff_respected | 1.00000 | 1.00000 | 1.00000 | PASS |
| zone_entries_per_day | 7.38200 | 7.50000 | 11.00000 | FAIL |
| events_per_day | 18.32200 | 19.00000 | N/A | FAIL |
| walking_hours | 6.08553 | N/A | 6.50000 | PASS |
| walking_speed_kmh | 3.47593 | 2.00000 | 4.00000 | PASS |
| resting_hours | 16.13527 | 15.50000 | 20.00000 | PASS |
| any_chase_day_fraction | 0.64800 | 0.50000 | 0.70000 | PASS |
| catch_day_fraction | 0.31800 | 0.20000 | 0.40000 | PASS |
| enter_road_day_fraction | 0.12000 | 0.10000 | 0.18000 | PASS |
| enter_water_day_fraction | 0.66200 | 0.65000 | 0.88000 | PASS |
| abandoned_trips_per_day | 0.72600 | N/A | 1.00000 | PASS |
| weather_frequency.clear | 0.41200 | 0.35000 | 0.45000 | PASS |
| weather_frequency.hot | 0.25600 | 0.20000 | 0.30000 | PASS |
| weather_frequency.overcast | 0.20600 | 0.15000 | 0.25000 | PASS |
| weather_frequency.rain | 0.12600 | 0.10000 | 0.20000 | PASS |
| rain_clear_tourist_ratio | 0.32835 | N/A | 0.40000 | PASS |
| hot_shade_advance_vs_overcast | 41.77737 | 45.00000 | N/A | WARN |
| hot_shade_advance_vs_rain | 114.93847 | 45.00000 | N/A | PASS |
| rain_waterhole_day_fraction | 0.28571 | N/A | 0.65000 | PASS |
| hot_waterhole_day_fraction | 0.78906 | 0.85000 | N/A | WARN |
| prey_rich_first_chase_advance | 27.42710 | 20.00000 | N/A | PASS |
| prey_rich_kopje_dwell_ratio | 1.73939 | 1.30000 | N/A | PASS |
| rival_extra_zone_entries | 1.49697 | 1.00000 | N/A | PASS |
| rival_waterhole_day_fraction | 0.15238 | N/A | 0.60000 | PASS |
| new_hard_failures_vs_v5 | 1.00000 | 0.00000 | 0.00000 | FAIL |

## Missed targets and candidate knobs

- **WARN: zone_top5_share_N500 = 0.25800**, expected [None, 0.25]. Candidate: randomness.period_prior_scale.
- **WARN: event_unique_fraction_N200 = 0.77875**, expected [0.85, None]. Candidate: randomness.period_jitter_minutes / day-type diversity.
- **FAIL: zone_entries_per_day = 7.38200**, expected [7.5, 11]. Candidate: day_types.rival.extra_patrol_entries_range.
- **FAIL: events_per_day = 18.32200**, expected [19, None]. Candidate: day_types.rival patrol dwell / entry plan.
- **WARN: hot_shade_advance_vs_overcast = 41.77737**, expected [45, None]. Candidate: shade_entry_heat_shift_minutes / weather heat ranges.
- **WARN: hot_waterhole_day_fraction = 0.78906**, expected [0.85, None]. Candidate: weather.hot.water_visit_multiplier / water_goal_bonus.
- **FAIL: new_hard_failures_vs_v5 = 1.00000**, expected [0, 0]. Candidate: review listed regressions; no silent retuning.

## Baseline losses (five day folds; lower is better)

| Model | Before headline | Current headline | Before all | Current all |
|---|---:|---:|---:|---:|
| L0 | 1.71008 | 1.80739 | 1.82091 | 1.86839 |
| L1 | 1.09911 | 1.27933 | 1.20461 | 1.32068 |
| L2 | 0.63147 | 0.87836 | 0.71297 | 0.88058 |
| L3 | 0.58451 | 0.83186 | 0.67498 | 0.84422 |
| L3w | — | 0.82823 | — | 0.84401 |

Oracle/L0 headline: before ~0.249; current 0.28503.
Before ratio about0.249 is the historical v5.4.0 seed42 oracle, not a matched seed2026 oracle; current ratio uses 100 seed3003 days and their own L0.

## Prior correlation regressions

[]

New hard failures versus the old check table: [{"name": "guardrail_zone_entries", "observed": 7.382, "expected": {"min": 7.5, "max": null}, "status": "FAIL", "message": "Hard phase-three guardrail."}]


## Fixed-sample sequence diversity

| Sequence | N | Metric | v5.4.0 | Current |
|---|---:|---|---:|---:|
| zone_entries | 200 | unique_fraction | 0.4315 | 0.5575 |
| zone_entries | 200 | distinct_sequences | 86.3000 | 111.5000 |
| zone_entries | 200 | top5_share | 0.3430 | 0.2742 |
| zone_entries | 200 | normalised_entropy | 0.8817 | 0.9078 |
| zone_entries | 500 | unique_fraction | 0.3020 | 0.4160 |
| zone_entries | 500 | distinct_sequences | 151.0000 | 208.0000 |
| zone_entries | 500 | top5_share | 0.3320 | 0.2580 |
| zone_entries | 500 | normalised_entropy | 0.8424 | 0.8745 |
| event_tokens | 200 | unique_fraction | 0.6705 | 0.7788 |
| event_tokens | 200 | distinct_sequences | 134.1000 | 155.7500 |
| event_tokens | 200 | top5_share | 0.1928 | 0.1368 |
| event_tokens | 200 | normalised_entropy | 0.9465 | 0.9697 |
| event_tokens | 500 | unique_fraction | 0.5540 | 0.6660 |
| event_tokens | 500 | distinct_sequences | 277.0000 | 333.0000 |
| event_tokens | 500 | top5_share | 0.1780 | 0.1240 |
| event_tokens | 500 | normalised_entropy | 0.9197 | 0.9491 |

20 seeded subsets without replacement at fixed N; entropy divided by log(distinct sequences). Missing N is not replaced by a smaller sample.

## Weather and hidden day-type breakdowns

Times below are minutes after day start; hidden day types are analysis only. Counts accompany every mean in JSON.

| weather | Days | Fraction | shade_entry_minutes | waterhole_day_fraction | tourist_volume | ambient_temp_c |
|---|---:|---:|---:|---:|---:|---:|
| clear | 206 | 0.4120 | 343.8459 | 0.7039 | 22.0922 | 27.0393 |
| hot | 128 | 0.2560 | 322.1234 | 0.7891 | 22.7500 | 31.4790 |
| overcast | 103 | 0.2060 | 363.9008 | 0.6505 | 22.7670 | 21.6503 |
| rain | 63 | 0.1260 | 437.0619 | 0.2857 | 7.2540 | 19.1795 |

| day_type | Days | Fraction | first_chase_minutes | kopje_dwell_minutes | zone_entries_per_day | waterhole_day_fraction |
|---|---:|---:|---:|---:|---:|---:|
| normal | 308 | 0.6160 | 903.8912 | 94.6287 | 7.0649 | 0.8084 |
| prey_rich | 87 | 0.1740 | 876.4641 | 164.5965 | 7.0805 | 0.7586 |
| rival | 105 | 0.2100 | 897.3121 | 90.1411 | 8.5619 | 0.1524 |


## Behaviour before/current

| Metric | v5.4.0 | v6.0.0 |
|---|---:|---:|
| events_per_day | 18.27600 | 18.32200 |
| zone_entries_per_day | 7.32800 | 7.38200 |
| walking hours | 6.00877 | 6.08553 |
| sleeping_resting hours | 16.18910 | 16.13527 |
