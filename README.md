# Lion GPS collar simulator

Current development version: **6.0.0 / lionsim-v6** (UPDATE_SPEC_6). Weather, hidden day types, schedule jitter and
observable ambient temperature are added; older seeds produce different data.
Old v5 runs cannot resume into v6. Earlier measurements below are historical.
The 17-token vocabulary, report schedule, hunt cutoff and PNG appearance remain unchanged.
[Phase-six mechanisms, assumptions and commands](docs/PHASE6_WEATHER.md) document
the declared settings, fixed-size diversity comparison and weather counting baseline.

Generate independent 24-hour days for **one synthetic lion**, with minute GPS
fixes, 17 event tokens, daily event/report JSON logs, and text-free path images
every three hours. This is a configurable stochastic simulator for inspecting synthetic
data, not an empirically calibrated model of lion behaviour. There is no machine
learning, training code, or external service dependency.

Phase 4 adds the [L5 observed-heading experiment](docs/L5_ANALYSIS.md): ten appended
causal heading columns, day-fold counting evaluation, shuffled and explicitly LEAKY
true-goal controls. Simulator 5.4.0, existing parameters and statistics are frozen.
The [500-day seed-2026 result](docs/PHASE4_L5_RESULTS.md) is **NOT HELPFUL** for
the specified L5 baseline: 24.84% worse headline loss than L3, though 14.34% better
than shuffled goals. No parameters were tuned after evaluation.

Before phase 6: package **5.4.0**, manifest schema **lionsim-v5**. Phase 3 currently
implements **S8.1–S8.5**: trip-start urgency, boredom and mood set walking style
and optional detours; ten causal observed-GPS features are appended to targets.csv. The accepted
phase-two baseline is tagged **v4.5.0** at commit `3de4f5a`.

**Old seeds produce different data** with the new movement style. Reproducibility
requires the same package version and effective configuration; older manifests
cannot resume into v5. Tokens, report schedule, day-level latent sampling, hunt
cutoff, stalking/chase logic and PNG styling remain unchanged. No phase-two
parameters were retuned. Phase-two measurements below are historical, not
measurements of the new movement distribution. See [movement-style details](docs/MOVEMENT_STYLE.md).
The [5.4.0 calibration](docs/PHASE3_CALIBRATION_RESULTS.md) fixes two seed-42
500-day failures: walking falls to **5.929 h/day** and visible detours rise to
**10.18%**. All hard movement/event guardrails pass. **Three targets remain unmet**:
boredom–straightness −0.3195, urgency–straightness 0.1829, and L4 headline loss
1.94% worse than L3. Both oracle/L0 ≥0.20 guardrails pass after 70,000 continuations. The smaller
100-day oracle sample still averages 6.062 walking hours/day; the 500-day result
does not guarantee every smaller sample passes.
The original [5.2.0 evaluation](docs/PHASE3_S83_RESULTS.md) remains archived.
Version 5.4.0 changes trajectories; old 5.2.0 seeds/figures remain historical. Resume requires the exact original version and saved configuration.
See [path-feature definitions and
causality](docs/PATH_FEATURES.md). S8.4 delivers the [text-free movement comparison](docs/style_examples.png)
and [usual days 1–3 PNGs, provenance and reproduction commands](docs/STYLE_EXAMPLES.md).
The selected example paths use smoothed observed GPS; normal report PNGs retain raw
observed cumulative paths. These illustrations do not resolve S8.3 acceptance failures.
Current full suite: **255 tests passed**, including phase-four causality, control isolation,
counting-model, frozen-simulation and resume checks. The [S8.5 coverage audit](docs/PHASE3_TEST_COVERAGE.md)
maps all six requested test requirements to existing checks. Phase-three implementation,
evaluation, figures and test coverage are delivered; **S8.3 acceptance remains unmet**.

## Setup and first run

