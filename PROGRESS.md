# Phases 1–2 complete; phase 3 S8.1–S8.5 delivered, acceptance unmet

Phase 3 status: S8.1–S8.5 delivered; bounded calibration package 5.4.0 evaluated on 500 seed-42 days and 100 oracle days. Walking and detour frequency now pass the required 500-day checks; boredom/straightness, urgency/straightness and L4 improvement still miss. Both oracle guardrails pass. Full suite: 236 passed. See docs/PHASE3_CALIBRATION_RESULTS.md. Acceptance remains unmet.

Scope: phase-one `docs/UPDATE_SPEC.md` tasks 1–10 are complete. Under `docs/UPDATE_SPEC_2.md`, S1–S5 are implemented and S6 evaluation is complete, including checkpoint/resume safety. Final 500-day statistics have eight calibration warnings; both oracle/L0 ratio checks warn. S7 regression audit is complete; all 189 tests pass. No calibration experiment has been applied.

- [x] 17-token event schema, internal traffic context, restored daily reports/latents
- [x] Seven usable next-zone targets and run-level targets.csv
- [x] Committed journeys, hunger/heat/traffic traces, bounded night naps
- [x] Statistical metrics, target checks and JSON/Markdown reports
- [x] Atomic output and per-day checkpoint/resume with 200-day execution chunks
- [x] Tests and final 200-day statistics check
- [x] Smoothed counting ladder and snapshot/resume oracle
- [x] Canonical learnability configuration, legacy aliases and resumable oracle CLI
- [x] Full acceptance coverage, timing edge-case fixes and measured README delivery

Existing text-free PNGs, per-day SeedSequence reproducibility, and image generation for every selected day are preserved. Parameter choices and observed target failures will be recorded in README.md after measurement.

in progress: phase 5 — inspect and finish inherited uncommitted tasks 1–5; no prior Git commits exist. Retaining the partial schema, simulator, statistics and atomic-resume implementation, updating obsolete tests and documentation rather than reverting it.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_event_exports.py tests/test_validation_rules.py tests/test_stats.py
next: verify inherited behaviour changes and resume, commit runnable phase 5, then implement task 6 only (no oracle).

done: phase 5 — retained and completed inherited tasks 1–5; atomic resume tests, 17-token reports, traffic context, targets, and statistics work. Relevant suites: 50 schema/stats/resume tests and 31 behaviour/road tests passed.
assumptions: bounded first hunt wait makes initially hungry days attempt hunting; staging moved to 17:00 and water-visit probability 0.65 added after the first diagnostic showed zero road entries. No target thresholds changed.
known problems: 200-day check has 19 PASS, 3 WARN, 0 FAIL; Road days 6.5%, resting 15.754h, walking 6.272h remain outside reference ranges. These are reported, not hidden.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: phase 6 — implement smoothed counting baselines with day-separated holdout and observable-history cues; no oracle.

in progress: phase 6 — add observable-history features to targets.csv, with no latent or future information. Preserve the original six columns and append four cue columns.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_validation_rules.py
done: phase 6 observable cue columns; 42 targeted tests passed. Exact report-boundary inclusion and future-event/latent independence are tested.
assumptions: shade hour is local clock hour of first observed ENTER_SHADE; absent is not_yet. Counts include events at the report timestamp.
known problems: none in cue export; phase 5 statistical warnings remain.
next: add Laplace counting baselines, sparse-cell backoff and report integration.
in progress: phase 6 counting baselines — deterministic 70/30 split by whole day, fixed nine target classes, Laplace smoothing, L3 sparse-cell backoff to L2. Integrate evaluation from the written targets.csv into JSON/Markdown stats.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_stats.py tests/test_resume.py
done: phase 6 counting ladder and CSV/report integration; 16 targeted tests passed, including a seeded 200-day finite/ordered-loss regression and resume equivalence.
assumptions: deterministic first 70% of sorted days train, last 30% test; alpha=1 across nine classes; unseen L1/L2 back off, L3 requires 10 training rows. Entropy uses test targets, losses use natural logs. No held-out tuning or forced loss ordering.
known problems: phase 5 road/rest/walking target warnings remain; README.pdf and performance_check.json are pre-existing historical artifacts and intentionally untouched.
next: run final 200-day report and full pytest, record measured baseline losses, commit phase 6 completion, then stop before task 7.


done: phase 6 final verification — full pytest: 143 passed in 29.95s. All source changes are committed in tested increments.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42
results: outputs/run_20261101_210910/stats_report.md and stats_report.json; 19 PASS, 3 WARN, 0 FAIL. L0=1.810101, L1=0.979962, L2=0.821198, L3=0.842583 nats; target entropy=1.800828; requested interpretation=learnable. L3 worsens loss by 2.60% versus L2; not tuned away.
known problems: road-entry days 6.5% (<10%); resting 15.754h (<16h); walking 6.272h (>5h diagnostic range). These remain honest warnings, not event-invariant failures. Historical README.pdf/performance_check.json remain untouched/untracked.
next: task 7 — oracle snapshot/resume evaluation (not started; await explicit phase instruction).

in progress: phase 7 — refactor the minute loop into resumable advances and deep-copy snapshots; verify exact original-RNG continuation and independent branches. Startup inspection found no partial source edits; historical README.pdf and performance_check.json remain untouched.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_simulator.py tests/test_road_dynamics.py
assumptions: snapshots hold the state before the report minute advances, including all completed minute history; oracle branches retain daily latents and committed schedules but resample unobserved future Poisson traffic.
next: finish and commit snapshot/resume support, then add the oracle evaluator and CLI.
done: phase 7 snapshot/resume — persistent minute buffers and independent deep copies reproduce the full original events, GPS, hidden state, traffic, latents and reports at all seven report boundaries. 40 relevant tests passed.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_simulator.py tests/test_road_dynamics.py
assumptions: retaining all recorded history preserves original end-of-day GPS noise draws exactly; oracle branches can advance without generating unused GPS tables.
known problems: baseline percentage warnings remain; no parameter tuning in this increment.
next: implement branched rollout probabilities and fair held-out oracle comparison.

in progress: phase 7 oracle — add deterministic snapshot-derived independent rollout streams, resample only future traffic, retain full-day rollout counts, and compare oracle and L0–L3 on identical held-out days. Add finite-sample interpretation thresholds to defaults.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py
next: integrate oracle into atomic per-day checkpoints and resume-aware CLI.
done: phase 7 oracle evaluator — five targeted tests pass, covering exact resumes, distinct repeatable branch seeds, traffic-prefix preservation, normalized Laplace probabilities, original-target matching and held-out comparison. No ML dependencies.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py
assumptions: near-zero means <=0.1 nats; close to L0 means relative absolute gap <=0.1; both defaults are configurable. Reports expose the Laplace floor and whether the near-zero threshold is resolvable. Existing minute-tick timing and strictly-future target semantics are retained.
known problems: small-rollout estimates have sampling uncertainty; scheduled wakes/durations are conditioned hidden state, while future traffic is resampled. Original statistical warnings remain.
next: phase 8 — integrate oracle CLI, manifests and per-day checkpoint/resume, then group learnability settings.

in progress: phase 8 CLI — wire oracle mode into existing atomic day checkpoints, aggregate reports and resume guards; bump version to 3.2.0 so runs cannot mix schemas. User has now authorized tasks 9–10 after tasks 7–8 are verified complete.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_resume.py
next: group learnability settings, audit task 9 coverage, then perform task 10 delivery without tuning warning percentages.
done: phase 8 oracle CLI — nine oracle/resume tests passed, including chunked continuation with two workers versus uninterrupted output, preserved checkpoint timestamps, --keep-files, manifest defaults/overrides, changed-rollout rejection and mode guards. Version 3.2.0 prevents mixing old runs.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_resume.py
assumptions: oracle mode writes statistics and probabilities without images or minute tables unless --keep-files is passed; --oracle-days defines the first N independent days. Existing --chunk-size bounds work per invocation.
known problems: percentage warnings unchanged; low-rollout pilots cannot resolve losses below their reported smoothing floor.
next: group the learnability knobs under the canonical learnability config object while accepting old file/CLI paths.

in progress: phase 8 config grouping — make learnability.behaviour, learnability.activity, learnability.chase, latent_ranges, softmax_temperature and chase_base_probability canonical. Preserve legacy JSON/--set aliases without duplicate runtime values; explicit canonical file values win, CLI overrides apply in order.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_config.py tests/test_oracle.py tests/test_behaviour_scenarios.py tests/test_validation_rules.py
next: full task 7–8 verification and oracle pilot, then tasks 9–10 audit and delivery.
done: phase 8 canonical configuration — 85 relevant tests passed. All requested learnability knobs are grouped and commented; legacy partial files and dotted CLI paths migrate, canonical file values take precedence, list overrides and CLI order work, and manifests contain no duplicate legacy controls. Simulation values were not tuned.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_config.py tests/test_oracle.py tests/test_behaviour_scenarios.py tests/test_validation_rules.py
assumptions: related activity durations and chase mechanics move with their learning controls to keep each setting in exactly one place; Python callers should read the canonical config paths.
known problems: original road/rest/walking warnings remain.
next: full pytest and a resumable 20-day x 100-rollout oracle pilot to close tasks 7–8, then audit task 9 and deliver task 10.

in progress: phase 8 final verification — full pytest plus a 20-day, 100-rollout-per-report oracle pilot in two 10-day chunks. This is a diagnostic pilot, not the full 100-day default experiment. No behavioral parameters changed.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --oracle --oracle-days 20 --oracle-rollouts 100 --seed 42 --workers 4 --chunk-size 10 --out outputs/oracle_pilot
next: record pilot output directory and resume its second chunk, then close tasks 7–8.
done: oracle pilot first chunk checkpointed 10/20 days in outputs/oracle_pilot/run_20261102_105202; no minute tables or images retained.
in progress: resume the same pilot for its remaining ten days.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/oracle_pilot/run_20261102_105202 --workers 4 --chunk-size 10
next: finish full tests, record oracle comparison and close tasks 7–8.
done: tasks 7–8 — full pytest: 161 passed in 34.95s. Resumed oracle pilot completed 20/20 days, 100 rollouts per usable report, 42 held-out targets. Saved outputs/oracle_pilot/run_20261102_105202/oracle_report.md and oracle_report.json.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
results: oracle=0.460304, L0=1.861813, L1=1.192013, L2=L3=1.318674 nats; balanced; smoothing floor=0.076227. This 20-day pilot does not establish large-sample calibration or baseline ordering.
assumptions: no behavioral values or target ranges changed in tasks 7–8; configuration paths moved only.
known problems: road/rest/walking warnings remain; task 9 audit found no dedicated goal-commitment or catnap-limit regressions yet.
next: task 9 — add missing commitment/nap regressions, audit oracle edge cases and verify the full acceptance suite; then task 10 delivery.

in progress: phase 9 — add controlled goal-commitment/interrupt tests, paired event and hidden-state nap duration/cycle assertions, explicit cutoff entries, and oracle report-boundary/invalid-checkpoint regressions. Existing schema/targets/stats/200-day baseline/seed tests are retained rather than duplicated.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_oracle.py
next: fix any discovered edge cases, run the full acceptance suite, then perform task 10's 200-day statistics delivery.
done: phase 9 missing regressions and fixes — 20 targeted tests passed. Added direct commitment/interrupt and missing-reason checks, configured nap cycle/minimum-duration tests, late-day short-nap prevention, explicit ENTER_HUNT cutoff checking, exact report-boundary oracle conditioning, and incomplete oracle-checkpoint recovery.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_oracle.py
assumptions: minimum nap duration applies to event timestamps as well as minute ticks. Wake seconds are bounded below by sleep-start seconds; fewer than a full minimum duration before day end produces quiet rest. Draw counts and default nap lengths remain unchanged.
known problems: tests exposed and fixed a 24m37s event-log nap despite 25 sleeping ticks, and oracle branches moving an already-observed zero-second entry into a future target. Version bumped to 3.2.1; prior 3.2.0 pilot remains historical and must not be resumed/mixed with corrected outputs. Behavioral target percentages were not tuned.
next: full pytest for phase 9, then rerun the corrected oracle pilot and required 200-day statistics in phase 10.

in progress: phase 9 final acceptance — full pytest after the targeted timing fixes; retain existing 200-day baseline ordering and seed/image regression coverage.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: task 10 — final 200-day report, corrected oracle pilot, README and explicit PASS/WARN/FAIL delivery.
done: phase 9 — full pytest: 170 passed in 33.44s. All task-9 acceptance areas are covered: 17-token/no-car/zone schema, future targets and END_OF_DAY, hunt cutoff, commitment and reasons, bounded real-duration naps, stats fields, 200-day baseline ordering, exact oracle resumes and seed/worker reproducibility.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
known problems: no failing tests; original statistical target warnings remain for honest measurement in task 10.
next: task 10 — run the required final 200-day check and corrected oracle pilot; update README with results, assumptions and reproducible commands.

