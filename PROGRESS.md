# Update tasks 1–5

Scope: `docs/UPDATE_SPEC.md` tasks 1–5, including its cross-cutting resume and atomic-write requirements. Baseline ladder and oracle tasks 6–7 are not implemented in this phase.

- [ ] 17-token event schema, internal traffic context, restored daily reports/latents
- [ ] Seven usable next-zone targets and run-level targets.csv
- [ ] Committed journeys, hunger/heat/traffic traces, bounded night naps
- [ ] Statistical metrics, target checks and JSON/Markdown reports
- [ ] Atomic output and per-day checkpoint/resume with 200-day execution chunks
- [ ] Tests and final 200-day statistics check

Existing text-free PNGs, per-day SeedSequence reproducibility, and image generation for every selected day are preserved. Parameter choices and observed target failures will be recorded in README.md after measurement.

in progress: phase 5 — inspect and finish inherited uncommitted tasks 1–5; no prior Git commits exist. Retaining the partial schema, simulator, statistics and atomic-resume implementation, updating obsolete tests and documentation rather than reverting it.
verify: /opt/anaconda3/bin/python3.12 -m pytest -x -q tests/test_event_exports.py tests/test_validation_rules.py tests/test_stats.py
next: verify inherited behaviour changes and resume, commit runnable phase 5, then implement task 6 only (no oracle).

done: phase 5 — retained and completed inherited tasks 1–5; atomic resume tests, 17-token reports, traffic context, targets, and statistics work. Relevant suites: 50 schema/stats/resume tests and 31 behaviour/road tests passed.
assumptions: bounded first hunt wait makes initially hungry days attempt hunting; staging moved to 17:00 and water-visit probability 0.65 added after the first diagnostic showed zero road entries. No target thresholds changed.
known problems: 200-day check has 19 PASS, 3 WARN, 0 FAIL; Road days 6.5%, resting 15.754h, walking 6.272h remain outside reference ranges. These are reported, not hidden.
verify: /opt/anaconda3/bin/python3.12 -m pytest -q
next: phase 6 — implement smoothed counting baselines with day-separated holdout and observable-history cues; no oracle.
