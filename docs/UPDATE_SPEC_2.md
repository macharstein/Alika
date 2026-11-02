UPDATE SPEC 2 for the `lionsim` project (read together with docs/UPDATE_SPEC.md; the same header rules, PROGRESS.md, git checkpoints and --resume safety apply).

CONTEXT: a 200-day stats run (seed 42) gave 19 PASS, 3 WARN, 0 FAIL, with these starting values (the "before" numbers):
zone entries/day 6.28; events/day 19.5; walking 6.27 h/day (WARN, target 1-5); resting 15.75 h (WARN, target 16-20); abandoned trips 2.2/day, of which traffic_avoidance 211 of about 442 total; waterhole reached on 105/200 days; ENTER_ROAD on 6.5% of days (WARN); class balance at report 6: 71% END_OF_DAY, at report 7: 97% END_OF_DAY; baseline log loss L0 1.810, L1 0.980, L2 0.821, L3 0.843 (L3 worse than L2, about half of test rows backed off); GPS observed path 49.2 km vs true 22.5 km; oracle not yet run.

DO NOT CHANGE: the 17-token vocabulary, the 8-report schedule, the 22:00 hunt cutoff, the day format (05:00 to 05:00), the independence of days, per-day seeding. Do not add tokens. Because the data distribution changes, bump the schema_version in run_manifest.json and note in README that old seeds give different data.

All targets below go into the "targets" block of default_config.json, and stats_report.md must print PASS / WARN / FAIL for each. Do not tune knobs just to turn a check green without telling me: at the end list every knob you changed and why. Tests must use fixed seeds and loose tolerances (check bounds and directions, not exact values).

=== S1. MEASUREMENT UPGRADES (do first) ===
a) Per-report results: in the baseline ladder, report log loss for L0 to L3 separately for each report index 1 to 7, plus a "headline" value computed over reports 1 to 5 only and an "all reports" value. Config flag headline_reports (default [1,2,3,4,5]).
b) Cross-validation: replace the single 70/30 split by 5-fold cross-validation by day; report mean and standard deviation of each loss across folds.
c) Fix L3 sparsity: replace hard backoff by Dirichlet-style interpolation, p_L3 = (n_cell_class + k * p_L2) / (n_cell + k), with k configurable (default 5), and use coarser cue bins (3 bins each: shade-entry hour, number of drinks so far, chase attempts so far, catch so far). Report the fraction of test rows whose L3 cell had zero training count.
d) GPS noise: lower the default gps noise sd from 15 m to 8 m. Add statistics: ratio observed/true path length, and mean apparent speed during resting minutes from raw 1-minute displacement versus from 5-minute smoothed displacement.
Targets: observed/true path length ratio <= 1.6; smoothed resting apparent speed < 0.8 km/h; L3 (interpolated) <= L2 within every fold's noise (report it, no pass/fail yet).

=== S2. TRAFFIC AVOIDANCE: DELAY, DON'T ABORT ===
Traffic must change timing or route, not cancel trips. When a car-heavy period raises the road penalty, the lion waits, slows, or picks an intermediate waypoint that keeps it farther from the road. Trips may still be abandoned only for fatigue, temperature, or a schedule boundary. Log "delayed_by_traffic" counts separately from abandonments.
Targets (200-day run):
- abandoned_trip_count mean per day <= 1.0
- traffic_avoidance share of abandoned trips <= 0.25 (should be near 0 if delays replace it; keep the reason code for the rare remaining cases)
- fraction of days on which the lion reaches the waterhole: 0.80 to 0.88
- walking hours per day: 3.0 to 5.0
- resting hours per day: 16.0 to 20.0
- mean walking speed stays within 2.0 to 4.0 km/h