Use **Python 3.10 or newer**. Some macOS installations still make `python3` point
to Python 3.9; select a newer interpreter when creating your environment.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m lionsim.run --days 1 --seed 42 --out outputs
```

The first run defaults to **one day**, starting on simulated **2026-01-01**,
with eight 1000 × 1000 PNGs and a contact sheet. `pyarrow` is optional:
`python -m pip install pyarrow` enables Parquet; otherwise both tables use
deterministic gzip-compressed CSV. `--set output.prefer_parquet=false` explicitly
selects CSV even when PyArrow is installed.

```sh
python -m pytest -q
```

Tests cover all requested acceptance cases, invalid event/configuration cases,
report boundaries, output serialization, and worker-count independence.

## Command-line options

| Option | Default / meaning |
| --- | --- |
| `--days N` | `1`; number of independent days, dates increasing by one |
| `--seed INT` | `42`; nonnegative base seed |
| `--out PATH` | `outputs`; parent of a new run folder |
| `--config PATH` | Optional partial or complete JSON configuration |
| `--set dotted.key=value` | Repeatable overrides, applied after the config file |
| `--start-date YYYY-MM-DD` | `2026-01-01`; date of original day 1 |
| `--image-days K` | Render the first K selected days; default is **every normal day**, none in stats/oracle mode |
| `--no-images` | Disable all report images and contact sheets; overrides image-days |
| `--workers W` | `1`; independent worker processes |
| `--day-index I` | Regenerate exactly original day I, **1-based**; overrides days |
| `--stats-only` / `--stats-days N` | Statistics without daily files; default 200 days |
| `--oracle` / `--oracle-days N` | Hidden-state oracle plus baselines; default 100 days |
| `--oracle-rollouts R` | Independent continuations per usable report; default 100 |
| `--keep-files` | Keep daily JSON and minute tables in stats/oracle mode; images separately require --image-days |
| `--chunk-size N` | At most 200 new days per invocation by default |
| `--resume RUN_DIR` | Continue the saved run, skipping completed day checkpoints |

Regenerate original day 137, with the original base seed, start date, and config:

```sh
python -m lionsim.run --day-index 137 --seed 42 --start-date 2026-01-01 --out regenerated
```

Each day uses child `I - 1` from `numpy.random.SeedSequence(seed).spawn(...)`.
Days have no carry-over. The runner spawns once and gives each worker its child;
standalone regeneration selects the same child. Scheduling, worker count,
image settings, and table format do not consume simulation randomness. Data
reproduce with the same configuration and software versions; wall-clock run
metadata intentionally differ. The manifest records versions and seed details.
Daily event JSON is always indented and has identical bytes when regenerated
with the same software/configuration. Run metadata uses compact JSON for larger
runs. GPS and hidden-state values remain identical.

Daily JSON includes events, reports, and analysis-only ground-truth latents.
Cumulative coordinate arrays are **off by default**; enable them with
`--set output.embed_cumulative_path_in_reports=true`. GPS is always kept in a
separate table in normal runs.

```sh
python -m lionsim.run --stats-only --stats-days 200 --seed 42
```

Statistics mode writes no images or minute tables unless `--keep-files` is set
(which keeps tables and daily JSON, still without images). `targets.csv` contains
seven report targets per day; the final report is excluded. Each target is the
first subsequent ENTER token, or END_OF_DAY. This label is never an event.

Every invocation processes at most `--chunk-size 200` new days. To continue a
planned larger run, repeat the resume command until status is complete:

```sh
python -m lionsim.run --stats-only --stats-days 600 --chunk-size 200 --seed 42
python -m lionsim.run --resume outputs/run_YYYYMMDD_HHMMSS
python -m lionsim.run --resume outputs/run_YYYYMMDD_HHMMSS
```

Completed day checkpoints are skipped. Each worker atomically commits a compact
checkpoint after its day's outputs; the manifest progress counter is reconciled
from disk on resume. An interrupted worker loses at most its current day. JSON,
CSV, gzip, Parquet, Markdown and PNG outputs use temporary files in the destination
folder followed by atomic rename. Resume uses the saved seed/configuration and
requires the same simulator version. Partial runs report statistics only for
completed days. Oracle mode uses the same checkpoint/resume mechanism; each day
checkpoint also contains its rollout counts and probabilities. A partially
evaluated day is rerun; completed oracle days are skipped.

Workers write their own days and return only compact counters. At most twice
the worker count is submitted ahead; complete daily data are never accumulated
in memory. The parent retains seed children, counts, and small validation
records. No machine-specific runtime guarantee is assumed; the manifest records
actual elapsed time for each run.

[`performance_check.json`](performance_check.json) records the measured scale
check, including software version, command, configuration hash, timing, size,
and validation results. Hardware and storage affect timing. Statistical budget
warnings remain visible rather than being treated as successful calibration.

## Configuration

[`default_config.json`](default_config.json) is the single source of defaults.
Every adjustable model, geometry, report, image, and diagnostic parameter has an
adjacent `_comment` or `_comments` entry. Documentation keys are preserved in
the manifest but never used by simulation. `Config` is a dataclass whose default
factory loads this file; each instance owns a separate copy.

Groups are `time`, `map`, `randomness`, `bars`, `goal`, `movement`,
`tourists`, `road_response`, `targets`, `statistics`, `learnability`, `output`,
`images`, and `validation`. Learnability controls have one canonical home:

| Path below `learnability` | Controls |
| --- | --- |
| `softmax_temperature`, `latent_ranges`, `chase_base_probability` | Goal randomness, daily hidden-state ranges and base catch probability |
| `behaviour` | Goal commitment, fatigue/heat interrupts, heat/traffic effects and night nap limits |
| `activity` | Activity durations, `hunt_start`, `hunt_end` and `catnap_minutes_range` |
| `chase` | Catch probability clipping/factors and chase mechanics |
| `laplace_alpha`, `train_fraction`, `l3_min_cell_count` | Counting evaluation and backoff |
| `oracle_days`, `oracle_rollouts` | Oracle workload |
| `oracle_near_zero_nats`, `oracle_noise_relative_tolerance` | Historical thresholds; only the near-zero smoothing-resolution diagnostic remains active |

Bar noise, heading noise and GPS noise/dropouts remain under `randomness`.
Older JSON/CLI paths (`behaviour.*`, `behaviours.*`, `chase.*`, and the three
moved `randomness.*` settings) remain accepted as aliases. In files, explicit
canonical values win over legacy values; CLI overrides apply in order, last
one wins. Python callers and saved manifests use canonical paths exclusively.

```sh
python -m lionsim.run --config my_config.json \
  --set randomness.gps_noise_sd_m=25 \
  --set learnability.softmax_temperature=0.9 \
  --set 'learnability.latent_ranges.start_hunger=[0.6,1.0]' \
  --set 'goal.periods.4.priors.Hunting ground=3.0' \
  --set road_response.approach_probability=0.8
