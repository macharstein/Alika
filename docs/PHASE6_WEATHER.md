# Phase 6: weather, hidden day types and randomness

Version **6.0.0**, schema **lionsim-v6**. Older seeds produce different trajectories;
resume refuses older schema/package versions. The 17-token vocabulary, eight report
times, legal hunting interval [18:30,22:00), chase/feeding/sleep event rules and PNG
appearance are unchanged. No dataset plan or tag is part of this task.

## Declared mechanisms

Weather is drawn daily from the day's RNG: clear40%, hot25%, overcast20%, rain15%.
It replaces the old uniform heat draw with category-specific uniform heat:
clear0.90–1.10, hot1.15–1.30, overcast0.70–0.90, rain0.60–0.80. Existing heat links
remain. Rain multiplies tourist rate by0.3, adds−2 to water goal logits and
multiplies scheduled water visits by0.25. It delays shade departure60minutes and
advances wake60minutes, shortening the nap. Hot adds1.2 to water logits and
multiplies scheduled water visits by1.3 (probability capped at1). Water logit
modifiers also apply to night patrol choices.

`day.json.weather`, each report's `weather`/`ambient_temp_c`, and the two appended
CSV context columns are observable. True ambient uses the existing ambient curve
times daily heat, linearly mapped from the existing ambient min/max to12–42°C
and clipped to that physical range. The public measurement uses a trailing5-minute
mean plus independent Gaussian sd0.5°C noise. Noise is drawn once at initialization,
so future movement cannot change earlier measurements. Hidden minute tables retain
the category, heat and unsmoothed true ambient. No dataset export tooling or
export-column registry exists in this repository; no new one was invented.

Day type is a separate independent categorical draw: normal60%, prey_rich20%,
rival20%. It appears only in `ground_truth_latents`, hidden minute tables and
analysis statistics; never in targets or public report context. Prey-rich multiplies
prey density byU(1.3,1.8), lowers hunt threshold0.10, advances readiness30minutes,
multiplies the first chase wait by0.5, scouting dwell by1.5 and limits attempts to4.
Normal keeps existing mechanics. Rival adds−2.5 to water logits, multiplies water
visit probability by0.2, adds mood drift−0.02/hour and plans1–3 extra daytime patrol
arrivals among Kopje/Plain/Den, excluding the current zone. Patrol stops are5–10min.
Safety, shade, hunting and terminal feeding/sleep rules remain authoritative;
interruptions may prevent planned arrivals. Actual extra entries are measured.

Softmax temperature is0.85 and every used period prior is scaled by0.8. Raw jitter
for midday, hunt and tourist boundaries is drawn uniformly from integer−20…20
minutes once per day and saved in hidden state/latents. Midday shifts both sleep
boundaries. Hunt jitter shifts readiness and period priors; actual hunting stays
inside the unchanged legal interval, so negative jitter cannot open hunting before
18:30. Tourist jitter shifts start only; traffic validation and oracle branches use
the saved actual start. Other noise settings are unchanged. `randomness.softmax_temperature`
is in the shipped JSON and retains its existing `learnability.softmax_temperature`
canonical alias, so both CLI spellings continue to work.

## Measurement definitions

Both zone-entry and full event-token sequence diversity use20 seeded subsets without
replacement at fixed N200 and N500 (seed606). Smaller runs show unavailable values,
not a substituted sample size. Distinct count, unique fraction, top5 coverage and
normalised Shannon entropy H/log(distinct sequences) are reported; entropy is0 for
one distinct sequence. The saved v5.4.0 seed2026 run supplies both reference sequence
families from `day.json`; it is never re-simulated.

Weather/type tables show frequencies and per-group means with sample counts.
First-chase means condition on days with a chase; Kopje dwell retains the existing
first-Kopje-entry to next-zone-entry duration (including departure travel). Ambient
means average eight public reports per day. Clock traces are minutes after05:00.

L0–L3 retain their existing five day-disjoint folds. L3w appends weather (hot,
clear/overcast, rain) to the full L3 history cell, then interpolates training-only
counts with k20 times L3. No day type enters the model. Report L3w without selecting
parameters from held-out loss. The oracle fixes daily weather/type/jitter with the
snapshot and resamples future decisions/traffic;100 days x100 continuations per
usable report means70,000 continuations.

Revised limits are those in UPDATE_SPEC_6; overlapping walking/rest/entry/water
checks use the revised values. Historical correlation thresholds stay unchanged.
The final report explicitly lists PASS-to-WARN/FAIL correlations and new hard
failures. Every missed target includes a candidate knob, which is not applied.
The historical oracle/L0≈0.249 is from seed42; the before simulation comparison
uses seed2026. These are labelled separately, rather than claiming matched seeds.

## Reproduction

```sh
python -m lionsim.run --stats-only --stats-days 500 --seed 3003 --workers 4 --no-images --chunk-size 100 --out outputs/phase6_stats
python -m lionsim.run --resume STATS_RUN --workers 4 --chunk-size 100
# Repeat resume three more times (500 days total).
python -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 3003 --workers 4 --no-images --chunk-size 20 --out outputs/phase6_oracle
python -m lionsim.run --resume ORACLE_RUN --workers 4 --chunk-size 20
# Repeat resume three more times (100 oracle days total).
python -m lionsim.phase6_report STATS_RUN --oracle-run ORACLE_RUN
```

Daily checkpoints retain compact event sequences/environment statistics, so stats-only
needs no minute files or images. Completed days are skipped on resume. Settings are
frozen before the measurement. Only a declared code-defect retry is permitted;
failed scientific targets alone do not trigger a rerun.