in progress: phase 10 delivery — generate the required 200-day seed-42 report and a corrected version-3.2.1 oracle pilot, then update README with all measured statuses and assumptions. Do not adjust simulator values or diagnostic ranges to force passes.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --oracle --oracle-days 20 --oracle-rollouts 100 --seed 42 --workers 4 --chunk-size 10 --out outputs/oracle_verified
next: record output directories, resume the oracle pilot, update README and run final full pytest.
done: final 200-day run completed at outputs/run_20261102_105804; corrected oracle first chunk completed 10/20 days at outputs/oracle_verified/run_20261102_105804. README now documents canonical configuration, oracle assumptions, checkpoint commands and both timing fixes.
in progress: resume the corrected oracle pilot and read final PASS/WARN/FAIL measurements for README.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/oracle_verified/run_20261102_105804 --workers 4 --chunk-size 10
next: publish measured result tables in README, run final full pytest and commit delivery.
in progress: phase 10 report polish — remove a stale 'oracle not in this phase' definition and NumPy type wrappers from Markdown relative gaps; numeric losses and simulation outputs are unchanged. Regenerate aggregate reports from completed checkpoints afterward.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_baselines.py
next: refresh both completed reports, record results and finish documentation.
done: phase 10 reports/documentation — 14 relevant statistics/baseline tests passed. Refreshed aggregates atomically from existing checkpoints; final numeric results are unchanged. README now includes every target status, canonical settings/aliases, CLI and chunked oracle commands, assumptions, finite-rollout limits and both timing fixes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_baselines.py
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/run_20261102_105804
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/oracle_verified/run_20261102_105804
results: 200-day run: 19 PASS, 3 WARN, 0 FAIL; road days 6.5%, resting 15.754167h, walking 6.271583h. L0=1.810101, L1=0.979962, L2=0.821198, L3=0.842583. Corrected 20-day/100-rollout oracle pilot: oracle=0.460304 versus L0=1.861813 on the same 42 targets; balanced, floor=0.076227.
assumptions: no behavior/control values or target ranges changed to obtain passes; canonical grouping and evaluation defaults do not tune trajectories. Oracle pilot is not the full 100-day default workload.
known problems: three statistical warnings and L3's 2.60% regression versus L2 remain measured limitations. README.pdf and performance_check.json remain untouched.
next: run final full pytest, commit completion, then stop with tasks 1–10 complete.

in progress: phase 10 final verification — run the complete pytest suite after documentation/report delivery; inspect final working-tree status and commit phase completion.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: tasks 1–10 complete after final verification; stop and report the remaining measured warnings.

done: phase 10 final verification — full pytest: 170 passed in 33.17s. Tasks 1–10 are complete; tested increments and final results are committed. No new ML dependencies.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
results: outputs/run_20261102_105804/stats_report.md (200 days; 19 PASS, 3 WARN, 0 FAIL); outputs/oracle_verified/run_20261102_105804/oracle_report.md (resumed 20-day pilot, 100 rollouts/report, balanced). README contains the complete target table and measured limitations.
assumptions: canonical configuration paths and finite-rollout interpretation thresholds are documented; fixes enforce actual nap duration and preserve observed boundary entries without tuning percentages.
known problems: road days 6.5%, resting 15.754h and walking 6.272h remain outside reference ranges; L3 is 2.60% worse than L2 on the 200-day holdout. Historical README.pdf/performance_check.json remain untouched and untracked.
next: tasks 1–10 complete; no further phase scheduled.

in progress: phase 2 S1 — inspect clean source tree and implement day-disjoint cross-validation, per-report/headline losses, interpolated L3, and GPS noise measurements. No inherited source edits need finishing; the new user spec and historical PDF/performance artifacts are untracked.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_oracle.py tests/test_stats.py
assumptions: deterministic interleaved day folds (5, reduced only for tiny pilots); all reports are tested once. Headline reports default 1–5. Three cue bins mean absent/early/late shade, counts 0/1/2+ (catch remains binary in ordinary days). Schema/version changes prohibit resuming old distributions.
next: finish S1 measurement changes before changing traffic or patrol behavior; implement only S1–S4, not S5–S7 or their large final runs.
done: S1 cross-validation increment — 18 targeted tests passed. Five day-disjoint folds, per-report and headline fold mean/std, L3 interpolation, zero-cell rate and paired-day L3−L2 uncertainty diagnostics now replace the old split/backoff. Oracle aggregation uses the same fold weighting. Manifest schema is lionsim-v4, simulator 4.0.0.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_oracle.py tests/test_resume.py
known problems: GPS noise measurements and S2–S4 behavior changes are not yet implemented. Tiny pilot runs use min(5, days) folds and explicitly report that count.
next: S1 GPS noise reduction and path/apparent-speed diagnostics.
in progress: S1 GPS diagnostics — reduce default observation SD from 15m to 8m, add observed/true path inflation and raw versus five-minute-smoothed apparent resting speed. Rest includes sleeping and quiet rest; smooth windows crossing moving activity are excluded.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_config.py
next: complete full S1 verification and measure a 200-day baseline before S2.
done: S1 GPS increment — 53 relevant tests passed. Default GPS SD is 8m; pooled path inflation and raw/smoothed resting apparent speeds are reported with configured checks. Zero true displacement yields an explicit null ratio.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_config.py
assumptions: five-minute smoothing is displacement between consecutive trailing five-fix means; only five fully resting intervals contribute, avoiding activity-transition contamination.
known problems: no behavior targets adjusted yet; S1 200-day measurement and full suite pending.
next: verify full S1 and record its 200-day reference before traffic changes.
in progress: S1 final verification — full pytest and 200-day seed-42 measurement with unchanged behavior.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s1
next: record S1 results, then S2 traffic delays and daytime walking efficiency.
done: S1 complete — full pytest: 172 passed in 34.19s; 200-day baseline saved to outputs/phase2_s1/run_20261102_111250. Behavior remains unchanged; new CV/GPS metrics are available before S2 changes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s1
next: S2 — traffic delays that preserve destinations and explicit waterhole/abandonment targets.
in progress: S2 — default aversion waits 4–10 minutes with saved destination/activity; separate delayed_by_traffic activation counts. Retain optional retreat routing for compatibility, also without an abandonment. Increase afternoon water choice probability from 0.65 to 0.85 to make water visits more common; measure actual arrivals rather than force a quota.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_road_dynamics.py tests/test_behaviour_scenarios.py tests/test_stats.py tests/test_oracle.py
assumptions: waiting counts as quiet rest; only physiological or schedule interruptions abandon the preserved journey. No event tokens are added.
next: measure 200-day S2 results, then implement evening road choices in S3.
done: S2 traffic implementation — preserved-destination waits and separate delay counts implemented; aversion no longer logs a canceled trip. Optional retreat routing also retains its original destination. Water choice probability is explicitly raised to 0.85; actual daily arrivals remain stochastic.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_road_dynamics.py tests/test_behaviour_scenarios.py tests/test_stats.py tests/test_oracle.py
assumptions: temperature/fatigue/schedule interruptions may still cancel travel; any such interruption during a traffic wait logs the preserved goal. Schema unchanged within v4; simulator version 4.1.0 prevents cross-stage resume mixing.
known problems: S2 target achievement is not yet measured.
next: full S2 pytest and 200-day measurement before S3.
in progress: S2 final verification — 59 targeted tests passed; run full suite and 200-day seed-42 statistics.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s2
next: record S2 measurements and implement S3 evening/low-traffic road visits.
done: S2 complete — full pytest: 174 passed in 33.87s. Measurement: outputs/phase2_s2/run_20261102_111536. Traffic abandonment share=0 PASS; actual abandonments=1.065/day WARN; waterhole days=66% WARN; walking=6.251833h WARN; resting=15.753917h WARN. Delay replacement alone does not solve long scheduled routes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
known problems: remaining abandonments are schedule/temperature/fatigue; no thresholds were relaxed. S4 must shorten daytime wandering to make room for night patrols.
next: S3 — causal evening road goals, then S4 night patrol and daytime travel efficiency.
in progress: S3 — one eligible evening road decision weighted by boredom and already-observed daily traffic; suppress daytime entry odds, route to the nearest road boundary and add a bounded road-surface speed bonus. Add road timing/share/correlation checks.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_road_dynamics.py tests/test_stats.py tests/test_oracle.py
assumptions: low traffic uses observed car counts only; future car schedules cannot influence a road goal. Hunt/feeding commitments remain protected; night road destinations are transit opportunities.
next: measure S3 on 200 days and proceed to S4 without changing target ranges.
scope update: user now requests finishing S2/S3 work in progress and continuing through S4 and S5. S6 large oracle/final runs and S7 as a separate phase remain outside scope; relevant acceptance tests are included with each implemented increment.
done: S3 implementation — 51 targeted tests passed. Evening road odds increase with boredom and decrease with observed same-day traffic; unseen future cars do not affect these odds. Road travel targets the nearest boundary; on-road speed receives a bounded 0.2 km/h bonus. Timing/share/correlation targets are reported.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_road_dynamics.py tests/test_stats.py tests/test_oracle.py
assumptions: one favored road decision per eligible non-catch evening; base chance 0.9 × boredom, discount exp(-0.18 × cars above 9), daytime multiplier 0.05. These are initial explicit model choices, not fitted to held-out targets.
known problems: S3 target achievement still needs the 200-day check; walking/water targets from S2 remain unresolved.
next: full S3 verification and 200-day measurement, then S4 patrol plus daytime walking-budget changes.
in progress: S3 final verification — full pytest and 200-day seed-42 report.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s3
next: S4 night patrols with naps, preserving catch-night terminal sleep and the hunting cutoff.
in progress: S3 validation fix — full suite found a brittle single-day interruption fixture, and the 200-day run found illegal Road naps. Road visits now use quiet rest before onward travel; the commitment regression audits ten fixed days instead of requiring a particular day to be interrupted. Simulator 4.2.1 isolates the corrected distribution.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_road_dynamics.py
known problems: initial S3 measured 8% Road days, 81.25% evening entries, 12.5% tourist-window entries, correlation -0.243. Timing improved, but frequency/correlation targets remain misses; the failed run is historical, not final validation evidence.
next: finish S3 verification before S4; keep sleep-location invariants unchanged.
done: S3 correction — 41 behavior/road tests passed; added hard validation to the fixed-seed road-reachability batch. Road stops preserve the original rule that sleep occurs only at safe resting zones.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_road_dynamics.py
next: full corrected S3 suite and measurement, then S4.
in progress: corrected S3 final verification — full pytest plus a fresh 200-day run; do not reuse failed v4.2.0 checkpoints.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s3_verified
next: S4 plan — draw 1–3 night destinations (mostly 2–3), use 60–110-minute naps at Plain/Den and quiet rests at visit zones, terminal sleep after a catch; constrain new voluntary daytime travel, favor shorter nearby goals and bound a faster cruise pace within 2–4 km/h. Finish heat-bound water trips rather than redirecting them to Shade; a short hunt-start grace avoids needless water turnbacks. Record all resulting knob changes and targets.
done: corrected S3 complete — full pytest: 176 passed; fresh 200-day run verifies hard invariants. Road timing improves but frequency/correlation and walking/water targets are still measured warnings, to be re-evaluated after S4.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s3_verified
next: S4 night patrol implementation, followed by S5 cross-time links as newly requested.
in progress: S4 — finite 1–3-destination night plans, long enough pauses to spread entries across late reports, naps only at safe zones, quiet rest/playing at other visits. Preserve catch-night terminal sleep. Reduce voluntary daytime wandering, retain bounded state-dependent pace, and stop diverting a hot lion away from its cooling water destination.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_road_dynamics.py tests/test_stats.py tests/test_oracle.py
assumptions: 1–3 planned destinations may include incidental zone crossings; all actual entries are measured. A maximum four nap cycles does not require four naps. Daytime travel budget prevents new voluntary journeys, never cancels an underway trip.
next: measure S4; explicitly document any remaining misses, then implement S5 latent/observable time links.
done: S4 initial implementation — targeted night-patrol, catch-sleep, cutoff, water-trip, road, stats and oracle tests pass. Night plans choose 1/2/3 destinations with probabilities 0.10/0.35/0.55; pauses are 65–115 minutes and safe-zone naps are capped at four. Non-safe visit zones use quiet rest, never invalid sleep events.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_road_dynamics.py tests/test_stats.py tests/test_oracle.py
assumptions: daytime voluntary-travel budget=120 minutes; nearby-goal distance penalty 0.3→0.8; patrol cruise fraction=0.35 within the same 2–4 km/h range. Existing trips finish; shade/water/hunt schedules override the voluntary budget. Hot water-bound lions continue toward water; hunt-start grace for finishing water travel is at most 30 minutes. These explicit changes aim to reserve night walking time, not relax targets.
known problems: combined S4 target achievement has not yet been measured.
next: measure and fully verify S4, then S5 cross-time links.
in progress: S4 final measurement and acceptance — full pytest and 200-day seed-42 run; inspect warnings before any additional changes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s4
next: record S4 results, then implement S5 and stop before S6.
done: S4 first full verification — 178 passed in 35.28s; outputs/phase2_s4/run_20261102_195237 has 0 hard validation failures. Walking fell from 6.252h (S2) to 5.158750h; waterhole days rose to 94%; entries=6.75/day, events=21.52/day; report-6 END_OF_DAY=37%. These remain target misses, not concealed passes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
known problems: added night water visits plus protected daytime water travel make water coverage too high; Road days remain 8.5%, correlation -0.294. More night structure reduced early report dominance but overall entry/event targets are not yet met.
next: one documented S4 adjustment before S5 — water-choice probability 0.85→0.75 to preserve day variation; cruise fraction 0.35→0.50 to reduce walking time while preserving state effects; Road low-volume reference 9→14 observed cars to make low-traffic night visits less rare; daytime road multiplier 0.05→0.01 to suppress tourist-window entries. Do not change target ranges.
in progress: S4 measured adjustment and re-verification; S5 will subsequently add the requested morning scouting route and latent timing links.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_road_dynamics.py tests/test_oracle.py
done: S4 adjustment — targeted behavior/road/oracle checks passed with the documented four knob changes; no reference ranges changed. Night patrols remain causal and bounded, and older checkpoint versions cannot be mixed with v4.3.1.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_road_dynamics.py tests/test_oracle.py
next: complete S4 full verification, then S5 morning scouting, hunger-linked waking and prey-linked hunt timing.
in progress: final S4 verification on adjusted defaults.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s4_verified
next: S5 implementation, followed by measured correlations and headline CV improvement.
done: S4 complete — adjusted-default full pytest: 178 passed in 34.36s. Fresh 200-day run at outputs/phase2_s4_verified/run_20261102_195807 completes without hard validation errors; actual warnings remain in its report. Both pre-adjustment and adjusted runs are retained for comparison.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s4_verified
next: S5 cross-time links and final S1–S5 documentation, not S6 large runs.
in progress: S5 — prey-linked morning Kopje scouting dwell (20–95m plus 8m noise), followed by Plain staging; hunger shifts waking earlier up to 30m with wake SD reduced 30→20m and the same 05:00–07:00 clip; low prey delays hunt departure up to 45m, high prey starts at 18:30. Add measured correlations and >=3% headline L3 improvement check. Existing heat coefficients remain unchanged.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_cross_time.py tests/test_behaviour_scenarios.py tests/test_oracle.py tests/test_stats.py tests/test_baselines.py
assumptions: first Kopje-to-next-entry gap is measured where a later entry exists, including travel; missing gaps stay null. The 22:00 cutoff is unchanged. Scouting stays observable through pauses and timing, not new tokens or exposed hidden latents.
next: measure S5 on 200 days, record all targets and any misses, update README, full pytest and commit completion.
done: S5 initial implementation — 41 targeted tests passed, including controlled latent comparisons, measured correlation directions, behavioral invariants, oracle exact resumes, and cross-validated baselines. Scouting and delayed hunts remain within the unchanged event vocabulary and hunting cutoff.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_cross_time.py tests/test_behaviour_scenarios.py tests/test_oracle.py tests/test_stats.py tests/test_baselines.py
assumptions: scouting choice probability=0.9; prey normalization uses fixed [0.5,1.5] references so counterfactual latent ranges do not erase effects. Hungrier waking shifts by 30m × hunger; wake noise is 20m. Low prey adds up to 45m of stationary pre-hunt waiting, not a canceled trip.
known problems: final 200-day S5 threshold achievement still needs measurement; no claim that all S1–S4 target misses are fixed.
next: full S5 suite and 200-day report; document final measurements/knob changes, then stop before S6.
in progress: S5 final measurement — full pytest and 200-day seed-42 statistics. S6's 100-day oracle and 500-day final runs are intentionally not started.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s5
next: update README and PROGRESS with final S1–S5 outcomes and exact reproduction commands.
done: initial S5 full verification — 181 passed in 35.42s; outputs/phase2_s5/run_20261102_200237: 33 PASS, 7 WARN, 0 FAIL. S5 correlations all pass: prey/dwell=0.8563, prey/chase=-0.6146, hunger/wake=-0.3749, heat/shade=-0.6638; headline L3 improves on L2 by 13.25%.
known problems: initial combined run still misses total entries/events, Den/Road entry share, sequence uniqueness, traffic/road correlation and walking hours. These are calibration limits, not hidden failures.
in progress: final S4 nap-limit audit — restore the original 20–60m catnap draw with the 25m minimum; retain the 65–115m total stop as nap plus quiet rest. This preserves short naps while spreading patrol entries over the night. No target ranges change. Add an event-duration regression and rerun final measurements.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_oracle.py
next: final S1–S5 report and README, then stop before S6.
done: nap-limit audit — short naps are separate from total stop duration, with exact resume coverage and a new 25–60m completed-nap regression. Terminal sleep still extends to morning. Simulator version 4.4.1 prevents mixing earlier patrol-stop semantics.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_oracle.py
next: final S5 full verification, 200-day measurement and documentation.
in progress: final S1–S5 documentation and report wording — explain schema/distribution change, CV/interpolation, all changed knobs and measured misses; correct obsolete report scope/bound language without altering numeric calculations.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_resume.py
next: final full pytest and 200-day run with v4.4.1; report results and stop before S6.
done: report/documentation wording — 12 stats/resume tests passed; CV entropy and gaps remain visible, sequence-bound wording matches phase-two inclusive targets, and resume help describes the current schema. README now marks old measurements as historical and explains current CV/interpolation.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_resume.py
next: final v4.4.1 full suite and 200-day check, then attach final results and all knob changes to README.
in progress: final v4.4.1 acceptance — full pytest and final 200-day S1–S5 report with restored short-nap bounds.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s5_verified
next: final measurement table and concise delivery; S6/S7 remain unstarted.
done: final v4.4.1 verification — full pytest: 182 passed in 35.92s. Final 200-day report: outputs/phase2_s5_verified/run_20261102_200914; 33 PASS, 7 WARN, 0 FAIL, all hard day invariants valid. Headline L3=0.609133 versus L2=0.702174, a 13.25% improvement. All four S5 correlations pass.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 200 --seed 42 --out outputs/phase2_s5_verified
known problems: 7.435 entries/day, 18.51 events/day, Den share 2.488%, Road share 1.479%, sequence uniqueness 44.5%, traffic/Road correlation -0.3010 and walking 5.793667h remain outside the requested ranges. No target bounds were relaxed. S1–S5 mechanisms are implemented; calibration targets are not all achieved.
in progress: final documentation — commit the full target table, per-report CV table, all changed configuration values and explanations, and final reproduction commands. This is documentation only; runtime code is already fully verified.
next: S6 — 100-day oracle and 500-day final run (not started); seven calibration warnings remain.

