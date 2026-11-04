# Frozen v6 release operations

The simulator tag `sim-v6.0.0-frozen` points to commit
`25d9d272ee6e3af86017b3cb5f8fc232310f4a7a`, tested with270 passing tests.
The tag stays fixed; release tooling and documentation are later commits.
See [known limitations](KNOWN_LIMITATIONS.md) before interpreting generated data.

No previous dataset plan/export pipeline was present in this checkout. The new
minimal pipeline is `tools/dataset.py`; it does not modify the simulator or its
configuration. Both the tooling checkout and simulator checkout must be clean,
including untracked files. The simulator HEAD must equal the pinned tag commit.
Raw config-file and canonical effective-config SHA256 values must match the plan.
These checks run before generation and again before each resumed chunk.

`dataset_plan.json` declares main seed7001 with N deliberately unset, contiguous
70/15/15 day splits, independent robustness seed8002 with300 held-out days,
chunk size200, and no cumulative paths in report JSON. Main N must be explicitly
supplied: floor(0.70N) train days, floor(0.15N) validation days, remaining test days.
All seven reports from one day share one split. The exact resolved N and day
boundaries are atomically written to `resolved_plan.json` **before simulation**;
resume refuses a different plan, schema, tooling commit, seed or config.

Main/robustness generation is disabled unless explicitly requested with
`--allow-generation`. It is not authorized or executed by this task. Seeds
42,137,271,2026,3003,9999 are forbidden for those roles. Seed9999 is allowed only
for the explicit20-day `smoke` role. Smoke outputs are marked `smoke_only=true`.

## Smoke commands

Use a clean checkout of the committed tooling, separate from a clean checkout
of the frozen simulator tag. This preserves the strict guards without moving
the tag or ignoring existing user files. Replace the two checkout paths below.

```sh
python /path/to/tooling/tools/dataset.py generate --repo /path/to/frozen-simulator --role smoke --out /path/to/smoke-output
python /path/to/tooling/tools/dataset.py export --out /path/to/smoke-output
python /path/to/tooling/tools/dataset.py verify --out /path/to/smoke-output
```

Generation invokes the existing resumable CLI with saved minute files, no images,
four workers and chunks of200. Repeating generate resumes the same resolved run.
The20-day smoke split is14 train/3 validation/3 test days:98/21/21 rows.

Only files in `export/` are model-facing deliverables. Its CSV columns come from
the strict whitelist in `export_columns.json`; weather and ambient_temp_c belong
to `context`. Day type, heat, true coordinates, true goals and true ambient are
excluded. `raw/` is internal simulator output containing analysis-only hidden
files and is never copied into the export. Verification checks source/CSV row
equality, complete day/report coverage, disjoint day splits, column policy,
checksums, provenance and event-validation success. It rejects unexpected files
inside the export directory. These checks do not assert that scientific calibration
thresholds pass on a20-day sample.
