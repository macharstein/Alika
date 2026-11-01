# Lion GPS collar simulator

Generate independent 24-hour days for **one synthetic lion**, with minute GPS
fixes, 17 event tokens, daily event/report JSON logs, and text-free path images
every three hours. This is a configurable stochastic simulator for inspecting synthetic
data, not an empirically calibrated model of lion behaviour. There is no machine
learning, training code, or external service dependency.

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
| `--image-days K` | Explicitly limit rendering to the first K selected days; default is **every day** |
| `--no-images` | Disable all report images and contact sheets; overrides image-days |
| `--workers W` | `1`; independent worker processes |
| `--day-index I` | Regenerate exactly original day I, **1-based**; overrides days |

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
completed days. No oracle is implemented in this phase.

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

Groups are `time`, `map`, `randomness`, `bars`, `goal`, `behaviours`, `movement`,
`chase`, `tourists`, `road_response`, `behaviour`, `targets`, `statistics`,
`learnability`, `output`, `images`, and `validation`. The primary randomness
knobs—including latent ranges, bar noise, softmax temperature, heading noise,
GPS noise/dropouts, and base catch probability—are grouped under `randomness`.
Duration distribution parameters sit alongside their respective behaviours.

```sh
python -m lionsim.run --config my_config.json \
  --set randomness.gps_noise_sd_m=25 \
  --set randomness.softmax_temperature=0.9 \
  --set 'randomness.latent_ranges.start_hunger=[0.6,1.0]' \
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
   grooming. Night catnap waking is followed by walking.
4. Groom durations use an arithmetic-mean-12-minute lognormal distribution
   (default log-space sigma 0.45). Drinks use a gamma distribution (shape 2,
   mean 8 minutes). Behaviour durations round to whole minutes with a one-minute
   minimum. Ordinary rest is 30–90 minutes, other visits 8–25 minutes, and local
   night walking 2–8 minutes by default. These additional ranges are configurable
   synthetic choices, not measured animal parameters.
5. Midday sleep occurs after reaching Shade, at most once daily. Its normal
   scheduled wake is clipped to 14:00–18:00; cooling can wake the lion after
   14:00. A behaviour normally chooses its next goal when it ends, so period
   boundaries do not teleport the animal or interrupt a journey.
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
    is an explicit `no_future_entry` category, including the final report.
17. The requested behaviour budgets are diagnostic reference means, not forced
    daily quotas. Resting combines sleep and quiet rest for the 16–20-hour
    check, while the summary also reports them separately. Two short grooming
    sessions cannot generally average 1.5 hours; eating depends on catches, and
    drinking depends on visits. Default ranges beyond resting are explicit
    modelling assumptions in `validation.hours_ranges`. Budget warnings do
    not invalidate otherwise consistent event logs or claim biological realism.
18. The token vocabulary is exactly 17 names (CAR_PASSED is internal traffic only). `ENTER_WATER`,
    `ENTER_HUNT`, `ENTER_FEED`, and `ENTER_ROAD` map to Waterhole, Hunting ground,
    Feeding spot, and Road. A chase outcome must immediately follow its start
    ignoring cars; a meal requires an unused catch; sleep is allowed only in
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

`summary_stats.json` contains event counts per day (mean/min/max), all 18 token
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
at most three cycles, with the last extending to day end to avoid chatter.
Trips are committed; physiological and schedule interruptions record an
abandoned goal and reason in hidden_state. Traffic curiosity does not freely
cancel a committed journey. Heat shifts shade departure earlier, waking later,
and multiplies drinking duration. True displacement measures walking speed;
GPS jitter is not counted as patrol speed.

The initial 200-day diagnostic had no Road entries. To make afternoon visits
possible, staging moved from 16:30 to 17:00, committed Road/Water trips finish
before staging, and an afternoon water probability of 0.65 was added. Road
selection depends on boredom and decreasing traffic volume probability; its
percentage is measured, not forced. Other new controls live in `behaviour`;
reference checks live in `targets`, and map coverage uses a 0.5 km grid from
`statistics`. No check ranges were widened to obtain passes. WARN means a finite
statistic outside its reference range; FAIL means a missing statistic or broken
invariant. Undefined correlations are null with an explanation. Tortuosity uses
true path/chord sums between consecutive zone entries, excluding zero chords.
The final stats_report.md/json are the authority on remaining deviations.

## Baseline ladder (task 6)

Statistics runs now read the persisted `targets.csv` and report L0–L3 held-out
multiclass log loss, in nats. The table keeps its original six columns and adds
`shade_entry_hour_bucket`, `drinks_so_far`, `chase_attempts_so_far`, `catch_so_far`.
Cues use only events at or before report time, never hidden bars or daily latents;
`not_yet` represents no observed shade entry. Catch is an observed-event boolean.

The first 70% of sorted unique day IDs train frequency tables; the remaining
whole days form the holdout (no report from a test day trains any table). L0 is
frequency only; L1 conditions on report index; L2 adds current zone/last event;
L3 adds the four history cues. Every class—including END_OF_DAY—gets Laplace
alpha=1. Unseen L1/L2 cells back off one level. L3 cells with fewer than 10
training observations back off to L2. These values are configurable under
`learnability`; no thresholds are chosen using held-out labels.

The report gives test-target entropy, absolute loss gaps and relative gaps
(previous minus next, divided by previous), and backoff counts. If the spread
of L0/L1/L2 divided by L0 is at most 3%, interpretation is `mostly noise`; if
L2/L0 is below 0.2 it is `nearly deterministic`; otherwise `learnable`. These
are the requested diagnostic heuristics, not proof of biological realism.
Losses are measured honestly; no sorting or forced ordering is applied. Fewer
than two days yields an explicit insufficient-data result with null losses.

Simulator version 3.1.0 prevents resuming older checkpoints that lack these
history cues. Start a new statistics run for baseline evaluation; existing
completed datasets and their reports remain untouched. Task 7 (oracle) is not
implemented here.

Measured phase-6 check (`--stats-only --stats-days 200 --seed 42`): 19 PASS,
3 WARN, 0 FAIL. Held-out losses were L0=1.810101, L1=0.979962,
L2=0.821198 and L3=0.842583 nats (entropy 1.800828). L3 was 2.60% worse
than L2; sparse historical cues do not automatically improve a finite-sample
counting baseline. The requested interpretation was `learnable`. Outstanding
warnings: Road-entry days 6.5%, resting 15.754 h, walking 6.272 h. Full report:
[phase-6 statistics](outputs/run_20261101_210910/stats_report.md). All 143 tests
passed. These measured deviations were not removed by adjusting target ranges.