done: final S1–S5 delivery documented in README.md and docs/PHASE2_RESULTS.md, including every changed setting, intermediate trials, full target table, per-report CV losses, reproduction commands and explicit remaining warnings. Historical README.pdf/performance_check.json remain untouched and untracked.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q (182 passed in 35.92s; no runtime changes after this verification)
results: outputs/phase2_s5_verified/run_20261102_200914/stats_report.md; 33 PASS, 7 WARN, 0 FAIL; headline L3 improvement=13.25%; all four S5 correlations pass.
known problems: calibration is not complete; walking and entry/event density targets still miss, along with Den/Road shares, uniqueness and traffic/Road correlation. No claim is made about S6 oracle ratios or a 500-day final evaluation.
next: S6 — 100-day oracle and 500-day final run (not started); seven calibration warnings remain.

in progress: phase 2 S6 reporting — startup found no partial source edits; historical README.pdf/performance_check.json remain untouched. Add fold-matched headline/all-report oracle comparisons and S6 target checks. Apply the ratio/headroom targets to both scopes; no behavior parameters will change.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_config.py
next: commit reporting, support explicit first-three-day images in stats mode, then run the 100-day oracle in 20-day chunks and 500-day statistics in 100-day chunks.
done: S6 oracle reporting — headline and all-report losses use the same equally weighted day folds as L0–L3, with fold standard deviations and separate ratio/headroom checks in both Markdown reports. Added target defaults 0.25–0.50 and 10%, strict config checks, and unequal-fold/headline/interpretation regression coverage; 65 relevant tests passed.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_config.py tests/test_stats.py
assumptions: S6 supersedes the old absolute near-zero/near-L0 interpretation; retain the old near-zero setting only as a smoothing-resolution diagnostic. Recommendations do not alter behavior.
known problems: seven S5 calibration warnings remain; no S6 experiment has run yet.
next: allow explicitly selected images in statistics mode without saving minute tables.
in progress: S6 image selection — let --stats-only --image-days K explicitly render the first K days, while defaults still produce no images or minute files. Track PNGs in checkpoints so missing images regenerate on resume; bump package version to 4.5.0 for the reporting/output contract, without changing trajectories.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_resume.py tests/test_oracle.py
next: run the 100-day oracle in five 20-day chunks.
done: S6 explicit image selection — 13 resume/oracle tests passed. Stats/oracle modes remain image-free by default, but explicit --image-days K now writes only selected PNGs, with checkpoint file validation and missing-image repair; no minute files are needed. Package version is 4.5.0; simulation behavior and seeds are unchanged from 4.4.1.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_resume.py tests/test_oracle.py
assumptions: --no-images still overrides an explicit image limit; image selection is immutable on resume.
known problems: S5 calibration warnings are unchanged.
next: first 20 days of the 100-day × 100-rollout oracle, then four resumptions.
in progress: S6 oracle experiment — 100 independent days, 100 rollouts for each of seven usable reports, seed 42, four workers, five invocations of at most 20 days. No model tuning; reports use the S6 ratio/headroom checks in both scopes.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42 --workers 4 --chunk-size 20 --out outputs/phase2_s6_oracle
next: record the output directory and resume after each completed 20-day chunk.
done: S6 oracle chunk 1 — completed 20/100 days in outputs/phase2_s6_oracle/run_20261102_202029. Continuing session inspected the uncommitted experiment log and retained it; no partial source edits exist.
in progress: S6 oracle chunk 2 — resume days 21–40 using existing checkpoints, with unchanged configuration and 100 rollouts/report.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_oracle/run_20261102_202029 --workers 4 --chunk-size 20
next: resume the remaining oracle chunks before the final 500-day statistics run.
in progress: S6 documentation — update the CLI image defaults and oracle interpretation to match the tested reporting contract while the experiment runs. Keep S1–S5 results labeled as the historical 200-day measurement.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py
next: complete all oracle chunks and record final results before running 500 days.
done: S6 oracle chunks 1–2 and documentation — 40/100 days checkpointed; README now matches explicit image selection and S6 scope/interpretation. Oracle regression suite: 10 passed.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py
assumptions: partial oracle results are provisional; no behavior or target tuning.
known problems: early oracle/L0 ratios are below 0.25; full 100-day result is pending.
next: S6 oracle chunk 3, days 41–60.
in progress: S6 oracle chunk 3 — resume days 41–60 from the saved run.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_oracle/run_20261102_202029 --workers 4 --chunk-size 20
next: finish the final two oracle chunks, then 500-day statistics.
done: S6 oracle chunk 3 — 60/100 days checkpointed; no model changes or failed hard invariants.
in progress: S6 oracle chunk 4 — resume days 61–80 with the same configuration.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_oracle/run_20261102_202029 --workers 4 --chunk-size 20
next: last 20-day oracle chunk, then final statistics.
done: S6 oracle chunks 3–4 — 80/100 days checkpointed; 10 oracle tests passed after resumption. No model changes; hard validation remains valid.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py
assumptions: all 100 days will be compared on identical folds before final interpretation.
known problems: provisional oracle ratio warnings remain.
next: final oracle chunk, days 81–100.
in progress: S6 oracle chunk 5 — complete days 81–100, then inspect both oracle loss scopes and target checks.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_oracle/run_20261102_202029 --workers 4 --chunk-size 20
next: start final 500-day stats run in 100-day chunks with --image-days 3.
done: S6 oracle experiment — all 100/100 days completed with 100 rollouts/report and valid hard invariants. First 80 days' target rows were also compared exactly with the prior S5 run; reporting/output changes preserve the simulation distribution.
assumptions: the oracle conditions on hidden drives and commitments, whereas counting baselines use observable history; comparisons use the same 100 days/folds within each scope.
known problems: both oracle/L0 ratios are below 0.25, so the requested diagnosis is too deterministic. Both oracle improvements over L2 pass. Proposed experiment: increase learnability.softmax_temperature, then remeasure; not applied in S6.
in progress: S6 final statistics chunk 1 — 500 days total, chunks of 100, seed 42, PNGs only on days 1–3, no minute tables.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 500 --seed 42 --workers 4 --chunk-size 100 --image-days 3 --out outputs/phase2_s6_final
next: record the final-run directory and resume four more 100-day chunks.
done: S6 final statistics chunk 1 — 100/500 days saved in outputs/phase2_s6_final/run_20261103_085841. Oracle final losses: headline 0.440580 versus L0 1.796986/L2 0.813254; all reports 0.412754 versus L0 1.868136/L2 0.873345. Ratios 0.245177/0.220944 WARN; L2 improvements 45.825%/52.739% PASS.
known problems: Matplotlib emitted sandbox font-cache warnings while rendering; generation completed successfully. PNG count and visual inspection will verify output before delivery. Model calibration warnings remain.
next: resume statistics chunks 2–5 and inspect the first-three-day images.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_oracle.py tests/test_resume.py (13 passed in 14.14s)
assumptions: font cache warnings are environmental; completed PNGs are still checked as artifacts. No rerun or cache-location change is needed if they are intact.
in progress: S6 final statistics chunk 2 — resume days 101–200; saved image selection remains days 1–3 only.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_final/run_20261103_085841 --workers 4 --chunk-size 100
next: statistics chunks 3–5, then final tests and delivery.
done: S6 statistics chunk 2 — 200/500 days checkpointed. All 27 PNGs decode; the day-1 contact sheet was visually checked and contains only zones, paths and endpoints. No corrupt images resulted from font-cache warnings.
in progress: S6 statistics chunk 3 — resume days 201–300.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_final/run_20261103_085841 --workers 4 --chunk-size 100
next: remaining 200 statistics days, final artifact audit and full pytest.
done: S6 statistics chunk 3 — 300/500 days checkpointed; hard validation remains valid.
in progress: S6 statistics chunk 4 — resume days 301–400.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_final/run_20261103_085841 --workers 4 --chunk-size 100
next: final 100 statistics days, aggregate audit and full pytest.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_stats.py tests/test_resume.py (13 passed in 1.62s)
assumptions: earlier partial reports are replaced atomically after each chunk; only the completed 500-day report will be used for delivery.
known problems: walking remains above five hours; final target statuses await all 500 days.
done: S6 statistics chunk 4 — 400/500 days checkpointed with valid hard invariants.
in progress: S6 statistics chunk 5 — complete days 401–500, audit checkpoint artifacts and unchanged targets, then record final loss/target tables and every changed knob.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase2_s6_final/run_20261103_085841 --workers 4 --chunk-size 100
next: final artifact verification, full pytest and S6 results documentation.
done: S6 final statistics — completed 500/500 days in five resumable chunks. Artifact audit verified all 600 checkpoints, 70,000 oracle continuations, matching 100-day oracle/statistics targets, exact S5 target equality for the first 200 days, all hard invariants, no minute files, and exactly 27 PNGs.
in progress: S6 delivery — publish final 500-day PASS/WARN/FAIL and per-report tables, separate 100-day oracle comparison, all S1–S5 knob changes and the two new S6 evaluation targets. Run the complete pytest suite before final commit.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: record final test result, commit S6 completion, then stop before S7.
done: S6 final delivery — full pytest: 185 passed in 37.96s. Completed the 100-day × 100-rollout oracle in 20-day chunks and 500-day statistics in 100-day chunks; all hard invariants pass. The final tables, full knob history, oracle interpretation, exact reproduction commands and image audit are in docs/PHASE2_S6_RESULTS.md and linked from README.md.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
results: outputs/phase2_s6_final/run_20261103_085841/stats_report.md — 32 PASS, 8 WARN, 0 FAIL; headline L3=0.618180 versus L2=0.667712, a 7.418% improvement. Exactly 27 text-free PNGs cover only days 1–3. Oracle results: outputs/phase2_s6_oracle/run_20261102_202029/oracle_report.md — headline 0.440580 nats, overall 0.412754; both L2-headroom checks PASS, both oracle/L0 ratio checks WARN.
assumptions: no behavioral or noise parameters were changed in S6; the two added target defaults implement the requested oracle bounds. Softmax-temperature adjustment is only a proposed future experiment. Same-seed target equality with S5 was verified across the first 200 days. S7 remains a separate audit, not implicitly completed by this delivery.
known problems: 500-day warnings are entries/day 7.392, events/day 18.198, Den share 2.8139%, Road share 1.6775%, uniqueness 30.8%, traffic/Road correlation -0.3438, report-6 END_OF_DAY 37%, and walking 5.759367h. Oracle/L0 ratios 0.245177 and 0.220944 imply too deterministic under the requested criterion. Nonfatal sandbox font-cache warnings did not damage images. Historical README.pdf/performance_check.json remain untouched.
next: S7 — audit the requested fixed-seed regression coverage; S6 is complete and calibration warnings remain.

