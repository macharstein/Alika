UPDATE TASK for the existing `lionsim` project (single-lion GPS collar simulator, data generation only). Modify the existing code. Do NOT rewrite from scratch, do NOT remove working features, and do NOT add any ML libraries (no torch, tensorflow, sklearn). Counting models with numpy/pandas are fine. Do not ask me questions: make reasonable choices and record every assumption in README.md. Keep results reproducible (per-day seeds from SeedSequence). Run pytest at the end and fix failures.

Goal of this update: make the generated sequences learnable but not trivial, remove car events from the event log, and add statistics that prove the balance between signal and noise.

=== 1. REMOVE CAR_PASSED FROM THE EVENT LOG ===
- CAR_PASSED must no longer appear in `events`. The vocabulary becomes 17 tokens: ENTER_DEN, ENTER_SHADE, ENTER_KOPJE, ENTER_WATER, ENTER_HUNT, ENTER_FEED, ENTER_PLAIN, ENTER_ROAD, WOKE_UP, FELL_ASLEEP, GROOM, DRINK, CHASE_START, CATCH, FAIL, EAT_START, EAT_END.
- Keep the car/tourist process inside the simulation: it still drives road avoidance and mood.
- Store traffic only as context: per report, "traffic_count_since_last_report" and "traffic_count_last_hour"; per day, tourist volume under "ground_truth_latents".
- Every event keeps: id, t (ISO with seconds), token, description, and add "zone" (current zone name or null).
- Update validation, tests, README, and the manifest (vocabulary list, schema version bump).

=== 2. RESTORE day.json FIELDS ===
day.json must contain: day_index, date, events, reports (8 per day, each with report_index, report_time, new_events, path_up_to_index, current_zone, traffic counts, and the cumulative path if embed_cumulative_path_in_reports is true), and "ground_truth_latents" (start_hunger, hunt_threshold, heat, prey_density, tourist_rate_per_hour, wake_time), clearly marked analysis-only. Hidden per-minute bars stay in the hidden_state files only.

=== 3. NEXT-ZONE TARGET LABELS ===
For each report (report 8, at 05:00 next day, is excluded because it ends the day) compute "next_zone_target": the first ENTER_* token after the report time within the same day. If there is none, the label is "END_OF_DAY" (a target label only, never an event token). Save per-day targets in day.json under each report ("next_zone_target", "time_to_next_zone_min" or null) and as a run-level `targets.csv` (day, report_index, report_time_bucket, current_zone, last_event, next_zone_target).

=== 4. BEHAVIOUR CHANGES (learnable structure, not noise) ===
Apply these to the simulator, with every new number placed in default_config.json under a "behaviour" key:
a) Goal commitment: once a goal zone is chosen, the lion keeps it until arrival, unless an interrupt happens (fatigue below a threshold, temperature above a threshold, or a time-period boundary such as the start of the midday sleep window). Log each abandoned trip in hidden_state with the reason. Remove the free turn-backs seen in the current output (lion stops 1 to 1.5 km short of the waterhole).
b) Hunting eligibility: Hunting-ground goals are allowed only between 18:30 and the stalking cutoff (default 22:00). No ENTER_HUNT or stalking after the cutoff. Add a validation rule for this.
c) Hunger leaves a visible trace: if start_hunger > hunt_threshold the lion goes to the hunting ground near 18:30 to 20:00 and makes one or more chase attempts (CHASE_START then CATCH or FAIL, multiple attempts allowed after a failure); otherwise it spends the evening on Plain/Kopje/Waterhole and makes no hunt. Both kinds of day are intended (the lion does not hunt every day).
d) After CATCH: ENTER_FEED, EAT_START, EAT_END, FELL_ASLEEP in the Feeding spot (as before). After repeated FAIL until cutoff: patrol and catnaps.
e) Heat leaves a trace: hotter days (higher "heat" latent) give earlier ENTER_SHADE and a later WOKE_UP (the lion stays longer), and longer drinking at the waterhole.
f) Tourist volume leaves a trace: higher volume lowers the probability of the lion approaching or entering the road; low volume and high boredom make ENTER_ROAD reachable. Aim for ENTER_ROAD on roughly 10 to 25% of days (check in the statistics, do not hard-force it).
g) Night catnaps: enforce a minimum nap length (default 25 min), a maximum number of catnap cycles per night (default 3), and merge naps shorter than the minimum, to remove the FELL_ASLEEP/WOKE_UP chatter seen in the current output.
h) Walking speed: verify that mean patrol speed matches the config (default 2 to 4 km/h) and add the mean to the statistics. Adjust the movement code if it is far lower.
Keep GPS noise and random walk wiggle as they are.