```

A partial file can contain only `{"randomness":{"bar_noise_sd":0.002}}`.
Nested objects merge; lists replace their defaults. Dotted numeric components
index list elements (`goal.periods.4`), and JSON values support numbers, booleans,
arrays, and objects. Simple strings such as `16:30` and `#FFFFFF` may be unquoted
inside the argument; quote the shell argument whenever it contains spaces,
brackets, or a `#`. Unknown keys and invalid values fail before generation.

Configuration constraints are intentional: the task's day length and sample
cadence remain 1,440 and 1 minute; the eight named token-bearing zones are fixed;
zone boundaries are inclusive and zones must not overlap **or touch**; all zones
must fit the map. Report times must be unique, ordered relative to day start,
and end at the next day start. Period priors must cover the clock exactly once.
The tourist window must fit inside the day and start at or after the latest
permitted initial wake, so `WOKE_UP` can always be the first event. Colors use
`#RRGGBB`. The contact grid must accommodate the configured number of reports.
Chase durations must fit inside one minute and within the configured allowed
outcome-delay range.

## Outputs

```text
outputs/run_YYYYMMDD_HHMMSS/
  run_manifest.json
  summary_stats.json
  validation_report.json
  stats_report.json / stats_report.md
  targets.csv
  checkpoints/day_0001.json
  oracle_report.json / oracle_report.md  # oracle mode only
  days/day_0001/
    day.json
    gps.parquet                 # or gps.csv.gz
    hidden_state.parquet        # or hidden_state.csv.gz
    images/
      2026-01-01_0800_day0001_report1.png
      ...
      2026-01-02_0500_day0001_report8.png
      2026-01-01_day0001_contact_sheet.png
```

Run folders use the machine's local wall clock; a numeric suffix prevents
collisions within one second. All dates inside data and image filenames are
**simulated** dates. Folder numbering has at least four digits, increasing in
width if needed to keep a larger run sortable. The current daily schema is
`lionsim-v3`: `day_index`, `date`, `events`, `reports`, `ground_truth_latents`.
Events contain `id`, ISO `t`, `token`, readable `description`, and `zone` (or null).
The 17-token vocabulary excludes CAR_PASSED. Traffic remains internal and appears
only as report counts since the preceding report / in the last hour, and the
actual daily `tourist_volume` in ground_truth_latents. That object also contains
the six daily latents and `_analysis_only: true`; it must not be treated as observed
predictor input. Hidden per-minute bars remain in their separate table.

Reports include new public events, path index, current true zone, traffic counts,
and (except the final report) next_zone_target and time_to_next_zone_min. Events
exactly at report time belong to that report; target search is strictly later.
Old output folders retain the schema/version with which they were generated.

`gps` has `t_iso, minute_index, x_km, y_km, x_true_km, y_true_km, missing`.
`hidden_state` has `t_iso, minute_index, hunger, energy, temperature, boredom,
mood, goal, behaviour, zone, movement_intent, road_trigger_t_iso, road_distance_km`.
The last three columns expose continuous road-response ground truth for analysis;
they never enter event JSON or image annotations. Both tables are
readable with `pandas.read_parquet(...)` or `pandas.read_csv(...)`.

Reports are internal rendering/statistics objects, referencing cumulative GPS
prefixes ending at indexes 180, 360, …, 1440 without duplicating coordinate arrays.
Contact sheets default to **2 columns × 4 rows**, in chronological row order.

## PNG contents and coverage

PNGs contain **only filled zone shapes, the accumulated white GPS path, and a
small endpoint dot** on black. There is no text, zone label, timestamp, legend,
event marker, direction arrow, title, or timeline. Dates/times remain in the
filenames, and readable event details remain in `day.json`. Each report uses
only the GPS prefix available at that report time. Events, hidden state, and
future fixes cannot affect its pixels. Map bounds, aspect ratio, colours,
resolution and contact sheets remain configurable.

Images are generated for **every simulated day by default**, including a
200-day run: 1,600 report PNGs plus 200 contact sheets. The previous automatic
five-day cap has been removed. Use `--image-days K` or `--no-images` only when
you explicitly want to limit or disable images. Saved configuration files with
old annotation or automatic-cap settings remain loadable; those obsolete
settings are ignored. New `--set` overrides must use current configuration keys.

```sh
python -m lionsim.run --days 200 --seed 42 --workers 4 --out outputs
```

To replace old annotated images and fill missing days in an existing run,
without resimulating or modifying the GPS/event/hidden-state files:

```sh
python -m lionsim.replot outputs/run_20261031_224234 --workers 4
```

This uses the recorded map, report times and stored GPS, renders every saved
day, and records the rendering update in the run manifest.

## Information in the movement history