in progress: phase 2 S7 coverage audit — read both specs, progress and Git history/status. No partial source edits exist; retain historical untracked README.pdf/performance_check.json untouched. Existing tests cover all requested areas, but strengthen non-vacuous feast-night coverage, the four-cycle nap limit, every-fold large-k interpolation, exact 05:00 target exclusion and same-seed traffic/report reproduction. Do not change simulator settings or distribution.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_baselines.py tests/test_event_exports.py tests/test_simulator.py
assumptions: reuse working fixed-seed regressions instead of duplicating simulation batches; exact assertions apply to deterministic contracts, while behavior rates retain loose bounds.
next: commit the focused test increment, document the S7 coverage map, run full pytest, and stop with phase 2 complete.
done: S7 focused regression increment — 42 relevant tests passed. Strengthened the existing batch to require feast cases, exercised nap caps 1–4, checked large-k interpolation in each fold/scope/report, extended identical-seed comparison to traffic and complete reports, and added three end-boundary cases at 04:59:59, 05:00:00 and 05:00:01.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_behaviour_scenarios.py tests/test_baselines.py tests/test_event_exports.py tests/test_simulator.py
assumptions: 05:00 belongs to the next simulation day for targets, and report 8 stays unlabeled. Behavior checks retain existing fixed seeds and loose rate bounds; no exact stochastic outputs are pinned.
known problems: no test failures or runtime changes; the eight S6 calibration warnings and two oracle ratio warnings remain.
next: document all nine S7 requirements against named tests, run full pytest, and commit completion.
in progress: S7 final audit/documentation — map each requested regression to its existing or strengthened test, explain deterministic versus statistical assertions, and run the full suite. No new config settings, ML dependencies, model changes or large evaluation reruns are needed for this test-only phase.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: record the full-suite result and commit phase 2 completion; stop without starting a calibration experiment.
done: phase 2 S7 — all nine requested areas are covered and documented in docs/PHASE2_TEST_COVERAGE.md. Full pytest: 189 passed in 36.42s. Documentation links and 16 named test references were verified. The focused regression changes were committed separately; this final checkpoint records the complete audit and phase status.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
assumptions: existing S1–S6 tests satisfy requirements where they already exercise the intended behavior; S7 strengthens gaps instead of adding redundant batches. No runtime changes, new settings, dependencies, schema/version changes or calibration tuning were made, so S6 measurements remain current.
known problems: the eight 500-day statistical warnings and two oracle/L0 ratio warnings remain documented in docs/PHASE2_S6_RESULTS.md. Historical README.pdf/performance_check.json remain untracked and untouched. No test failures or partial edits remain.
next: Phase 2 S1–S7 complete; await a new task before changing calibration parameters.

in progress: phase 3 S8.1 — read UPDATE_SPEC_3.md, progress and Git history/status; no partial source edits exist. Tagged accepted commit 3de4f5a as v4.5.0 before changes. Implement only trip-frozen movement style and its tests; S8.2 features, S8.3 calibration/L4 and S8.4 figures remain outside scope. Track the supplied new spec; historical PDF/performance files remain untouched.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_config.py
assumptions: base attraction is existing 1-heading_persistence and base turning noise is existing walk_heading_sd_degrees; put new coefficients under movement_style without retuning either base. Low mood adds 0.2 to the clipped turn multiplier. Preserve existing patrol speed bounds after multiplying. Planned straightness is chord/polyline length through accepted waypoints to the initial goal target; realized straightness is actual start-to-current chord / accumulated true path, finalized at arrival, interruption or day end. Trip-start bars and style stay fixed through traffic delays.
next: implement and commit pure movement-style planning/config tests, then integrate trip lifecycle and hidden diagnostics, bump schema/version, and verify the full suite.
done: S8.1 planner/config increment — 60 relevant tests passed. Added trip-start urgency/style formulas, documented coefficients, bounded 1–2-waypoint planning, validation and fixed-seed formula/probability/edge geometry tests. Existing movement code is not yet wired to the planner.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_config.py
assumptions: waypoint placement alternates sides, rejects out-of-map points instead of clipping offsets, prefers unrelated-zone clearance, and falls back to an in-map point only if clearance is infeasible. If no point fits, omit it. Zero-length paths have undefined (null) straightness.
known problems: initial test incorrectly required exclusion even where geometry makes it unavoidable; corrected to enforce exclusion in the open corridor and map/offset bounds at all edges. No runtime behavior has changed in this increment.
next: integrate frozen trip lifecycle, true-path diagnostics and schema/version bump; test movement directions, traffic continuation, interruption, exact resumes and hidden-file export.
in progress: S8.1 simulator integration — attach one frozen style to each committed walking trip, retain it across traffic responses, and close it at arrival/interruption/day end. Log causal cumulative straightness each minute and mark the final trip row; keep diagnostics in hidden_state only. Preserve stalking/chase movement and event state-machine rules. Bump package to 5.0.0 and manifest schema to lionsim-v5.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_oracle.py tests/test_road_dynamics.py tests/test_behaviour_scenarios.py
next: resolve implementation failures without retuning accepted phase-two defaults; then full pytest and S8.1-only delivery.
done: S8.1 integration — 78 relevant tests passed, including exact oracle continuation, traffic responses, existing night/hunt rules, trip diagnostics/export, schema/resume guards, reproducibility, unchanged latent/traffic generation, and isolated stalking/chase equivalence. Package is 5.0.0; manifest schema is lionsim-v5; README explains old-seed incompatibility and historical phase-two measurements.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_oracle.py tests/test_road_dynamics.py tests/test_behaviour_scenarios.py
assumptions: style applies to committed goal travel; temporary road-response movement keeps its established mechanics while sharing the original trip ID/path accounting. Goal attraction modifies bearing correction independently of noise, preserving the legacy perturbation scale; otherwise increasing urgency also amplified noise and inverted the required direction. Turning style, speed multiplier and detour plan are fixed until the trip ends. Completed statistics are on the final trip row, not retroactively copied across earlier rows.
known problems: changed paths made all twelve days in an old small traffic batch respond; replaced its incidental requirement for a response-free day with checks that each day retains non-response activity and several days respond. No behavior defaults were retuned. S8.3 population calibration/guardrails have not been evaluated or claimed complete.
next: commit the runnable integration, document trip fields and edge cases, then full pytest and stop after S8.1.
in progress: S8.1 final documentation and acceptance — document frozen style formulas, per-trip hidden fields, nullable straightness, bounded waypoint fallbacks and retained traffic/stalking/chase behavior. Run the full suite; do not add path features, L4, example figures or retune calibration.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: fix any genuine regression, record full-suite result, and commit S8.1 completion only.
done: phase 3 S8.1 — full pytest: 212 passed in 41.10s. Accepted baseline tag v4.5.0 points to 3de4f5a. Package 5.0.0/schema lionsim-v5 adds frozen movement style, bounded detours and per-trip hidden-state diagnostics; README and docs/MOVEMENT_STYLE.md document formulas, lifecycle, edge cases and old-seed incompatibility.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
assumptions: all 18 new settings live under movement_style; exact comparison against the tag verified every existing default unchanged. Plotting, report and event modules also match the accepted tag. Tests verify directional path effects, same-seed and snapshot continuation, and unchanged stalking/chase mechanics. No ML dependencies added.
known problems: S8.3 population correlations and guardrails are not yet evaluated; old phase-two statistics are historical. No failing tests or partial implementation edits remain. Historical README.pdf/performance_check.json remain untouched.
next: S8.2 — user requested continuation of phase 3 during final S8.1 verification; implement observed-GPS path features as the next task, before L4/calibration/figures.
in progress: phase 3 S8.2 feature calculations — continue with the next task only after the user's continuation request. Compute causal trailing five-minute smoothing and five path metrics. Detect completed inter-zone trips from observed departures and already-emitted ENTER events, never hidden trip IDs, goals, latents or true coordinates; document this observable approximation to hidden trip boundaries.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_path.py tests/test_config.py
assumptions: start a trip at a sustained observed departure beyond the previous zone (50m margin, two consecutive minutes); end at a subsequent public zone-entry event. Use the last GPS fix at/before the event, never interpolate with a future fix. Five-minute trailing smoothing uses available history during initial warmup. Area is occupied 0.25km cells times cell area, not a convex hull. Missing/undefined values remain null, not invented zeros.
next: commit independently tested feature functions, append ten columns to targets.csv with resume/version protection, then full tests; leave S8.3/L4 and figures for the following task.
done: S8.2 feature calculations — 55 feature/config tests passed. Added trailing observed-only smoothing, straightness, elapsed-time mean speed, circular variance of turns, chord-deviation distance and occupied-grid area; last completed observed trip and recent three-hour windows are causal. Tests cover known geometries, stationary/empty paths, smoothing, trip completion timestamps, future mutation/truncation, true-position independence and invalid settings.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_path.py tests/test_config.py
assumptions: smoothing lag must first register the source zone before a departure can begin; this avoids treating delayed GPS entry as an immediate new departure. An observable trip is an inter-zone approximation, not hidden simulator segmentation. Only five new features_path settings were added; no behavior settings changed.
known problems: no failing tests; CSV integration remains pending. S8.3 correlations, L4 and guardrails remain outside this step.
next: integrate ten feature columns into target checkpoints/CSV, bump export-compatible package version, test resumed and multi-worker exports, then full suite.
in progress: S8.2 CSV/checkpoint integration — append five last_trip and five last_3h metrics to the existing target columns. Keep daily JSON/reports unchanged. Reject incomplete feature checkpoints and regenerate only affected days. Bump package to 5.1.0 (schema remains v5) so pre-feature runs cannot silently resume with a different CSV contract; simulator distribution stays 5.0.0.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_path.py tests/test_resume.py tests/test_oracle.py
next: document observed trip segmentation and feature units/nulls, run full pytest, and stop before S8.3.
done: S8.2 CSV integration — 25 feature/resume/oracle tests passed. Ten numeric-or-null feature columns follow the original target columns; daily JSON and report payloads remain unchanged. Checkpoints validate feature presence/finite values, missing-feature recovery regenerates only the damaged day, and resumed/two-worker output matches uninterrupted output byte-for-byte. Package 5.1.0 protects the extended CSV contract while retaining schema v5 and 5.0.0 trajectories.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_path.py tests/test_resume.py tests/test_oracle.py
assumptions: valid unavailable metrics serialize as JSON null / blank CSV fields, distinct from absent checkpoint keys. The final report remains excluded. No path features enter L0–L3; L4 belongs to S8.3.
known problems: no failing tests; observed trip boundaries are approximations to hidden committed trips and must be identified as such in documentation. S8.3 calibration remains unperformed.
next: final feature documentation, full suite and S8.2 completion checkpoint.
in progress: S8.2 final documentation/acceptance — document feature formulas/units, observed trip segmentation, trailing-window boundaries, nulls and version compatibility. Run the full suite, including inherited image/event/reproducibility and baseline checks; do not implement L4 or run S8.3 calibration.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: record final results, commit S8.2 completion, and stop before S8.3.
done: phase 3 S8.2 — full pytest: 224 passed in 56.13s. Package 5.1.0/schema v5 exports ten observed-path features to targets.csv, with causal smoothing, observable completed-trip detection, explicit null semantics and atomic checkpoint recovery. README, docs/PATH_FEATURES.md and movement documentation explain the interface, boundary approximation and export compatibility.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
assumptions: the completed-trip feature is an observable inter-zone segment, deliberately independent of hidden trip labels. Numeric path features use only smoothed observed coordinates at/before report time. Exact comparison against completed S8.1 verified all previous defaults, simulator/style logic and report/event/PNG modules unchanged; only five features_path settings were added. S8.3 must distinguish observable segmentation from ground-truth trips when evaluating correlations.
known problems: no test failures or partial source edits. S8.3 population correlations, L4, guardrails and S8.4 figures remain unimplemented/unmeasured; no calibration claims or retuning. Historical README.pdf/performance_check.json remain untracked and untouched.
next: S8.3 — path-shape correlations, L4 counting baseline and guarded evaluation; S8.1–S8.2 are complete.