=== S3. ROAD VISITS WITH A CAUSE ===
Make ENTER_ROAD reachable with a causal structure: the probability that the lion chooses the road as a goal rises with boredom and with low same-day tourist volume, is highest in the evening after the tourist window (about 19:00 to 23:00) and lower during the window while cars are passing. Roads are easier to walk on, so also allow the road as a transit option on night patrols.
Targets (200-day run):
- fraction of days with ENTER_ROAD: 0.10 to 0.18
- ENTER_ROAD share of all zone entries: 0.02 to 0.05
- Pearson correlation between actual tourist volume per day and number of road entries per day: <= -0.35
- at least 60% of ENTER_ROAD events occur between 19:00 and 23:59
- at most 10% of ENTER_ROAD events occur during the tourist window

=== S4. NIGHT PATROL ON NON-CATCH NIGHTS ===
After the hunt cutoff, on nights without a catch the lion patrols the territory (document: walking the territory, playing, short catnaps): 1 to 3 additional zone entries chosen among Plain, Kopje, Den, Waterhole (and Road per S3), with catnaps between (keep the nap limits from the earlier update, but allow up to 4 cycles). After a catch, the lion stays asleep at the Feeding spot until morning (unchanged). No night chases.
Targets (200-day run):
- zone entries per day: mean 8.0 to 11.0
- events per day (17 tokens): mean 24 to 32
- non-feast days with at least one zone entry after 23:00: >= 0.70
- feast days with any zone entry after EAT_END: <= 0.15
- END_OF_DAY share at report 6: 0.40 to 0.60; at report 7: 0.60 to 0.80
- walking hours still <= 5.0 and mean walking speed within 2 to 4 km/h (night patrol must not blow the walking budget; if it does, shorten daytime wandering, and report it)
- unique_sequence_fraction >= 0.5 and top_five_sequence_share <= 0.35

=== S5. CROSS-TIME LINKS (early behaviour carries information about later behaviour) ===
a) prey_density to morning scouting: scouting dwell time at the Kopje increases with prey_density (the lion scans for herds from high ground). The dwell must be observable as the time gap between ENTER_KOPJE and the next zone entry. Higher prey_density also moves the first chase earlier.
b) hunger to wake time: hungrier days wake earlier by up to about 30 minutes (keep the 05:00 to 07:00 clip).
c) heat to afternoon: keep existing heat links (shade entry earlier, shade exit later, longer drinks).
Targets (200-day run):
- corr(prey_density, kopje_dwell_minutes) >= 0.40 (on days with a Kopje entry)
- corr(prey_density, first_chase_time) <= -0.30 (on hunting days)
- corr(start_hunger, wake_time) <= -0.30
- corr(heat, shade_entry_time) <= -0.40
- baseline ladder: cross-validated L3 (interpolated) at least 3% better than L2 on the headline reports (1 to 5). If not reached, report that clearly and list what you tried.

=== S6. ORACLE AND FINAL RUN ===
Run the oracle from the first update spec on 100 days with 100 rollouts per report (--resume, in chunks of 20 days). Report oracle log loss on the headline reports and overall, next to L0 to L3.
Targets: oracle/L0 between 0.25 and 0.50; oracle at least 10% below L2 (there must be headroom for history-aware models). If the oracle is above L2, say the simulator is too noisy; if oracle/L0 is below 0.25, say it is too deterministic, and propose which knob to turn.
Then run a 500-day stats-only run in chunks of 100 with --resume. Generate images only for the first 3 days. Print the final stats_report.md summary table with all PASS/WARN/FAIL lines, the per-report loss table, and the list of knobs changed.

=== S7. TESTS ===
Add tests (fixed seed, small day counts, loose bounds) for: delayed_by_traffic logged and traffic_avoidance abandonments near zero; ENTER_ROAD occurs and mostly after 19:00; non-feast nights have zone entries after 23:00 and feast nights do not; hunt cutoff still respected; END_OF_DAY logic unchanged; interpolated L3 equals L2 when k is very large; CV folds are by day with no overlap; vocabulary still 17 tokens; reproducibility with the same seed.