Road curiosity is a response to a car that **already passed**, not merely a
bonus for choosing the Road zone. While walking or resting, a sufficiently
bored lion with enough energy and mood may notice a car within the configured
hearing radius. At one of the next 1–3 minute ticks it turns toward the nearest
road boundary, approaches a point about 180 metres outside it, watches for
3–12 minutes, and resumes its saved destination. It can do this without an
`ENTER_ROAD` event. Repeated cars or low mood can instead trigger a bounded
retreat; a cooldown prevents continuous retriggering. Sleep, grooming, drinking,
hunting, feeding and post-catch travel are protected from curiosity interruptions.

Walking pace also depends on energy, temperature and boredom, with bounded
noise, instead of drawing an unrelated uniform speed each minute. Consequently,
turning after a stimulus, approach/retreat direction, pauses, acceleration and
pace changes carry information even when the categorical zone does not change.
Existing slow stalking, short chase bursts, recovery rest and feeding sequences
provide additional temporal structure. The same car does not always cause the
same response: state, recent exposure, distance and randomness all matter.

`road_response` exposes the response probabilities, detection radius, thresholds,
delay, standoff, dwell, timeout, retreat and cooldown. The default 4 km perception
radius is a synthetic choice, not a claim about measured lion hearing. Responses
never teleport the lion and may time out before reaching the road. Causal tests
check that a car precedes its response, approaching reduces road distance without
requiring a zone entry, and protected activities remain uninterrupted. These are
known synthetic relationships for later prediction experiments, not evidence
that a future predictor will generalize to real collars. No predictor is trained
here; hidden-state columns are analysis labels, not observed inputs.

## Modelling and discretization assumptions

1. Positions use a flat Cartesian map in kilometres, not latitude/longitude or
   a geographic projection. Timestamps are naive simulated local times, with
   seconds and no timezone/DST transitions. Each default day is
   `[05:00, next 05:00)`, with a final GPS fix at the right boundary.
2. There are **1,441 GPS fixes** (indexes 0–1440) and **1,440 hidden-state rows**.
   A hidden row describes its one-minute interval; its bars and raw zone are
   recorded before that interval's movement and continuous bar update. Events
   carry within-minute seconds, but position and physiology are integrated at
   minute resolution. Fractional-minute activity is assigned to that minute's
   main behaviour; the seven behaviour categories sum to 24 hours.
3. Every day starts at the Den centre, asleep. Initial bars reset independently.
   Temperature starts at ambient × the daily heat latent, clipped to `[0,1]`.
   Wake time is a clipped normal draw rounded to a whole second; the matching
   `WOKE_UP` is always the first event. Initial and midday waking are followed by
   grooming. Night catnap waking can be followed by quiet rest before the next patrol leg.
4. Groom durations use an arithmetic-mean-12-minute lognormal distribution
   (default log-space sigma 0.45). Drinks use a gamma distribution (shape 2,
   mean 8 minutes). Behaviour durations round to whole minutes with a one-minute
   minimum. Ordinary rest is 30–90 minutes, other visits 8–25 minutes, and local
   night walking 2–8 minutes by default. These additional ranges are configurable
   synthetic choices, not measured animal parameters.
5. Midday sleep occurs after reaching Shade, at most once daily. Its normal
   scheduled wake is clipped to 14:00–18:00; cooling can wake the lion after
   14:00. A behaviour normally chooses its next goal when it ends, so period
   boundaries never teleport the animal; only explicit physiological or scheduled
   interrupts can cancel a committed journey, with a recorded reason.
6. Goal scores use distance to zone **centre**, noisy logits, and a numerically
   stable softmax. Unspecified afternoon/evening priors are low (`0`); explicit
   none values are `-5`. Hunger determines hunting eligibility. No-catch night
   destinations are restricted to Plain/Den. The post-catch feeding sequence
   takes precedence over further goal sampling, including the night priors.
7. Patrol speed is calculated from the current energy, temperature and boredom
   with per-minute noise, bounded by the configured patrol speed range. Heading persistence blends toward
   the noisy desired bearing using wrapped angles. Stalking and short local
   night walks stay within their current target zone. Map-edge displacements
   reflect; resting true-position jitter stays inside its existing named zone.
   There is no obstacle, terrain, prey-agent, carcass, or road-vehicle geometry.
8. Entry hysteresis uses consecutive **true-position samples**. The initial
   considered zone is Den, without an `ENTER_DEN`. A no-zone gap resets an
   unfinished candidate but preserves the last confirmed named zone. Returning
   to that same zone emits no duplicate entry; another named zone must first
   be confirmed. Internal event `zone`, hidden `zone`, and internal report
   `current_zone` use raw true-position lookup, which can be null. Exported
   event JSON has no `zone` field.
9. Stalking is permitted only during the configured evening hunting window and
   above the daily hunger threshold. A discretized Poisson encounter uses
   `1-exp(-rate/60)` each eligible minute, allowing at most one chase per minute.
   Failed attempts cost energy/boredom/mood, rest 10–20 minutes, and may resume
   before 22:00. Hunting time includes chase minutes and excludes failure rest.
