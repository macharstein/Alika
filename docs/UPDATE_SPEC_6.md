UPDATE SPEC 6 for `lionsim`: WEATHER, DAY TYPES AND MORE RANDOMNESS (read with docs/UPDATE_SPEC.md; same header rules, PROGRESS.md, git checkpoints, --resume safety).

CONTEXT: v5.4.0 is the "before" version (seed 2026, 500 days: events/day 18.28, zone entries/day 7.33, walking 6.009 h, unique zone-sequence fraction 0.302, headline log loss L0 1.7101, L1 1.0991, L2 0.6315, L3 0.5845; oracle/L0 about 0.249). Goal: more route diversity and more randomness while staying learnable. Do NOT change the 17-token vocabulary, report schedule, hunt cutoff, event rules, or the PNG look. Bump the package to 6.0.0 and the schema to lionsim-v6; note in README that older seeds give different data. Do not tag or write any dataset plan in this task.

=== W1. WEATHER (observable, logged) ===
- Per day, draw weather in {clear, hot, overcast, rain} with configurable probabilities (default 0.40, 0.25, 0.20, 0.15), from the day's RNG.
- Weather sets the existing heat latent with noise: hot 1.15-1.30, clear 0.90-1.10, overcast 0.70-0.90, rain 0.60-0.80 (config). Keep the existing heat links (shade entry time, shade exit, drinking).
- Rain: tourist volume x0.3; waterhole goal bonus lowered (water is available elsewhere); midday nap starts later and is shorter.
- Hot: waterhole bonus raised; shade entry earlier (via heat).
- Logging: day.json gets top-level "weather" (category) and each report gets "ambient_temp_c" (smoothed ambient temperature from the existing ambient curve times heat, mapped to Celsius, default range 12 to 42, plus small Gaussian noise sd 0.5). Weather and ambient_temp_c are OBSERVABLE context: add them to targets.csv and, if the dataset export tooling exists, to export_columns.json and the "context" feature group. Hidden-state files keep the true values.

=== W2. HIDDEN DAY TYPES ===
Draw day_type in {normal 0.60, prey_rich 0.20, rival 0.20}, independent of weather. Log it ONLY under ground_truth_latents and in hidden files (never in targets, never exported).
- prey_rich: prey_density x U(1.3, 1.8); first chase earlier; Kopje scouting dwell longer; hunt threshold lowered by 0.10; up to 4 chase attempts.
- rival: waterhole goal bonus strongly reduced; 1 to 3 extra daytime patrol zone entries among Kopje, Plain, Den; mood drift slightly lower.
- normal: unchanged.
All coefficients under "day_types" in default_config.json.

=== R1. MORE RANDOMNESS ===
- goal softmax temperature 0.70 -> 0.85
- period prior scale x0.8 (applied to all period priors)
- per-day jitter of period boundaries (midday sleep window, hunt window start, tourist window start): uniform +/-20 minutes, drawn once per day
Put these under "randomness" in default_config.json; keep every other randomness setting unchanged.

=== D1. DIVERSITY METRICS (stats.py) ===
Add to the stats report (both zone-entry sequences and full event-token sequences):
- unique fraction at a FIXED sample size N=200 (mean over 20 random subsets of days, fixed seed) and at N=500
- number of distinct sequences in 500 days; top-5 sequence share; normalised entropy of the sequence distribution
- the same values for v5.4.0 computed from the saved seed-2026 run outputs/phase4_l5/run_20261104_093129 (no new simulation), shown side by side
Also add weather and day-type breakdowns: frequencies, per-weather means (shade entry time, waterhole-day fraction, tourist volume, ambient_temp_c), per-day-type means (first chase time, Kopje dwell, zone entries/day, waterhole-day fraction).

=== M1. MEASUREMENT RUN (one run, no tuning after seeing results) ===
Seed 3003 (unused so far), 500 days, --stats-only, chunks of 100 with --resume, --workers 4, no images. Then the baseline ladder (L0 to L3, 5-fold CV by day, as before) plus L3w = L3 with weather added as a cue (3 bins: hot, clear/overcast, rain). Then the oracle on 100 days x 100 rollouts (--resume, chunks of 20). Report everything next to the v5.4.0 numbers above.

=== TARGETS (print PASS/WARN/FAIL; revised guardrails are listed because the v5.4.0 limits were heuristics) ===
Diversity:
- zone-sequence unique fraction at N=200 >= 1.25 x the v5.4.0 value measured the same way
- distinct zone sequences in 500 days >= 1.3 x v5.4.0
- top-5 zone-sequence share at N=500 <= 0.25
- event-token sequence unique fraction at N=200 >= 0.85
Learnability balance:
- oracle/L0 (headline, 100 days) between 0.28 and 0.45
- L2 at least 15% better than L1; L3 at least 3% better than L2 (headline)
- report L3w vs L3 (no target)
Behaviour guardrails:
- event invariants 0; hunt cutoff respected; zone entries/day 7.5 to 11; events/day >= 19
- walking <= 6.5 h/day; mean walking speed 2.0 to 4.0 km/h; resting 15.5 to 20 h
- hunt-attempt days 0.50 to 0.70; catch days 0.20 to 0.40; road-entry days 0.10 to 0.18; waterhole days 0.65 to 0.88; abandoned trips <= 1.0/day
Observable traces:
- weather frequencies within 5 percentage points of config
- mean tourist volume on rain days <= 0.4 x clear days
- mean shade entry time on hot days at least 45 min earlier than overcast and rain days
- waterhole-day fraction: rain <= 0.65, hot >= 0.85
- prey_rich first chase time at least 20 min earlier than normal; Kopje dwell >= 1.3 x normal
- rival zone entries/day at least 1.0 more than normal; rival waterhole-day fraction <= 0.60
Prior links: list any v5.4.0 correlation that moves from PASS to WARN or FAIL; no new hard FAIL allowed.
If a target fails, say so plainly with the numbers and the knob you would turn; do not tune and rerun silently (one declared retry is allowed only for a code defect, described in the report).

=== TESTS ===
Fixed seeds, loose tolerances: weather categories appear with roughly configured frequencies; weather and ambient_temp_c are present in day.json and targets.csv; day_type is absent from targets.csv and from any export column list; rain lowers expected traffic; prey_rich days have earlier first chases on average; rival days have more zone entries on average; period jitter stays within +/-20 min; hunt cutoff still respected; vocabulary still 17 tokens; same seed reproduces the same data; existing tests still pass.