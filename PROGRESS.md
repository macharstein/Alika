# Phase 1 complete; phase 2 S1–S5 implemented

Scope: phase-one `docs/UPDATE_SPEC.md` tasks 1–10 are complete. Under `docs/UPDATE_SPEC_2.md`, S1–S5 are implemented and verified, including checkpoint/resume safety; seven statistical calibration warnings remain. S6 and S7 as separate phases have not been started.

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