10. Chase direction is random; distance equals chase speed × duration. The
    burst appears between adjacent minute fixes. Start and outcome fit in the
    same minute, with the configured default 20–40-second delay. Success factor
    interpolates linearly between 0.6 and 1.3 using normalized equal energy/mood
    weights, then the final probability is clipped to `[0.05,0.6]`.
11. A catch sends the lion to Feeding spot. Eating ends below hunger 0.1 or
    after 150 minutes, followed by terminal sleep there. Internal traffic may continue after that sleep, without new public events. The day boundary truncates unfinished behaviours;
    no events from the next independent day are invented.
12. Sleeping energy recovery, stationary awake depletion, and moving depletion
    are alternative rates: walking's `-0.12/h` replaces `-0.04/h`; it is not
    added to it. All five bars receive independent Gaussian noise each minute
    and clip to `[0,1]`. Boredom can accumulate in an unchanged no-zone region.
    Mood relaxes toward 0.5. Bars are not exposed to a report consumer.
13. Ambient temperature uses two smoothly joined cosine arcs: a 9-hour rise
    from 05:00 to 14:00 and a 15-hour fall back to 05:00. Temperature relaxation
    uses an exponential one-hour time constant, with movement and cooling-zone
    offsets. Temperature is a dimensionless synthetic index, not degrees.
14. Tourist count is Poisson for the daily window; conditional arrival seconds
    are uniform and sorted. Traffic is counted wherever the lion is and may
    share a timestamp. Mood effects use distance to the **nearest road point**,
    not its centre. Minute integration applies that minute's car effects before
    movement. Equal-time events retain deterministic insertion order.
15. Observation noise is independent per coordinate/fix. The first GPS fix is
    always observed, so forward filling is well-defined; later dropout samples
    retain `missing=true` and repeat the preceding observed coordinates.
    Underlying true positions keep moving. Noisy observations are not clipped
    to map bounds, though images show fixed map limits.
16. Report events are `(previous_report, report_time]`, with the first report
    also including day start. The endpoint GPS fix is included. After-midnight
    reports use the following calendar date. The next-zone class in summaries
    means the next confirmed `ENTER_*` strictly **after** the report; absence
    is `END_OF_DAY`. The final report has no target and is excluded from
    `targets.csv` and all loss evaluations.
17. The requested behaviour budgets are diagnostic reference means, not forced
    daily quotas. Resting combines sleep and quiet rest for the 16–20-hour
    check, while the summary also reports them separately. Two short grooming
    sessions cannot generally average 1.5 hours; eating depends on catches, and
    drinking depends on visits. Default ranges beyond resting are explicit
    modelling assumptions in `validation.hours_ranges`. Budget warnings do
    not invalidate otherwise consistent event logs or claim biological realism.
18. The token vocabulary is exactly 17 names (cars are internal traffic, never event tokens). `ENTER_WATER`,
    `ENTER_HUNT`, `ENTER_FEED`, and `ENTER_ROAD` map to Waterhole, Hunting ground,
    Feeding spot, and Road. A chase outcome must immediately follow its start
    in the public event sequence; a meal requires an unused catch; sleep is allowed only in
    Den, Shade, Feeding spot, or Plain.
19. To preserve causal ordering within a minute, entry events use random seconds
    0–9 and ordinary activity events generally use 12–59. Wake-following grooming
    is delayed by a random 1–19 seconds and can cross into the next minute;
    state durations remain minute-quantized. A just-confirmed entry minute cannot
    also initiate a chase. Meal end and subsequent sleep use ordered subwindows.
    These sequencing conventions preserve the exact public event vocabulary.

## Validation and summary interpretation

`validation_report.json` exposes per-day errors and aggregate behaviour-budget
warnings. Hard failures produce exit code **1**; configuration/input errors
produce **2**. Unexpected execution failures mark the manifest as failed and
retain successful-day counters and an explicit execution error. Completed
runs with only statistical warnings exit **0**.

`summary_stats.json` contains event counts per day (mean/min/max), all 17 token
frequencies, mean behaviour hours, catch-day fraction, chase success rate,
mean zone entries, next-zone counts/proportions for every report clock time,
and total/mean/min/max tourist cars. A success rate with no chases is `null`.
The complete effective configuration is saved in `run_manifest.json`.

The modules mirror their filenames: configuration, geometry, simulator state
machine, event helpers, reports, plotting, I/O, validation/statistics, and CLI
are separate so parameters and rules can be inspected independently.

## Updated behaviour and diagnostic assumptions (tasks 1–5)

These rules supersede the earlier minute-model descriptions where noted:
hunting-day eligibility is frozen from start_hunger > hunt_threshold. Hungry
days stage for an evening hunt; the first stalking encounter uses a bounded
3–25-minute exponential wait to ensure an attempt. Other days do not hunt.
Hunting goals, entries and chases are forbidden outside the configured hunting
window. A catch commits to Feed/eat/sleep. Night naps are at least 25 minutes,
at most four cycles in phase two, with terminal sleep extending to day end.
Short naps retain the original 20–60-minute draw and a 25-minute minimum; longer
night stops include quiet rest after waking.
Trips are committed; physiological and schedule interruptions record an
abandoned goal and reason in hidden_state. Traffic curiosity does not freely
cancel a committed journey. Heat shifts shade departure earlier, waking later,
and multiplies drinking duration. True displacement measures walking speed;
GPS jitter is not counted as patrol speed.

