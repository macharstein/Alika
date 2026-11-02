# Completed tasks 1–6

Scope: `docs/UPDATE_SPEC.md` tasks 1–5, including its cross-cutting resume and atomic-write requirements. Task 6 is now completed as requested; task 7 oracle remains unimplemented.

- [x] 17-token event schema, internal traffic context, restored daily reports/latents
- [x] Seven usable next-zone targets and run-level targets.csv
- [x] Committed journeys, hunger/heat/traffic traces, bounded night naps
- [x] Statistical metrics, target checks and JSON/Markdown reports
- [x] Atomic output and per-day checkpoint/resume with 200-day execution chunks
- [x] Tests and final 200-day statistics check

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