in progress: phase 3 S8.3 — read spec, progress and Git history/status; no partial source edits. Add L4 with fixed path bins and L3 interpolation, analysis-only per-trip correlations, explicit guardrails and accepted-v4.5.0 status comparison. Run 500 seed-42 days in chunks of 100 and a matched 100-day/100-rollout oracle in chunks of 20. Leave S8.4 figures for the next task. Historical PDF/performance files remain untouched.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_config.py
assumptions: path cues use fixed, declared thresholds (no held-out fitting); detour has missing/no/yes bins. Continuous cues use low/middle/high for observed values plus explicit missing state. L4 interpolates toward L3 with k=5. Report fixed single-cue ablations to identify the closest cue if the combined model misses 2%, without selecting/tuning on those results. Analysis correlations use hidden trip boundaries to align starting bars with smoothed observed geometry, kept separate from the observable segmentation used in targets.csv.
next: commit L4 and tests, then integrate trip metrics/guardrails and evaluate without retuning existing simulation parameters.
done: S8.3 L4 counting baseline — 54 baseline/config tests passed. Five day-disjoint folds, L3 interpolation, fixed single-cue diagnostics and a no-path smoothing control; huge k matches L3 and unseen cells back off exactly. No simulator settings changed.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_config.py
assumptions: corrected initial bin plan before evaluation: exactly three states per cue, missing/low/high at straightness 0.9 and speed 1 km/h, missing/no/yes at 0.4 km deviation. Missingness is one of the three bins, not a fourth. Fixed k=5; no held-out tuning.
known problems: population targets and guardrails remain unmeasured; no failing tests.
next: add compact trip diagnostics, guardrails and accepted-baseline comparison, then resumable evaluation.
in progress: S8.3 trip diagnostics — align all hidden committed trips, including interrupted/day-end trips, to trailing-smoothed observed and raw true GPS at identical start/end boundaries. Store scalar metrics only. Add hard guardrails alongside unchanged calibration checks and a pure comparison against archived v4.5.0 check values; bump package to 5.2.0 for checkpoint compatibility.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_trip_statistics.py tests/test_stats.py tests/test_config.py tests/test_resume.py tests/test_oracle.py
assumptions: detour means realized smoothed-observed chord deviation >=0.4 km, not planned waypoint count. Mean trip speed includes waits. All trips enter the denominator; undefined geometries are explicitly counted. Old targets remain WARN outside ranges; new hard guardrails FAIL on violation.
next: commit diagnostics after targeted tests, then run seed-42 evaluation without parameter retuning.
done: S8.3 diagnostics — 71 targeted tests passed; four trip/guardrail/comparison tests also pass after adding the explicit comparison CLI. Compact trip geometry includes interrupted trips, causal smoothed observations and identical true-path boundaries. New hard guardrails preserve old calibration semantics. Archived authentic v4.5.0 checks with commit/seed/day provenance. Package 5.2.0 rejects older checkpoint contracts; trajectories unchanged.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_trip_statistics.py tests/test_stats.py tests/test_config.py tests/test_resume.py tests/test_oracle.py
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_trip_statistics.py
assumptions: baseline comparison is explicit (`python -m lionsim.trip_statistics RUN --reference docs/phase2_v450_checks.json`), requires complete matching seed/day count and writes separate JSON/Markdown artifacts. Missing formerly passing checks fail the comparison. Oracle minimum 0.20 applies to both headline and all-report scopes, separately from the unchanged 0.25–0.50 calibration range.
known problems: population metrics have not yet been evaluated; no test failures.
next: run the fixed 500-day statistics and 100-day oracle experiments in resumable chunks, document every warning/status change and all parameter additions; then full pytest.
in progress: S8.3 fixed evaluation — 500 stats days in five 100-day chunks and 100 oracle days ×100 rollouts in five 20-day chunks, seed 42. No images (S8.4 deferred), no minute files, no tuning. Each day checkpoints independently; interrupted invocations resume from their output directories.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 500 --seed 42 --chunk-size 100 --workers 4 --no-images --out outputs/phase3_s83_stats
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42 --chunk-size 20 --workers 6 --no-images --out outputs/phase3_s83_oracle
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume RUN_DIR --chunk-size CHUNK --workers WORKERS
next: finish all chunks, compare accepted checks, record full tables and missing targets without changing parameters, then full pytest.
evaluation checkpoints: stats directory outputs/phase3_s83_stats/run_20261103_141337; oracle directory outputs/phase3_s83_oracle/run_20261103_141338. First 100 stats days completed; oracle first chunk is running. Resume these exact directories after interruption rather than creating new experiments.
done: S8.3 500-day statistics — all five chunks completed: 37 PASS, 13 WARN, 1 FAIL over 4,028 trips. Walking 6.0955 h/day fails <=6.0. Boredom/straightness -0.294315, selected-goal urgency/straightness 0.068929 and detour fraction 0.069017 miss targets; urgency/speed 0.329792 and observed/true straightness 0.905918 pass. L4 worsens headline loss by 2.0815%; closest single cue is detour, still 2.0112% worse. Fixed no-path control also worsens loss; no tuning performed.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.trip_statistics outputs/phase3_s83_stats/run_20261103_141337 --reference docs/phase2_v450_checks.json
assumptions: completed evaluation does not mean accepted calibration. Reference comparison passes literal no-PASS→FAIL guardrail, but lists report-7 END_OF_DAY share 0.61→0.554 as the sole PASS→WARN change; all eight old warnings persist. New hard walking failure remains explicit.
known problems: S8.3 acceptance is not met. Matched oracle still running; S8.4 remains deferred.
next: finish oracle chunks, audit artifacts and unchanged defaults, run full pytest, commit measured results and stop.
done: S8.3 statistics delivery checkpoint — README and docs/PHASE3_S83_RESULTS.md contain all 51 checks, losses by scope/report, paired trip counts, fixed cue trials, sole baseline status change and all 15 new settings. Four comparison/geometry tests pass. Audit verified every prior S8.2 default unchanged and simulator/style/features/events/reports/plotting modules identical; 500 checkpoints contain 3,500 observable targets and 4,028 scalar trip summaries, with no minute files or PNGs.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_trip_statistics.py
known problems: measured S8.3 acceptance failures are documented; oracle final measurements and full suite remain pending.
next: complete oracle at outputs/phase3_s83_oracle/run_20261103_141338, append its results, run full pytest and finish this task.
in progress: S8.3 final verification — oracle has completed 80/100 days and final chunk is running. Run full pytest while completing its matched evaluation; final documentation will retain all measured failures. No further implementation or parameter changes planned.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: audit 100 oracle checkpoints and 70,000 continuations, append matched losses/guardrails and status changes, record full suite result, commit and stop before S8.4.
done: phase 3 S8.3 implementation/evaluation — full pytest: 231 passed in 60.86s. Completed 500 stats days and 100 matched oracle days ×100 rollouts (70,000 continuations). Oracle headline/all ratios 0.249858/0.226929 pass the new >=0.20 guardrails; both old >=0.25 calibration warnings remain. No old oracle status changes. All matched targets/features/statistics agree across runs; all 600 day invariant checks pass. README and docs/PHASE3_S83_RESULTS.md contain complete measurements, definitions, settings, tests and limitations.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.trip_statistics outputs/phase3_s83_stats/run_20261103_141337 --reference docs/phase2_v450_checks.json
assumptions: evaluation complete is not calibration accepted. Exactly 15 settings were added; every earlier default, simulator/style/features/events/reports/plotting module remains unchanged from S8.2. No tuning or ML libraries. No PNGs requested in this task. Historical README.pdf/performance_check.json remain untracked and untouched.
known problems: S8.3 acceptance NOT met: walking 6.0955 h/day exceeds 6; boredom/straightness -0.294315 misses <=-0.35; selected-goal urgency/straightness 0.068929 misses >=0.30; detours 6.9017% miss 10–30%; L4 worsens headline loss 2.0815%. Reference report-7 END_OF_DAY share changed PASS→WARN. All failures are retained honestly; no uncommitted partial implementation remains after final commit.
next: S8.4 — text-free movement examples and usual days 1–3 PNGs; S8.3 acceptance failures remain open and must not be described as calibrated.
in progress: phase 3 S8.4 — read specs, progress and Git history/status; no inherited partial source edits. Produce two text-free panels from real seed-42 trips already included in S8.3: left day 318/trip 6 (urgency 0.2, boredom 0.985, one planned detour), right day 254/trip 11 (urgency 0.962, boredom 0.160, no detour). Reuse the unchanged normal renderer and map scale; plot trailing-smoothed observed GPS on exact trip bounds. Store times/metrics/provenance separately, without coordinates. Then render the usual PNGs for days 1–3 with the existing runner.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_style_examples.py tests/test_plot_annotations.py
assumptions: these explicitly selected contrasting examples illustrate possible styles, not representative averages or a controlled causal experiment. S8.3 acceptance failures remain open. Selection is explicit CLI input rather than a new simulator setting; rendering and smoothing reuse existing defaults. Historical README.pdf/performance_check.json remain untouched.
next: implement and test the reproducible example renderer, commit the runnable increment, generate/inspect all 28 PNGs, then full pytest and final commit.
done: S8.4 reproducible example renderer — six targeted tests passed. New standalone CLI recreates two explicitly selected trips with the source manifest config/seed, rejects version or trip-statistics mismatches, and reuses the untouched daily renderer to join identical-scale map panels. JSON sidecar records scalar metrics and ISO times, with no coordinates. Tests inspect text-free artists, contrast, boundary coverage, deterministic pixels and source mismatch rejection. Corrected an initial test assumption: Road reaches the top map edge, so only empty corners must be black.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_style_examples.py tests/test_plot_annotations.py
assumptions: no new simulator/render settings or version bump needed; this standalone artifact tool changes neither simulation nor checkpoint contracts. The original S8.3 artifacts remain unchanged.
known problems: no test failures; S8.3 calibration/guardrail failures remain unchanged.
next: generate docs/style_examples.png plus scalar provenance, render the 27 usual day-1–3 PNGs, inspect output and run full pytest.
in progress: S8.4 artifact generation — generate the two-panel figure at configured 1000px per map, plus its scalar provenance; generate days 1–3 through the existing runner with --image-days 3. Stats-only avoids saving minute trajectories. Inspect the comparison and all three contact sheets, audit all PNG sizes/checkpoints against source targets, then document and run the full suite.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.style_examples outputs/phase3_s83_stats/run_20261103_141337 --wandering 318 6 --direct 254 11 --out docs/style_examples.png
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 3 --seed 42 --image-days 3 --workers 3 --out outputs/phase3_s84_images
next: inspect generated artifacts, document their interpretation and provenance, then full pytest and final commit.
done: S8.4 artifact generation — docs/style_examples.png (2000×1000) and scalar provenance JSON created; normal images saved in outputs/phase3_s84_images/run_20261103_212040 (24 report PNGs plus three contact sheets). Visually inspected the comparison and all contact sheets: black maps, coloured zones, white paths, no labels/axes/text. Audit decoded all 28 PNGs, verified contact-sheet tiles exactly match their reports and checkpoint file sizes are correct. Days 1–3 targets and statistics exactly match S8.3; no minute files saved.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.style_examples outputs/phase3_s83_stats/run_20261103_141337 --wandering 318 6 --direct 254 11 --out docs/style_examples.png
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 3 --seed 42 --image-days 3 --workers 3 --out outputs/phase3_s84_images
assumptions: daily report PNGs retain raw observed cumulative paths; the comparison uses five-minute-smoothed observed trip paths. ISO timestamps live in filenames/sidecar, never image text. Three-day statistics are incidental rendering output, not replacement calibration evidence.
known problems: none in S8.4 artifacts; all previously documented S8.3 acceptance failures remain.
next: document example interpretation/reproduction and full-suite results, commit and stop before further calibration or tasks.
in progress: S8.4 final documentation and verification — link the comparison, provenance and day contact sheets, document selected examples and unchanged calibration state, then run the full suite.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: commit verified S8.4 delivery and print the next task line.
done: phase 3 S8.4 — full pytest: 233 passed in 53.90s. Delivered docs/style_examples.png and scalar provenance JSON, with left wandering/right direct paths on identical black maps. Delivered 27 ordinary text-free PNGs for days 1–3 in outputs/phase3_s84_images/run_20261103_212040. All 28 images decoded and visually inspected through the comparison and three contact sheets; contact-sheet pixels and checkpoint sizes verified. README and docs/STYLE_EXAMPLES.md document panel identities, ISO times, metrics, selection limitations, output locations and exact reproduction commands.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
assumptions: selected illustrations are not representative averages or evidence of calibration acceptance. Package remains 5.2.0/schema v5; all defaults and simulator/style/features/events/reports/plotting modules are unchanged from S8.3. No ML libraries, new simulator settings, trajectory JSON or minute outputs were added. Daily targets/statistics match S8.3 exactly.
known problems: no S8.4 failures or partial implementation edits. S8.3 walking guardrail and four statistical targets remain unresolved; report-7 END_OF_DAY regression and prior warnings persist. Historical README.pdf/performance_check.json remain untracked and untouched.
next: S8.5 — audit phase-three test coverage; S8.3 acceptance failures remain open and must not be described as calibrated.
in progress: phase 3 S8.5 coverage audit — user requested continued work while S8.4's final commit completed. Git is clean apart from the two historical untracked files. Read phase-three requirements and inspect existing movement, feature, baseline, trip-statistics, figure, oracle and resume tests. All six explicit S8.5 requirements already have substantive coverage; reuse it rather than duplicating simulation batches. Document exact requirement-to-test mapping and the distinction between controlled mechanism tests and failed population acceptance.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_features_path.py tests/test_baselines.py
assumptions: S8.5 is a coverage/verification task, not authorization to hide failures or retune S8.3 percentages. No production or default changes are needed based on this audit. Add tests only if a concrete uncovered requirement emerges.
next: commit the targeted coverage audit, run full pytest, update phase-three completion/acceptance status, commit and stop.
done: S8.5 requirement audit — 44 targeted tests passed in 20.53s. All six explicit requirements are covered: fixed-seed directional path ratios, in-map detours, causal smoothed observed features, L4/large-k convergence, schema bump and reproducibility. docs/PHASE3_TEST_COVERAGE.md maps requirements and supporting contracts to nine test files and 28 verified test names. No uncovered requirement justified duplicate tests or implementation changes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_features_path.py tests/test_baselines.py
assumptions: controlled mechanism tests are not substitutes for population calibration or predictive improvement; passing them does not erase S8.3 failures. Existing equality checks use appropriate numerical tolerances and day-disjoint evaluation.
known problems: no targeted test failures; S8.3 acceptance failures remain unchanged.
next: run the full suite for final S8.5 verification, update completion status and commit; no automatic retuning.
in progress: S8.5 final verification — run all tests after the documented coverage audit. Confirm no production/default or generated-example changes since S8.4; update current status and stop after the final tested commit.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: record full-suite result, mark S8.1–S8.5 implementation/evaluation/figures/coverage delivered with acceptance still unmet, then stop.
done: phase 3 S8.5 — full pytest: 233 passed in 53.86s. Coverage audit verifies all six requested S8.5 contracts and supporting boundaries/provenance/resume checks, with nine test files and 28 named references. README and docs/PHASE3_TEST_COVERAGE.md record implementation/evaluation/figure/coverage completion without claiming calibration acceptance. No production code, defaults, test behavior or artifacts changed in this audit.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
assumptions: reuse existing meaningful tests rather than adding duplicates. S8.1–S8.5 delivery is complete; full-day population performance is assessed by S8.3 measurements, not controlled unit tests or selected figures. Package 5.2.0/schema v5 and all prior evaluation artifacts remain valid.
known problems: S8.3 remains unaccepted: walking 6.0955 h/day (>6), boredom–straightness -0.294315 (<=-0.35 required), selected-goal urgency–straightness 0.068929 (>=0.30 required), visible detours 6.9017% (10–30% required), and L4 headline loss 2.0815% worse (>=2% improvement required). Report-7 END_OF_DAY share changed PASS→WARN. No remaining numbered implementation/test tasks or partial edits; historical untracked files untouched.
next: address the documented S8.3 calibration and L4 failures in a separate bounded calibration step; phase-three implementation, figures and coverage are delivered, but acceptance is not met.
in progress: phase 3 calibration diagnosis — user explicitly requested addressing S8.3 failures. Read specification, progress and Git status/history; no partial source edits. Keep all acceptance thresholds, event rules, schedules, latents, GPS noise and existing phase-two behavior settings fixed. Investigate movement-only calibration on a separate seed (137, 100 days), with at most three declared candidates before one 500-day seed-42 confirmation. Retain every candidate result. L4 changes must use observed inputs and training-only fitting; no held-out threshold searches or hidden-state inputs.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_config.py
assumptions: the user's calibration request authorizes revising phase-three movement coefficients beyond the initial S8.1 values; original formulas/coefficients remain documented as historical. Diagnosis: detour probability ignores urgency, while high-urgency Shade trips actually have negative straightness correlation; L4's extra count interpolation worsens loss even without adding path cues. Calibration tests must distinguish mechanisms from held-out population performance.
next: introduce a configurable urgency penalty for detours with a compatibility default of zero, test it, then evaluate three explicit movement-only candidates on seed 137 before selecting a candidate for confirmation.
done: calibration mechanism increment — 69 movement/config tests passed, including urgency suppression and map-bound handling. Added movement_style.detour_urgency_weight with compatibility default 0; 1 suppresses discretionary detours at maximal urgency. Package bumped to 5.3.0/schema remains v5 to prevent old checkpoint resumes with a changed config contract. Declared baseline plus three movement candidates in docs/calibration_phase3 before evaluating seed 137; no acceptance threshold changes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_config.py
assumptions: original 5.2.0 measurements and figures remain historical, reproducible with that version; current default trajectories are unchanged until candidate selection. Selection uses movement guardrails/targets, never held-out L4 loss.
known problems: S8.3 failures remain until measured otherwise.
next: evaluate baseline/A/B/C on 100 seed-137 days, record all results and select one movement candidate for confirmation.
in progress: calibration selection runs — baseline and frozen A/B/C each run 100 days at seed 137, no images/minute files. Outputs go to outputs/phase3_calibration_137/{baseline,A,B,C}. Preserve their manifests/configs and reports. While they run, inspect observed-cue coverage and the L4 count prior without changing the seed-42 evaluation or target thresholds.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 100 --seed 137 --workers 3 --no-images --out outputs/phase3_calibration_137/baseline
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 100 --seed 137 --workers 3 --no-images --config docs/calibration_phase3/A.json --out outputs/phase3_calibration_137/A
next: compare baseline/A/B/C, choose using the declared movement-only criteria, then freeze the chosen settings for seed-42 confirmation.
done: seed-137 baseline/A/B/C selection — all 100-day runs completed and saved in docs/calibration_phase3/selection_results.json. A/B/C fix walking (5.608/5.655/5.577 h) but regress urgency/speed (-0.083/-0.062/-0.190). B passes boredom and detour targets; C passes urgency/straightness and detours. None is acceptable as a default. Baseline remains unchanged.
assumptions: preserve the declared failed candidates; do not hide the speed regression. Inspection shows speed multiplication saturates the unchanged 4 km/h cap, erasing urgency variation. Extend the original three-candidate plan transparently by one mechanistic repair (D): B's geometry, speed intercept restored to original 0.85 and urgency slope 0.4 retained. No additional geometry/threshold search; this addresses a newly observed regression rather than selecting solely on seed-42 thresholds.
known problems: candidate acceptance is incomplete, and L4 remains unresolved.
in progress: evaluate D on the same diagnostic seed, then require confirmation on separate days/seed before adopting; implement training-only L4 bins separately with explicit missingness and regularization.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 100 --seed 137 --workers 4 --no-images --config docs/calibration_phase3/D_speed_repair.json --out outputs/phase3_calibration_137/D
next: decide whether D merits seed-42 confirmation; retain all candidate outcomes and fixed thresholds.
in progress: L4 binning repair — original fixed straightness cut (0.9) places most finite values into the same bin. Add optional per-report tertiles fitted only from training-day observed features, giving three numeric bins plus an explicit missing category; detour remains missing/no/yes at unchanged 0.4 km. Compare one declared regularized variant (k=20) on seed-137 targets, without changing L0–L3 or tuning against seed-42 confirmation. Record cutpoints in each fold for audit. Retain fixed-bin mode for historical comparisons.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_config.py
assumptions: this corrects the initial interpretation of three bins (missing/low/high offered only two numeric levels). Missing values must remain separate, not imputed from labels. Quantiles use no target labels; per-report fitting separates path variation from the known daily clock. k=20 is declared before this diagnostic to reduce sparse-cell overconfidence; no k/threshold grid search.
next: test training-only cutpoints/holdout isolation and large-k equivalence, record the diagnostic, then freeze chosen settings for confirmation.
done: L4 training-bin increment — 55 baseline/config tests passed after explicitly covering blank CSV feature values. Training-only per-report tertiles and k=20 reduce diagnostic L4 regressions: baseline seed-137 -0.09%, B -0.03%, D +0.05% relative improvement; none reaches 2%. Recorded all fold cutpoints/losses in docs/calibration_phase3/l4_training_bins_diagnostic.json. No held-out cuts or hidden inputs. Package 5.3.1 protects the extended config/report contract; fixed-bin mode remains the default pending selection.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_baselines.py tests/test_config.py
known problems: D's lower speeds restore a positive urgency/speed relationship (0.2386) but walking remains 6.0732h, urgency/straightness 0.1592 and detours 9.49%; no candidate accepted. Dataset diagnostic reveals very short high-urgency Shade return trips (3–6 minutes) have low straightness, so stronger mid-trip steering alone is insufficient.
next: commit the runnable L4 diagnostic and failed candidate records, then address departure-heading carryover in one explicitly documented mechanism revision, without changing trip definitions or acceptance thresholds.
in progress: departure-heading mechanism revision — initial heading is inherited from previous activity even on a very short urgent return trip. Add an optional trip-start rotation toward its first waypoint/goal, weighted by frozen urgency; no position jump, future data or event change. Compatibility default is zero. Declare one E revision of D: full urgency-weighted departure alignment, 0.6–1.0 km planned offsets (to remain visible after unchanged five-minute smoothing), and the declared training-tertile/k=20 L4. This is a transparent second extension of the original three-candidate plan, motivated by short-trip geometry diagnosis; no acceptance thresholds/metrics are changed.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_config.py
assumptions: a lion can face its chosen direction at departure; urgency controls how quickly it does so. Alignment is a one-time heading update, preserves position and all movement bounds, and remains in snapshot state. E is the final geometry candidate for this bounded attempt; if it still misses targets, report those without another threshold-driven search.
next: evaluate E on seed 137 and an independent seed 271, then decide whether it improves enough for one 500-day seed-42 confirmation.
done: departure-heading revision — 70 targeted movement/config tests passed. New optional one-time heading alignment is urgency weighted, never teleports, never realigns an active trip and preserves other movement modes. Compatibility defaults remain zero; package 5.3.2 protects the added config key. E configuration is frozen in docs/calibration_phase3/E_departure_repair.json before evaluation.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_config.py
known problems: no implementation test failures; no calibration candidate is yet accepted.
next: E seed-137 and seed-271 validation, then one seed-42 confirmation if justified; retain failures and stop geometry tuning.
in progress: final movement candidate validation — run E for 100 days each at seeds 137 (diagnostic) and 271 (independent validation), using frozen E settings and training-only L4 bins. No images or minute files; outputs/phase3_calibration_137/E and outputs/phase3_calibration_271/E. Geometry tuning stops after this candidate; do not choose based on seed-42 results.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 100 --seed 137 --workers 4 --no-images --config docs/calibration_phase3/E_departure_repair.json --out outputs/phase3_calibration_137/E
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 100 --seed 271 --workers 4 --no-images --config docs/calibration_phase3/E_departure_repair.json --out outputs/phase3_calibration_271/E
next: record both validation outcomes; confirm the final candidate at 500 seed-42 days without further tuning, preserving any failures.
done: E validation — seed 137: walking 5.9065h, entries 7.13, boredom/straightness -0.3704, urgency/straightness 0.1385, urgency/speed 0.3177, detours 10.04%, fidelity 0.9322; seed 271: walking 5.7552h, entries 7.30, boredom/straightness -0.3034, urgency/straightness 0.1651, urgency/speed 0.3616, detours 11.59%, fidelity 0.9367. Both pass all hard movement/event guardrails and retain urgency/speed, unlike A/B/C. Urgency/straightness still misses; boredom is not robust across seeds. L4 remains ~1% worse on these small validation sets.
assumptions: select E as the bounded improvement candidate, not as fully calibrated. It fixes walking and visible detour frequency on both validation seeds without the earlier speed regression. Stop geometry tuning as declared and report remaining limitations. Seed 42 is confirmation only; no revisions after observing it.
in progress: freeze E as package 5.4.0 defaults for one seed-42 confirmation and oracle run. Update tests that explicitly assumed original coefficients or forced detours to preserve their original purpose, not weaken acceptance assertions. Keep historical figure tests on an explicit original-style config so their selected trips remain meaningful.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_style_examples.py tests/test_baselines.py tests/test_config.py
next: commit selected defaults, run 500 seed-42 days in 100-day chunks and matched 100-day oracle in 20-day chunks, then compare all old status changes and document residual failures honestly.
done: selected-default freeze — 82 targeted movement/figure/baseline/config tests passed in 32.05s. Defaults exactly match frozen E; package 5.4.0/schema v5. Original probability-law test now explicitly selects original scale/no urgency suppression; geometry/lifecycle tests explicitly force detours, and historical example tests use original movement settings. No directional, causal, boundedness or acceptance assertions were relaxed. Corrected a local targeted-edit mistake before testing: L4 settings were initially matched in comments; actual defaults are now verified against E config exactly.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_movement_style.py tests/test_style_examples.py tests/test_baselines.py tests/test_config.py
assumptions: selected defaults are an improvement candidate, not claimed accepted. Prior 5.2.0 results/figures are historical. S8.3 target values and all phase-two settings remain fixed.
known problems: validation still misses urgency/straightness and L4; boredom varies across seeds. No further geometry tuning planned.
next: seed-42 confirmation and oracle in resumable chunks, compare all guardrails/status changes, then full pytest and final measured documentation.
in progress: final 5.4.0 seed-42 confirmation — 500 statistics days in chunks of 100 and 100 oracle days ×100 rollouts in chunks of 20. No images/minute files. Settings are frozen; no tuning against these results. Outputs roots: outputs/phase3_calibrated_stats and outputs/phase3_calibrated_oracle.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 500 --seed 42 --chunk-size 100 --workers 4 --no-images --out outputs/phase3_calibrated_stats
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42 --chunk-size 20 --workers 6 --no-images --out outputs/phase3_calibrated_oracle
next: resume both exact run directories until complete, retain all outcomes, compare with 5.2.0 and accepted 4.5.0, then full tests.
confirmation checkpoints: stats outputs/phase3_calibrated_stats/run_20261103_221518; oracle outputs/phase3_calibrated_oracle/run_20261103_221518. Resume these exact directories if interrupted; do not create replacement seed-42 experiments.
in progress: confirmation resumed after status request — saved runs contained 100/500 stats days and 20/100 oracle days; both first chunks completed cleanly. Resume four remaining chunks in each exact directory with frozen 5.4.0 configuration. Existing uncommitted edits are final documentation/progress updates; no partial implementation changes to revert.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase3_calibrated_stats/run_20261103_221518 --chunk-size 100 --workers 4
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase3_calibrated_oracle/run_20261103_221518 --chunk-size 20 --workers 6
next: finish both confirmations, document measurements and regression status, run full pytest and commit.
in progress: final regression verification — run the full suite against frozen 5.4.0 while confirmation chunks proceed. No further simulation, feature-definition or acceptance-threshold changes are planned; fix only concrete implementation regressions if tests reveal them.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: combine full-test evidence with complete 500-day/oracle measurements and explicitly retain unresolved calibration targets.
done: 5.4.0 500-day confirmation — 39 PASS, 12 WARN, 0 FAIL. Walking now passes at 5.928967 h/day (was 6.0955) and visible detours pass at 10.1836% (was 6.9017%). All hard movement/event guardrails pass: entries 7.326/day, pooled speed 3.50853 km/h, abandoned trips 0.626/day, all 500 day invariants valid. Urgency/speed 0.318465 and observed/true straightness 0.933494 remain PASS. Boredom/straightness -0.319508, urgency/straightness 0.182882 and L4 -1.94391% relative improvement remain WARN; acceptance is still unmet. Detour-only cue is closest, still 0.73127% worse than L3.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.trip_statistics outputs/phase3_calibrated_stats/run_20261103_221518 --reference docs/phase2_v450_checks.json
assumptions: no changes after confirmation. Compared with accepted 4.5.0, the sole status change remains report-7 END_OF_DAY share PASS→WARN (0.61→0.57); no previous PASS becomes FAIL. Old eight warnings remain. Oracle evaluation still in progress; do not infer its final guardrail result from partial chunks.
next: finish oracle, document all comparisons and residual failures, record full tests, commit the bounded calibration outcome.
done: final regression suite — 236 passed in 61.50s. Current documentation now records 5.4.0 formulas, original/updated distributions, all candidate outcomes, explicit plan extensions, unchanged target thresholds, complete 500-day check/loss tables and every status change. Historical 5.2.0 figures remain identified as such. The only changes versus 5.2.0 statuses are walking FAIL→PASS and detour frequency WARN→PASS; three phase-three targets remain WARN.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
known problems: oracle confirmation still running; do not claim full acceptance or all failures fixed. No new implementation changes or test failures.
next: complete/audit 100 oracle days and 70,000 continuations, append matched comparisons and final status, then commit and stop this bounded calibration attempt.
done: bounded 5.4.0 calibration delivery — both confirmation runs complete. Full suite: 236 passed in 61.50s. 500-day result is 39 PASS, 12 WARN, 0 FAIL; walking 5.928967 h/day and detour fraction 10.1836% now pass. Oracle headline/all ratios 0.249285/0.233359 pass >=0.20; the older >=0.25 warnings remain, with no oracle status changes versus 5.2.0 or accepted 4.5.0. Audited all 600 checkpoints, 3,500 target rows and 70,000 continuations; matching days have identical target/features/statistics, every day passes event invariants. All target thresholds and phase-two settings unchanged; no ML libraries.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.trip_statistics outputs/phase3_calibrated_stats/run_20261103_221518 --reference docs/phase2_v450_checks.json
assumptions: confirmation is frozen, not a tuning loop. docs/PHASE3_CALIBRATION_RESULTS.md records every candidate, the two explicit plan extensions, original/current comparisons, all check tables, oracle results and limitations. The 100-day oracle subset's incidental walking mean remains 6.062167 h/day (FAIL); the specified 500-day mean passes. Historical 5.2.0 images/data remain documented and unchanged.
known problems: NOT fully accepted: boredom/straightness -0.319508 versus <=-0.35; urgency/straightness 0.182882 versus >=0.30; L4 1.94391% worse than L3 versus >=2% improvement. Detour-only cue is closest, still 0.73127% worse. Original calibration warnings and report-7 END_OF_DAY PASS→WARN persist. No unfinished runs, tests or partial implementation edits remain after final commit; historical README.pdf/performance_check.json untouched.
next: investigate the three remaining S8.3 targets using new independent validation data and a mechanism review; this bounded calibration fixed walking and detour frequency but did not achieve full acceptance.
in progress: phase 4 A1 — read prior spec/progress/Git history/status and save UPDATE_SPEC_4.md. No inherited partial source edits; historical README.pdf/performance_check.json remain untouched. Add causal observed-heading features and new analysis settings only. Freeze simulator package 5.4.0/schema v5, every existing parameter and all existing statistics. Use a separate heading export-version marker for new checkpoints rather than changing simulator version.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_heading.py tests/test_config.py
assumptions: displacement uses causal as-of positions at t and t−W; insufficient history produces null displacement/speed, moving=false and an explicit incomplete-window flag. speed_recent is km/min (exactly |d|/W). Distance and tie-breaking use zone centres, matching the specified bearings; bin <=1.5 km is inclusive. New L5 analysis runs from saved GPS/hidden files in a separate CLI, so true-goal code is never imported by model-facing exports. Fresh stats-only evaluation will use --keep-files to supply those required saved inputs; no images.
next: commit tested heading features, append columns with backward-compatible resume, then implement isolated L5/control analysis, tests and the fixed fresh-seed run.
done: phase 4 A1 causal features/settings — 51 targeted tests passed; stationary, straight walk, prefix truncation and invalid settings covered. Existing defaults and simulator source unchanged.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_heading.py tests/test_config.py
next: append heading CSV columns and validate resume checkpoints.
assumptions: heading distance bins are fixed at 1.5 km; no fitted cuts are needed. Zero-length displacement cannot define a bearing. known problems: none in this increment.
in progress: phase 4 A1 export integration — append heading columns after every existing target column; use heading-v1 marker and reject incompatible exports on resume while retaining legacy 5.4.0 runs without heading settings.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_heading.py tests/test_features_path.py tests/test_resume.py
done: phase 4 A1 exports — 22 targeted tests passed, including checkpoint repair, worker equivalence and legacy 5.4.0 resume with identical existing statistics. Fixed strict config validation to permit missing analysis-only sections in old saved manifests; new configurations retain required nested settings.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_heading.py tests/test_features_path.py tests/test_resume.py
next: implement day-disjoint L5 counting evaluation, shuffled and isolated LEAKY true-goal controls, decision/report and sensitivity.
assumptions: old runs keep their old CSV schema; heading-v1 new runs append ten columns. known problems: none in this increment.
in progress: phase 4 A2–A4 — implement isolated counting analysis with exact existing L3 probabilities/day folds, report-index/goal/moving cells, split-local shuffle, LEAKY current-goal control, subsets, confusion counts, declared-default decision and post hoc window sensitivity.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_l5_counts.py tests/test_l5_analysis.py
assumptions: L5 uses the cell explicitly specified by A2, without appending L3 state/history keys. Laplace smoothing is inherited through L3; no extra pseudo-count is added to the specified L5 formula. Fixed geometric cuts require no fitting; existing L3 cuts are declared config constants. The true-goal control is an empirical leaky benchmark, not guaranteed to improve loss. Undefined/nonpositive L3-to-truegoal gaps are reported explicitly, never clipped. MARGINAL means >=2% and <5% versus L3; >=5% without the required shuffle advantage is NOT HELPFUL.
done: phase 4 A2–A4 analysis — 10 targeted tests passed. L3 matches existing headline/all/per-report losses; huge-k L5 approaches L3; day folds have no overlap; split-local shuffling preserves report marginals; hidden goal changes cannot affect nonleaky losses; model-facing import graph excludes truegoal; saved-input end-to-end analysis is deterministic/resumable and leaves targets/statistics/manifest untouched. First test used exact float equality for empty-cell algebra; changed to 1e-14 tolerance (5.6e-17 rounding), as requested by spec.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_l5_counts.py tests/test_l5_analysis.py
next: strengthen boundary/frozen-simulator tests, document reproducible commands and assumptions, run full suite before fresh-seed experiment.
assumptions: hidden goal is read at the exact report minute after its transitions and before that minute's movement; analysis caches are explicitly LEAKY and remain outside exports. Five folds required. known problems: no production experiment has run or been inspected yet; no tuning.
in progress: phase 4 A6 pre-experiment audit — add heading angular/distance/tie boundary tests and frozen-simulation equivalence, document analysis-only usage/units/assumptions, and run relevant tests then full regression suite. Freeze all choices before inspecting fresh-seed results.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_heading.py tests/test_l5_counts.py tests/test_l5_analysis.py tests/test_config.py
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
done: phase 4 A6 pre-experiment verification — 64 targeted tests passed; full suite 255 passed in 64.45s. Audited git diff: simulator, events, reports, path features, movement style, existing stats and package/schema versions unchanged. All existing default_config.json values exactly match a7ff47e. New settings do not change fixed-seed GPS, hidden state, events or daily statistics. Documentation records commands, units, nulls, tie rules, leaky isolation and decision boundaries.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_features_heading.py tests/test_l5_counts.py tests/test_l5_analysis.py tests/test_config.py
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: run 500 new days at seed 2026, five 100-day chunks with --resume, workers=4, stats-only --keep-files --no-images; then evaluate once at declared defaults.
assumptions: scanned every outputs/**/run_manifest.json before running: neither 2026 nor 2027 has been used. Freeze W20, displacement0.15 km, angle30 degrees, distance1.5 km, k20 and shuffle seed2026; sensitivity10/20/30 only. known problems: none in phase-four implementation; historical phase-three calibration warnings remain outside this frozen analysis scope.
in progress: phase 4 A5 declared fresh-seed experiment — implementation frozen at 586c347; start seed2026, 500 days, chunks100, workers4, stats-only with saved minute tables and no images. Do not inspect/tune partial L5 results. This is the first production L5 run; no defect rerun used.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --stats-only --stats-days 500 --seed 2026 --keep-files --no-images --workers 4 --chunk-size 100 --out outputs/phase4_l5
done: phase 4 A5 simulation chunk 1 — 100/500 days checkpointed at outputs/phase4_l5/run_20261104_093129; status partial, original simulation warning printed without changes. No L5 result evaluated.
next: resume the same saved manifest for days101–200. assumptions: unchanged frozen settings; known problems: none in execution.
in progress: phase 4 A5 simulation chunk 2.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase4_l5/run_20261104_093129 --workers 4 --chunk-size 100
done: phase 4 A5 simulation chunk 2 — 200/500 days; same run/seed/config, no L5 evaluation yet.
next: resume days201–300. assumptions: unchanged; known problems: no execution failures.
in progress: phase 4 A5 simulation chunk 3.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase4_l5/run_20261104_093129 --workers 4 --chunk-size 100
done: phase 4 A5 simulation chunk 3 — 300/500 days; checkpoint resume continues without regeneration/failures.
next: resume days301–400. assumptions: unchanged; known problems: no execution failures.
in progress: phase 4 A5 simulation chunk 4.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase4_l5/run_20261104_093129 --workers 4 --chunk-size 100
done: phase 4 A5 simulation chunk 4 — 400/500 days; same saved configuration and seed.
next: resume final days401–500, then run isolated L5 analysis. assumptions: unchanged; known problems: no execution failures.
in progress: phase 4 A5 simulation chunk 5.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.run --resume outputs/phase4_l5/run_20261104_093129 --workers 4 --chunk-size 100
done: phase 4 A5 simulation — all 500/500 days complete in five100-day chunks using --resume, four workers, no images; seed2026. Final ordinary walking warning is inherited and not altered (6.009 h/day). This independent seed may expose existing calibration failures; simulator changes are prohibited.
in progress: phase 4 A5 first and only declared-default evaluation from saved minute GPS and hidden files; compute L5, controls, subsets, confusion and post hoc sensitivity.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.l5_analysis outputs/phase4_l5/run_20261104_093129
next: inspect and audit complete report, document results without tuning, run final tests and commit.
done: phase 4 A5 first production analysis — l5_report.json/md written successfully; no defect or rerun. Seed2026 headline CV losses: L3=0.5845062255702655, L5=0.729722032045735, shuffled=0.8518484296308273, LEAKY truegoal=0.8109963194627966. L5 is 24.8442% worse than L3 and 14.3366% better than shuffled: NOT HELPFUL under the declared rule. No positive L3-to-truegoal gap exists, so gap closed is undefined. Moving goal accuracy: 588/1501=39.1739% all reports; 514/1253=41.0215% headline. No tuning after results.
verify: /opt/anaconda3/bin/python3.12 -m lionsim.l5_analysis outputs/phase4_l5/run_20261104_093129
assumptions: these are results for the literal specified coarse L5 cell and counting model; they do not establish that heading has no information in other models. Truegoal is an empirical leaky control, not a guaranteed loss upper bound. Post hoc W10/20/30 headline L5=0.734882/0.729722/0.722480; W20 remains main.
known problems: frozen simulator's fresh-seed existing checks are 37 PASS, 13 WARN, 1 FAIL (walking guardrail, 6.0087 h/day). No simulation/statistic changes permitted. PyArrow printed sandbox CPU-cache inspection warnings while reading tables; reading and analysis completed normally.
next: archive human-readable results, audit outputs/provenance and run final regression suite, then commit and stop phase4.
in progress: phase 4 final delivery/audit — archive complete report with interpretation and inherited simulator-check failures; verify every saved input hash and checkpoint, then final full pytest.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
done: phase 4 A1–A6 complete — final full suite 255 passed in 63.29s; git diff --check clean. All 500 simulation checkpoints, 500 analysis caches, 1,500 input hashes, 3,500 target rows, five identical day-disjoint folds and zero PNGs audited. Reports saved under outputs/phase4_l5/run_20261104_093129; full human-readable archive at docs/PHASE4_L5_RESULTS.md. No production defects, no rerun, no post-result tuning. Simulator remains 5.4.0/schema lionsim-v5; every existing parameter/statistic implementation remains unchanged. Historical README.pdf/performance_check.json untouched.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
verify: /opt/anaconda3/bin/python3.12 -m lionsim.l5_analysis outputs/phase4_l5/run_20261104_093129
assumptions: declared W20/k20 result retained despite post hoc W30's lower loss. Negative result applies to this specified counting baseline; heading beats shuffle but does not improve L3. No positive truegoal gap exists.
known problems: L5 verdict NOT HELPFUL; frozen simulation retains 13 warnings and one walking-hours failure on the independent seed (6.0087667 > 6 h/day). These are reported outcomes, not unfinished phase-four implementation work.
next: Phase 4 complete; no further tasks scheduled.
in progress: phase 6 W1 — read UPDATE_SPEC_6.md, original header, progress and last10 commits/status. No inherited partial edits; user-provided spec is new, historical README.pdf/performance_check.json untouched. Implement observable weather and causal ambient measurements, heat/traffic/water/nap effects, version6.0.0/schema-v6 and appended public context exports.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_weather.py tests/test_config.py tests/test_event_exports.py tests/test_simulator.py
assumptions: weather/day type use independent categorical draws from the day's RNG. Ambient Celsius maps heat-scaled ambient using configured ambient min/max to [12,42], clips the physical range, smooths trailing5 minutes and adds independent sd0.5 measurement noise drawn at initialization. Hidden tables retain unsmoothed true Celsius. Rain delays shade departure60min and advances wake60min beyond existing heat effects; water preference modifies both logits and scheduled visit probabilities. No dataset export tooling/column list exists; targets.csv is the model-facing export. No dataset plan or tag will be created.
next: tested W1 checkpoint, then hidden day types/jitter, diversity/L3w, full regression, frozen one-run measurement and oracle.
done: phase 6 W1 — 83 targeted tests passed, including weather frequencies, causal temperature, traffic/nap effects, exports and reproduction. Bumped6.0.0/schema-v6; old run resume is rejected by existing version/schema checks. Updated exact-column tests for intentional new public fields; no token/report-time/PNG changes.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_weather.py tests/test_config.py tests/test_event_exports.py tests/test_simulator.py tests/test_features_heading.py
next: implement hidden day types and once-per-day schedule jitter; preserve hunt cutoff and full event validation.
assumptions: ambient sensor noise is drawn before movement and never changes after a report; weather is public, true ambient stays hidden. known problems: no implementation failure; production seed3003 has not run.
in progress: phase 6 W2/R1 — hidden independent day types; prey-rich prey/scouting/hunt links and attempt cap; rival extra daytime patrol intentions/water avoidance/mood drift; once-daily jitter and flattened period priors.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_day_types.py tests/test_weather.py tests/test_config.py tests/test_behaviour_scenarios.py tests/test_oracle.py tests/test_cross_time.py
assumptions: preserve the original legal hunt interval [18:30,22:00); raw hunt jitter is uniform +/-20, affects readiness and period priors, with actual hunting clamped to the unchanged legal start/cutoff. Midday jitter shifts start/end together; tourist jitter shifts start only and oracle branches retain that start. Rival patrols plan1–3 additional distinct destinations but safety/shade/hunt interruptions remain authoritative; actual entry uplift is measured, never forced. Prey-rich lowers threshold0.10, multiplies prey byU(1.3,1.8), advances readiness30min, multiplies initial chase wait0.5 and scout dwell1.5, caps attempts4. Rival water logit−2.5, visit multiplier0.2, mood drift−0.02/hour, patrol dwell5–10min. Defaults declared before measurement. Softmax is stored under randomness in shipped JSON and migrated through the existing canonical learnability alias for backward-compatible --set semantics.
done: phase 6 W2/R1 — 83 targeted tests passed. Forced-type fixed-seed samples confirm earlier prey-rich chases and more rival zone entries; all120 scenario days pass event validation and prey-rich never exceeds4 attempts. Tested independent type frequencies, bounded jitter, exact resume, hidden/public separation and oracle snapshot reproduction. Fixed traffic validator/diagnostic window to use the saved jittered start; legal hunting rules unchanged.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_day_types.py tests/test_weather.py tests/test_config.py tests/test_behaviour_scenarios.py tests/test_oracle.py tests/test_cross_time.py
next: D1 fixed-sample diversity against saved v5.4.0, weather/type breakdowns, L3w and revised declared-target report.
assumptions: weather and day_type remain fixed across oracle branches; future traffic resamples using the actual daily tourist start. known problems: none in targeted tests; no seed3003 measurement or tuning performed.
in progress: phase 6 D1/M1 analysis — fixed-size sequence diversity from new checkpoints and saved v5.4.0 day.json logs, weather/type breakdowns and L3w on identical folds. Add declared revised guardrail comparison without changing prior correlation thresholds.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_phase6_statistics.py tests/test_stats.py tests/test_baselines.py tests/test_resume.py
assumptions: sample without replacement20 times using fixed seed606 at N200 and N500; insufficient days gives null, never substitutes a smaller N. Normalised entropy is Shannon entropy/log(number of distinct sequences), zero for a single sequence. L3w cell appends 3-bin weather to the full L3 history cell, interpolating counts with k20 times L3; all training counts use the existing day folds. Kopje dwell retains the existing entry-to-next-entry duration definition; first-chase averages condition on chase days. Temperature breakdown averages all8 public report measurements per day. Reference sequences come only from saved v5.4.0 files, never re-simulation.
done: phase 6 D1/M1 analysis — 31 targeted tests passed. Fixed-N metrics are deterministic, incomplete samples remain null, reference is read from saved files, L3w uses matched folds and cannot consume day_type, comparison report contract tested. Updated only overlapping behavioural guardrail limits explicitly revised by spec; prior correlation thresholds unchanged. Preflight review fixed tourist-end-at-day-boundary clipping and prevented rival daytime intentions from taking over night arrivals; no measurement had run.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_phase6_statistics.py tests/test_stats.py tests/test_baselines.py tests/test_resume.py tests/test_day_types.py
next: full regression and documentation; freeze settings before seed3003 measurement/oracle.
assumptions: historical oracle~0.249 is seed42, not a matched seed2026 oracle; report labels this difference. known problems: no production failures/retries; seed3003 absent from every output manifest at preflight.