The initial 200-day diagnostic had no Road entries. To make afternoon visits
possible, staging moved from 16:30 to 17:00, committed Road/Water trips finish
before staging, and an afternoon water probability of 0.65 was added. Road
selection depends on boredom and decreasing traffic volume probability; its
percentage is measured, not forced. Other new controls live in `learnability.behaviour`;
reference checks live in `targets`, and map coverage uses a 0.5 km grid from
`statistics`. No check ranges were widened to obtain passes. WARN means a finite
statistic outside its reference range; FAIL means a missing statistic or broken
invariant. Undefined correlations are null with an explanation. Tortuosity uses
true path/chord sums between consecutive zone entries, excluding zero chords.
The final stats_report.md/json are the authority on remaining deviations.

## Baseline ladder (task 6)

Statistics runs now read the persisted `targets.csv` and report L0–L4 held-out
multiclass log loss, in nats. The table keeps its original six columns and adds
`shade_entry_hour_bucket`, `drinks_so_far`, `chase_attempts_so_far`, `catch_so_far`.
Cues use only events at or before report time, never hidden bars or daily latents;
`not_yet` represents no observed shade entry. Catch is an observed-event boolean.

Sorted day IDs are assigned round-robin to five folds. Each day is held out
once, and every report from that day stays outside its fold's training counts.
Tiny runs use `min(5, day_count)` folds and disclose that number. Results report
fold mean and population standard deviation for each report, headline reports
1–5, and all reports. L0 is frequency only; L1 adds report index; L2 adds current
zone and last event. Unseen L1/L2 cells fall back one level.

L3 uses coarse observed-history bins: absent/early/late shade entry (cut at 11:00),
and 0/1/2+ drinks, chase attempts and catches. Catch is normally binary, so its
third bin is unused unless multiple catches are present in supplied data. L3
interpolates rather than discarding sparse cells:
`p_L3 = (class_count + k * p_L2) / (cell_count + k)`, with k=5. An empty L3 cell
therefore equals L2 exactly. L0–L2 use Laplace alpha=1 across all nine classes.
The report gives the zero-training-cell fraction, and each fold's paired daily
headline L3−L2 gap and standard error. Those fold gaps are diagnostics, with no
pass/fail test. The S5 headline improvement target is reported separately.

`learnability.headline_reports`, `cv_folds`, `l3_interpolation_k`, `shade_hour_cut`
and `laplace_alpha` control evaluation. Legacy `train_fraction` and
`l3_min_cell_count` remain loadable but are unused. No holdout outcomes tune
counts, bins or priors. Missing per-report samples produce null values rather
than invented losses. Fewer than two days yields insufficient data.

The original noise/determinism interpretation remains a heuristic based on
all-report losses; it is not a biological validation. Historical 70/30 results
below should not be directly compared with the new cross-validation averages.

Measured phase-6 check (`--stats-only --stats-days 200 --seed 42`): 19 PASS,
3 WARN, 0 FAIL. Held-out losses were L0=1.810101, L1=0.979962,
L2=0.821198 and L3=0.842583 nats (entropy 1.800828). L3 was 2.60% worse
than L2; sparse historical cues do not automatically improve a finite-sample
counting baseline. The requested interpretation was `learnable`. Outstanding
warnings: Road-entry days 6.5%, resting 15.754 h, walking 6.272 h. Full report:
[phase-6 statistics](outputs/run_20261101_210910/stats_report.md). All 143 tests
passed. These measured deviations were not removed by adjusting target ranges.


## Hidden-state oracle (tasks 7–8)

```sh
python -m lionsim.run --oracle --oracle-days 100 --oracle-rollouts 100 --seed 42
```

Oracle mode evaluates every usable report in the first N independent days.
Use `--oracle-days` rather than `--days`, `--stats-days` or `--day-index` in this
mode. CLI oracle sizes override the corresponding `learnability` defaults;
both the effective workload and full model configuration are in the manifest.
Daily files and images are omitted by default. `--keep-files` retains original
daily JSON/GPS/hidden state, never rollout trajectories or snapshots.

For a resumable diagnostic pilot:

```sh
python -m lionsim.run --oracle --oracle-days 20 --oracle-rollouts 100 --seed 42 --workers 4 --chunk-size 10
python -m lionsim.run --resume outputs/run_YYYYMMDD_HHMMSS --workers 4 --chunk-size 10
```

A snapshot deep-copies position, bars, mode, goal, hysteresis, memories, RNG,
daily latents, committed schedules and recorded history. Resuming with the saved
RNG reproduces all original events, GPS noise/dropouts, traffic and hidden rows.
The engine integrates minute ticks: snapshots are immediately before the report
minute's tick. Entries stamped at second zero are already observed, so oracle
branches condition their entry timing on that fact; they cannot shift those
entries into future targets. Previously committed delayed events and scheduled
wakes remain part of the hidden state.

