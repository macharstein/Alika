# Frozen v6.0.0 smoke result

**PASS**: generate → export → independent verify for20 days, seed9999.
The frozen tag is `sim-v6.0.0-frozen` at `25d9d272ee6e3af86017b3cb5f8fc232310f4a7a`.
Tooling commit: `ad7a60e`. Both detached checkouts were clean throughout generation.
No simulator behaviour, thresholds or default settings changed.

| Split | Days | Rows |
|---|---:|---:|
| Train |14|98|
| Validation |3|21|
| Test |3|21|
| Total |20|140|

There are32 whitelisted columns. `weather` and `ambient_temp_c` are context
features; `day_type`, `heat`, true positions/goals and hidden state are not exported.
Verification confirmed exact source-row equality, complete report coverage,
disjoint day splits, file checksums and successful event validation on all20 days.
The exact split plan was written before simulation and precedes every day checkpoint.
No images or cumulative paths in report JSON were generated.

Results: [verification report](../outputs/frozen_v6_smoke_9999/verification_report.json),
[export manifest](../outputs/frozen_v6_smoke_9999/export/export_manifest.json),
[resolved plan](../outputs/frozen_v6_smoke_9999/resolved_plan.json),
[provenance/checksums](frozen_v6_smoke_result.json).

No main(seed7001) or robustness(seed8002) generation was run. Main N remains
unspecified and must be supplied before resolving its split plan. Seed9999 outputs
are explicitly smoke-only and cannot be used as release training/evaluation data.
This verifies the pipeline, not scientific acceptance; see [known limitations](KNOWN_LIMITATIONS.md).

The simulator tag was created only after all270 pre-tooling tests passed.

Final full suite after adding release tooling: **283 passed in77.06s**.
The frozen tag remains unchanged; only documentation and release tooling were added afterward.
