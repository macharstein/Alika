# Phase 3 S8.5 test coverage audit

All six requirements in `docs/UPDATE_SPEC_3.md` S8.5 are covered by tests added during S8.1–S8.3. S8.4 adds figure/provenance checks. This audit reuses those tests; it introduces no production changes, duplicate simulation batches, configuration changes or ML libraries.

## Required coverage

| S8.5 requirement | Existing tests | Evidence and limits |
| --- | --- | --- |
| Expected path-length ratio increases with boredom and decreases with urgency | [test_movement_style.py](../tests/test_movement_style.py): `test_expected_path_length_ratio_rises_with_boredom_and_falls_with_urgency` | Uses the same start/goal and 40 fixed seeds for each controlled condition. Both mean path-length-ratio differences exceed a loose 0.01 margin; urgent trips also have higher mean speed. This isolates the walking mechanism and does **not** assert the failed full-day population correlations. |
| Detour waypoints stay inside the map | [test_movement_style.py](../tests/test_movement_style.py): `test_detour_plan_bounds_and_zone_exclusions` | Exercises routes along all four map edges and an interior corridor; generated waypoints are in bounds, 0.4–1 km sideways, and respect exclusions where feasible. Detours are forced for this geometry test; a separate probability test covers normal stochastic occurrence. |
| Features use smoothed observed GPS only and ignore future data | [test_features_path.py](../tests/test_features_path.py): `test_trailing_five_minute_smoothing_changes_features_and_ignores_true_positions`, `test_future_gps_and_events_cannot_change_any_report_feature`, `test_report_features_do_not_read_hidden_state_or_latents` | Checks known rolling-average values and resulting speed; mutating true positions, deleting hidden state/latents, truncating the future and changing future GPS/events cannot affect features. A fix exactly at the report boundary can affect the recent window. |
| L4 runs and equals L3 for very large k | [test_baselines.py](../tests/test_baselines.py): `test_l4_learns_path_cue_on_same_folds_and_reports_fixed_ablations`, `test_l4_large_prior_equals_l3_in_each_fold_and_report`, `test_l4_zero_training_cell_is_exact_l3_and_bins_are_fixed` | A toy dataset with informative observed path shape improves L4; training/testing days remain disjoint. At k=10^12, losses agree within 10^-9 for every available fold, scope and report. Unseen cells equal L3 exactly. The toy case does **not** claim the real 500-day L4 target passed. |
| Schema bumped | [test_movement_style.py](../tests/test_movement_style.py): `test_style_reproducibility_schema_and_resume_contract` | Asserts manifest schema `lionsim-v5`, package major version 5, persisted style configuration, successful compatible resume and rejection of v4 manifests. |
| Same seed reproduces the same data | [test_movement_style.py](../tests/test_movement_style.py): `test_style_reproducibility_schema_and_resume_contract`, `test_trip_snapshot_has_independent_waypoints_and_exact_continuation`; [test_simulator.py](../tests/test_simulator.py): `test_same_seed_is_identical`, `test_day_index_uses_spawned_child`, `test_cli_worker_count_and_single_day_regeneration` | Exact GPS/hidden-state/event/latent agreement; child-seed/day-index and worker-independent regeneration; committed waypoint state survives snapshots without shared mutable arrays. |

## Supporting coverage

| Contract | Existing tests |
| --- | --- |
| Style stays frozen during travel/traffic waits; changes only on a new trip | [test_movement_style.py](../tests/test_movement_style.py): `test_trip_style_survives_bar_changes_and_traffic_wait_then_interrupts` |
| Stalking/chase mechanics and latent/traffic/report generation stay unchanged | [test_movement_style.py](../tests/test_movement_style.py): `test_style_coefficients_do_not_change_stalking_or_chase`, `test_style_changes_preserve_daily_latents_traffic_and_report_schedule` |
| Analysis trip diagnostics do not leak into public JSON/GPS | [test_movement_style.py](../tests/test_movement_style.py): `test_hidden_trip_diagnostics_match_true_path_and_do_not_enter_json` |
| CSV columns, finite/null semantics, worker/resume equivalence and checkpoint repair | [test_features_path.py](../tests/test_features_path.py): `test_csv_features_resume_workers_and_checkpoint_repair` |
| Full-state oracle resume matches the original at every report | [test_oracle.py](../tests/test_oracle.py): `test_original_rng_resume_reproduces_entire_day_at_every_report` |
| Observed/true trip alignment, interruptions, paired counts and hard failures | [test_trip_statistics.py](../tests/test_trip_statistics.py): `test_trip_geometry_uses_observed_smoothing_and_inclusive_endpoint`, `test_trip_targets_include_all_statuses_and_filter_only_urgency_straightness` |
| Every accepted-baseline status change is listed; missing formerly passing checks fail | [test_trip_statistics.py](../tests/test_trip_statistics.py): `test_reference_comparison_lists_all_changes_and_missing_passes_fail`, `test_comparison_cli_requires_matched_complete_run` |
| Text-free figure, exact regenerated provenance and stable pixels | [test_style_examples.py](../tests/test_style_examples.py): `test_examples_are_text_free_repeatable_and_match_recorded_trips`, `test_changed_source_and_wrong_version_do_not_publish_examples` |
| Text-free daily plots and exact contact-sheet tiles | [test_plot_annotations.py](../tests/test_plot_annotations.py): `test_pngs_have_only_filled_zones_path_and_endpoint`, `test_contact_sheet_is_exact_report_tiles_without_added_text` |
| Selected image days are generated and damaged artifacts repaired on resume | [test_resume.py](../tests/test_resume.py): `test_stats_explicit_images_are_limited_and_repaired_on_resume` |

## Verification

```sh
python -m pytest -x -q tests/test_movement_style.py tests/test_features_path.py tests/test_baselines.py
python -m pytest -q
```

Focused verification: **44 passed in 20.53s**. Final full suite: **233 passed in 53.86s**. Counts and execution times are also recorded in PROGRESS.md. Test names and linked files were checked against the repository. Every assertion in the required mapping exists; no test is skipped or replaced with a calibration success claim.

## Acceptance remains separate

S8.1–S8.5 implementation, evaluation, figures and coverage can be complete while calibration is not accepted. The fixed [S8.3 evaluation](PHASE3_S83_RESULTS.md) still reports walking 6.0955 h/day (>6), boredom–straightness −0.294315 (required ≤−0.35), selected-goal urgency–straightness 0.068929 (required ≥0.30), visible detours 6.9017% (required 10–30%), and L4 loss 2.0815% worse than L3 (required ≥2% improvement). Report-7 END_OF_DAY share changed from PASS to WARN. No coefficient or threshold was changed during S8.4/S8.5 to conceal these results.