Branch streams are derived by SHA-256 of the saved PCG64 state, day index and
minute, then `SeedSequence.spawn`. This does not consume the original stream.
Branches retain daily latents and committed durations; they resample future
decisions and unobserved future Poisson traffic. Cars at or before the report
boundary, previous exposure and pending reactions are preserved. The oracle
therefore does not benefit from the original day's pre-generated future cars.

Each branch runs the full remainder of the day. Its first strictly future entry
(or END_OF_DAY) contributes to one of nine counts. Probabilities are
`(count + alpha) / (rollouts + 9 * alpha)`, using the same Laplace alpha as the
baselines. `oracle_report.json` stores timestamped counts, class probabilities,
actual original targets and log loss. `oracle_report.md` shows the comparison
and each report's time, target and probability in human-readable tables.

The oracle/L0–L4 comparison reports headline indices 1–5 and all reports using
the same out-of-fold days and mean-across-fold weighting, with fold standard
deviations. The all-day row-weighted oracle loss is also shown separately.
With fewer than two completed days the comparison is explicitly unavailable.
S6 checks `targets.oracle_l0_ratio_range` (0.25–0.50) and
`targets.oracle_l2_improvement_min` (10%) separately for both scopes. An oracle
above L2 is labeled **too noisy**; a ratio below 0.25 is labeled **too deterministic**
and proposes increasing `learnability.softmax_temperature` before remeasurement.
The proposal does not change parameters. These diagnostics describe this generator,
not empirical calibration guarantees. The old absolute near-zero/near-L0 rules
are superseded; the absolute near-zero setting still describes smoothing resolution.

Finite rollout counts and smoothing limit the result. Even unanimous 100-rollout
predictions with alpha=1 have loss `-log(101/109) = 0.076227` nats. Reports expose
this floor and whether the near-zero threshold is resolvable. A small-day pilot
can give unstable baseline ordering; do not equate its heuristic classification
with evidence from a large independent evaluation.

## Acceptance and changes (tasks 9–10)

The acceptance suite covers event schema, strict future targets, hunt cutoffs,
committed goals and interrupt reasons, configured nap limits, statistics keys,
200-day counting losses, exact oracle continuation, checkpoint recovery, legacy
configuration migration, seed/worker reproducibility, and text-free images.

Tests exposed two timing issues fixed in version 3.2.1: independent event-second
jitter could make a 25-tick nap appear shorter than 25 minutes, and oracle
branches could move an entry already observed at the report boundary into the
future. Nap wake seconds now respect the sleep-start second; an interval with
insufficient remaining seconds becomes quiet rest. Oracle branches condition
on the zero-second entry observation. No behavior probabilities, latent ranges,
nap limits, speed values or target-check ranges were tuned in tasks 7–10.
Configuration grouping changed paths, not model values. New oracle settings
control evaluation workload and interpretation only.

## Verified delivery (2026-11-02, version 3.2.1)

The required `--stats-only --stats-days 200 --seed 42` run completed all 200 days:
**19 PASS, 3 WARN, 0 FAIL**. All 200 days passed event invariants. The three
warnings remain unchanged; their reference ranges were not widened.

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| zone_entries_per_day | **PASS** | 6.28 | [6.0, 12.0] |
| zone_entry_share.Den | **PASS** | 0.0398 | [0.03, 0.35] |
| zone_entry_share.Shade | **PASS** | 0.1919 | [0.03, 0.35] |
| zone_entry_share.Kopje | **PASS** | 0.176 | [0.03, 0.35] |
| zone_entry_share.Waterhole | **PASS** | 0.0916 | [0.03, 0.35] |
| zone_entry_share.Hunting ground | **PASS** | 0.1139 | [0.03, 0.35] |
| zone_entry_share.Feeding spot | **PASS** | 0.0549 | [0.03, 0.35] |
| zone_entry_share.Plain | **PASS** | 0.3217 | [0.03, 0.35] |
| zone_entry_share.Road | **PASS** | 0.0104 | {'minimum_exclusive': 0, 'maximum': 0.35} |
| hunt_attempt_day_fraction | **PASS** | 0.68 | [0.5, 0.7] |
| catch_day_fraction | **PASS** | 0.345 | [0.2, 0.4] |
| road_entry_day_fraction | **WARN** | 0.065 | [0.1, 0.25] |
| unique_sequence_fraction | **PASS** | 0.5 | {'minimum_exclusive': 0.3} |
| top_five_sequence_share | **PASS** | 0.25 | {'maximum_exclusive': 0.5} |
| mean_walking_speed_kmh | **PASS** | 2.9516 | [2.0, 4.0] |
| hours_per_behaviour.resting | **WARN** | 15.7542 | [16.0, 20.0] |
| hours_per_behaviour.walking | **WARN** | 6.2716 | [1.0, 5.0] |
| hours_per_behaviour.hunting | **PASS** | 0.8713 | [0.2, 3.0] |
| hours_per_behaviour.grooming | **PASS** | 0.4175 | [0.1, 2.5] |
| hours_per_behaviour.eating | **PASS** | 0.5352 | [0.0, 1.5] |
| hours_per_behaviour.drinking | **PASS** | 0.1502 | [0.0, 1.0] |
| event_invariants | **PASS** | 0 | 0 |


