# Phase 2 S7 regression coverage

S7 audits the tests accumulated during S1–S6 and strengthens gaps. The simulator,
configuration defaults, schema and package version remain unchanged. The S6
[500-day and oracle measurements](PHASE2_S6_RESULTS.md) still describe this distribution;
passing regression tests does not resolve the recorded calibration warnings.

## Requested coverage

| S7 requirement | Tests | What they establish |
| --- | --- | --- |
| Traffic delay logging; near-zero traffic abandonments | [test_road_dynamics.py](../tests/test_road_dynamics.py): `test_traffic_wait_preserves_destination_and_records_delay_not_abandonment`, `test_default_traffic_delays_are_logged_without_traffic_abandonments` | Controlled delay preserves and resumes the goal; a ten-day seed-42 batch logs delays and no traffic-abandonment reasons. |
| Road entries occur and mostly follow 19:00 | [test_road_dynamics.py](../tests/test_road_dynamics.py): `test_seeded_road_entries_are_reachable_and_predominantly_evening` | Forty fixed-seed days contain Road entries, more than half in the evening; every day passes hard validation. A separate causal test checks boredom and observed traffic effects. |
| Late entries on non-feast nights; none after feasting | [test_behaviour_scenarios.py](../tests/test_behaviour_scenarios.py): `test_night_patrols_add_late_entries_without_breaking_catch_sleep_or_cutoff` | Forty days include both feast and non-feast cases. More than half of non-feast days have entries after 23:00; feast days have none after EAT_END. The explicit feast-count assertion prevents a vacuous pass. |
| Hunt cutoff remains 22:00 | [test_behaviour_scenarios.py](../tests/test_behaviour_scenarios.py): `test_hunting_stops_at_22_even_when_hunger_and_prey_remain_high`, plus the night-patrol batch | Forced failed hunts exercise the cutoff: no later CHASE_START/ENTER_HUNT or hidden hunting behavior, even with high hunger. |
| END_OF_DAY and final-report exclusion unchanged | [test_event_exports.py](../tests/test_event_exports.py): `test_target_is_strictly_future_same_day_and_final_report_is_excluded`, `test_next_day_entry_cannot_be_used_as_a_same_day_target`, `test_final_morning_entry_is_inside_day_only_before_0500` | Target selection excludes entries at the report boundary and at/after the next 05:00 day boundary. An entry at 04:59:59 remains a valid target. Later non-entry events do not prevent END_OF_DAY; report 8 has no target or target-time field. |
| Large interpolation prior makes L3 approach L2 | [test_baselines.py](../tests/test_baselines.py): `test_large_prior_approaches_l2_and_headline_excludes_late_reports` | With k=10^12, L3 and L2 losses agree within 10^-9 overall and in every available fold, scope and report. This prevents opposite fold errors from cancelling in an aggregate. |
| CV folds separate whole days | [test_baselines.py](../tests/test_baselines.py): `test_cross_validation_day_split_and_interpolation` | Training and test day sets are disjoint; each of 30 toy days appears in exactly one held-out fold. Known counting losses also check actual training counts. |
| Vocabulary remains 17 tokens | [test_event_exports.py](../tests/test_event_exports.py): `test_all_seventeen_events_have_descriptions_and_zone_context`; [test_simulator.py](../tests/test_simulator.py): `test_batch_of_twenty_passes_invariants` | All public tokens retain descriptions/zone fields, CAR_PASSED and END_OF_DAY are rejected as event tokens, and generated days retain the same vocabulary. |
| Same-seed reproducibility | [test_simulator.py](../tests/test_simulator.py): `test_same_seed_is_identical`, `test_day_index_uses_spawned_child`, `test_cli_worker_count_and_single_day_regeneration` | Exact agreement of events, GPS, hidden state, latents, traffic and reports, plus independent child-seed and worker/single-day regeneration checks. Different seeds still change GPS. |

## Additional strengthened check

`test_night_catnaps_enforce_minimum_real_duration_and_maximum_cycles` now covers
caps 1, 2, 3 **and 4**, retaining real event-duration and hidden-sleep assertions.
The existing completed-nap test still checks the original short duration limit.

Behavioral batches use fixed seeds and loose directional bounds, not exact event
counts or calibration percentages. Exact equality is appropriate for deterministic
schema, boundary and seed contracts. Toy-row interpolation checks use numeric
tolerances. Existing tests are reused rather than adding redundant simulation batches.
No knobs changed in S7, and no ML libraries were added.

## Verification

Focused test increment: **42 passed in 13.95s**. Final full suite: **189 passed in 36.42s**. All documentation links and 16 named test references were verified.

```sh
python -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_baselines.py tests/test_event_exports.py tests/test_simulator.py
python -m pytest -q
```

The older 200-day baseline ordering regression remains in the full suite; the
S7 mechanism checks use small batches or deterministic toy data. Final full-suite
results are recorded in PROGRESS.md.