=== 5. STATISTICS REPORT (new module stats.py) ===
CLI: python -m lionsim.run --stats-only --stats-days 200 --seed 42 (no images, no per-minute files unless --keep-files). Writes `stats_report.json` and `stats_report.md` to the run folder. Report:
- Events per day (mean, min, max), zone entries per day, token frequencies (all 17), share of each zone among entries
- Fraction of days with: any chase, a catch, a feast, an ENTER_ROAD, an ENTER_HUNT; chase success rate
- Hours per behaviour (sleeping/resting, walking, hunting, grooming, eating, drinking) versus targets
- Distribution of wake time, shade entry time, shade exit time, waterhole arrival time, first chase time
- Unique daily zone-sequence fraction, share of days covered by the top 5 sequences, distribution of zone-sequence length
- Path statistics per day: total length, mean speed while walking, tortuosity (path length divided by straight-line distance between consecutive zone entries), map coverage (fraction of 0.5 km grid cells visited), number of abandoned trips
- Class balance of "next_zone_target" for each of the 7 usable report indices, and overall
- Correlations between latents and observable traces (hunger vs hunting day, heat vs shade entry time, tourist volume vs road entries), as numbers
- Targets check: a "targets" block in default_config.json with ranges, and the report must print PASS, WARN or FAIL for each:
  zone entries per day 6 to 12; each zone's share of entries at least 0.03 and at most 0.35 (ENTER_ROAD may be lower but warn if 0); hunt-attempt days 0.5 to 0.7; catch days 0.2 to 0.4; unique daily sequences above 0.3; top-5 sequences cover under 0.5 of days; mean walking speed 2 to 4 km/h; hours per behaviour within the earlier ranges (resting 16 to 20 h).

=== 6. BASELINE LADDER (inside stats.py, counting models only) ===
Using targets.csv, split days 70/30 by day. Compute multiclass log loss on the next_zone_target (including END_OF_DAY as a class), with Laplace smoothing alpha configurable (default 1), for:
  L0 frequency only
  L1 time-of-report bucket (the 7 report indices)
  L2 time bucket + current zone + last event token
  L3 L2 + day-level cues from observable history (shade entry hour bucket, number of drinks so far, number of chase attempts so far, catch so far yes/no); if this makes cells too sparse, back off to L2 with a documented rule
Report all four losses, the entropy of the target distribution, and the relative gaps (L0-L1, L1-L2, L2-L3). Print a short text interpretation: if L0, L1, L2 are nearly equal (within 3%) say "mostly noise"; if L2 is below 20% of L0 say "nearly deterministic"; otherwise "learnable".

=== 7. ORACLE LOSS (new module oracle.py) ===
CLI: python -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42
For each of the first N days and each usable report, snapshot the FULL simulator state (position, bars, behaviour, goal, RNG state, latents, event log so far) at the report time, then run the rest of the day `oracle-rollouts` times, each with a different RNG seed spawned from the snapshot. Estimate P(next_zone_target | hidden state) from rollout frequencies (with the same Laplace smoothing). Report: oracle log loss on the actual next-zone targets of the original run, compared with L0 to L3. Interpretation lines: "oracle near zero: too deterministic", "oracle close to L0: too noisy", otherwise "balanced". This needs the simulator to support state snapshot and resume (deep copy of the state object); refactor minimally to allow it, and add a test that a resumed rollout with the original RNG state reproduces the original rest of the day.

=== 8. CONFIG AND CLI ===
Add every new parameter to default_config.json with comments, group the learnability knobs under "learnability" (softmax temperature, goal commitment, interrupt thresholds, nap limits, hunt cutoff, latent ranges, chase probabilities), keep --set working for all of them, and store them in run_manifest.json. Add flags: --stats-only, --stats-days, --oracle, --oracle-days, --oracle-rollouts, --keep-files.

=== 9. TESTS ===
Add pytest tests for: CAR_PASSED absent from events; vocabulary has 17 tokens; zone field present; next_zone_target logic including END_OF_DAY; no ENTER_HUNT or CHASE after the cutoff; goal commitment (no abandoned trips without a logged reason); catnap limits; stats report keys exist; baseline losses are finite and ordered L0 >= L1 >= L2 on a 200-day run (allow small tolerance); oracle resume reproduces the original day; seed reproducibility still holds.

=== 10. DELIVERY ===
At the end run: --stats-only --stats-days 200 --seed 42, show stats_report.md, and report which targets PASS, WARN or FAIL. Do not tune parameters to force every check to pass without telling me: list which knobs you changed and why. Update README.md.

=== 11. RESUME SAFETY (applies to everything above) ===
- Every long-running command (stats, oracle, large day batches) must support --resume: days already completed are detected on disk and skipped. Write results incrementally (one file or one JSONL line per day, plus a progress counter in run_manifest.json) so a killed process loses at most one day of work.
- All file writes must be atomic: write to a temporary file in the same folder, then rename, so a cutoff never leaves a corrupt JSON, parquet or PNG.
- Run long jobs in chunks (default 200 days per command) and never as a single 2000-day command inside a Codex session. The README must show the chunked command pattern.
- Every phase must be re-runnable: if some of it is already done, detect that (code present, tests passing, PROGRESS.md) and continue instead of duplicating.