[Full 200-day statistics](outputs/run_20261102_105804/stats_report.md) and
[machine-readable report](outputs/run_20261102_105804/stats_report.json).

The 140/60-day baseline split gives L0=1.810101, L1=0.979962,
L2=0.821198 and L3=0.842583 nats; interpretation **learnable**.
L3 remains 2.60% worse than L2; the sparse-cell backoff is reported honestly.

The corrected oracle pilot completed 20 days × 7 reports × 100 rollouts
in two resumable chunks. Its 42 held-out targets are from days 15–20:

| Model | Same pilot holdout loss (nats) |
| --- | ---: |
| L0 | 1.861813 |
| L1 | 1.192013 |
| L2 | 1.318674 |
| L3 | 1.318674 |
| oracle | 0.460304 |

Pilot interpretation: **balanced**; smoothing floor **0.076227 nats**.
This is a 20-day diagnostic, not the default 100-day experiment. Its L2/L3
values are higher than L1 on this small holdout; no ordering was forced.
Compare models within the same table, not across different test sets.

[Timestamped oracle report](outputs/oracle_verified/run_20261102_105804/oracle_report.md)
and [probability/count details](outputs/oracle_verified/run_20261102_105804/oracle_report.json).

Final acceptance command: `python -m pytest -q`. Results and exact local
interpreter commands are recorded in `PROGRESS.md`.

## Phase-two S1–S5 reference measurement

The implemented distribution is **4.4.1**, with schema **lionsim-v4**.
All 182 tests pass. The final 200-day seed-42 run has **33 PASS, 7 WARN, 0 FAIL**;
all hard event invariants pass. [Complete results and every changed knob](docs/PHASE2_RESULTS.md)
include the full target table and per-report CV losses.

Key measured improvements: no traffic abandonments, 0.605 real abandonments/day,
86% waterhole days, 11% Road-entry days, all Road entries after 19:00, and
13.25% headline L3 improvement over L2. All four S5 correlation targets pass.

The requested calibration is **not fully achieved**: entries/events per day,
Den/Road shares, sequence uniqueness, traffic–Road correlation and walking
hours remain warnings. Walking is 5.794 h/day despite the daytime budget;
required trips and the new scouting route can exceed that budget. No targets
were widened, and no extra events were generated merely to reach a count.

[Final statistics](outputs/phase2_s5_verified/run_20261102_200914/stats_report.md)
and [JSON report](outputs/phase2_s5_verified/run_20261102_200914/stats_report.json).
This is the S1–S5 reference measurement; the larger S6 evaluation follows.


## Phase 2 S6 final evaluation

Package **4.5.0** preserves the S5 trajectories. The 100-day oracle used 100
rollouts per report in five 20-day chunks; the final 500-day statistics used
five 100-day chunks. All days pass hard event validation. Exactly **27 text-free
PNGs** cover days 1–3, with no minute files or images for later days.

Full pytest: **185 passed**. Final statistics: **32 PASS, 8 WARN, 0 FAIL**. Headline L3 improves over L2 by
**7.42%**. Remaining warnings are entries/day (7.392), events/day (18.198),
Den/Road entry shares (2.81%/1.68%), sequence uniqueness (30.8%),
traffic–Road correlation (−0.3438), report-6 END_OF_DAY share (37%), and walking
(5.759 h/day). The uniqueness fraction depends on sample size.

On its matched 100-day evaluation, oracle headline loss is **0.440580 nats**,
**45.83% below L2**. Oracle/L0 is **0.2452 headline, 0.2209 overall**, both below
the requested 0.25–0.50 range: **too deterministic** by the S6 criterion.
A proposed next calibration experiment is to increase
`learnability.softmax_temperature` and remeasure; no such tuning was applied.

[Full target checks, per-report losses, oracle comparison, all changed knobs and
reproduction commands](docs/PHASE2_S6_RESULTS.md).
[500-day statistics](outputs/phase2_s6_final/run_20261103_085841/stats_report.md).
[100-day oracle](outputs/phase2_s6_oracle/run_20261102_202029/oracle_report.md).

Explicit `--image-days 3` now enables those images in stats/oracle mode;
without that option these modes remain image-free. Images are checked and
repaired through ordinary `--resume`. S6 adds only the two evaluation thresholds
`targets.oracle_l0_ratio_range=[0.25,0.50]` and
`targets.oracle_l2_improvement_min=0.10`; it changes no behavior parameters.
S7 regression coverage is documented in [the test audit](docs/PHASE2_TEST_COVERAGE.md).


## Phase 2 S7 regression audit

S1–S7 are complete. Full pytest: **189 passed in 36.42s**.
All nine S7 requirements are mapped to named tests in the
[coverage audit](docs/PHASE2_TEST_COVERAGE.md). The audit adds exact next-day
05:00 boundary cases and strengthens feast-night, four-nap-limit, per-fold
interpolation and same-seed traffic/report checks. Fixed-seed behavior tests
retain loose bounds; deterministic contracts retain exact assertions.

No simulator code, configuration settings or model parameters changed in S7.
The S6 calibration and oracle warnings remain unresolved; passing regression
tests establishes the implemented contracts, not that every statistical target
has been met.
