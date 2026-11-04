# Phase 4 L5 results — frozen simulator 5.4.0

The declared experiment completed once, with **no post-result tuning, defect fix,
or rerun**. Implementation/settings were committed at `586c347` before execution.
Seed **2026** was absent from every output manifest before this run. All 500 days
completed using four workers, five 100-day chunks with `--resume`, stats-only,
`--keep-files`, and no images. There are 3,500 target rows and five folds with
400 training/100 test days each, exactly matching L0–L4.

Run: `outputs/phase4_l5/run_20261104_093129`. Original artifacts:
[l5_report.md](../outputs/phase4_l5/run_20261104_093129/l5_report.md) and
[l5_report.json](../outputs/phase4_l5/run_20261104_093129/l5_report.json).
Reproduction and assumptions: [L5 analysis](L5_ANALYSIS.md).

**Interpretation:** the heading cue beats its shuffle control, but the specified
L5 interpolation makes predictions worse than L3. This is evidence against this
particular counting baseline at the declared settings, not evidence that heading
contains no predictive information. The LEAKY true-current-goal control also
loses to L3: the prescribed coarse cells do not guarantee an upper bound on
performance, and a positive gap-closed percentage cannot be reported honestly.
No model or parameter was changed in response.

The frozen simulator's existing independent-seed checks are **37 PASS, 13 WARN,
1 FAIL**. The failure is `guardrail_walking_hours` (mean about **6.009 h/day**,
limit 6 h). Other warnings include the preexisting movement-correlation/L4
checks. These remain visible in the original stats_report files; phase 4 neither
changes their definitions nor tunes the simulator to remove them. The prior
seed-42 calibration results do not guarantee this fresh seed passes.

Verified all 1,500 saved source-file hashes, target/statistic hashes, all 500
completion checkpoints, no PNGs, no hidden goal column in targets, and main W20
results identical to the corresponding post hoc row. Existing default values
and simulator/statistics source are unchanged from `a7ff47e`.

---

# L5 observed-heading experiment

Simulator 5.4.0; schema lionsim-v5; seed 2026; 500 days.
Natural-log multiclass log loss; mean and population SD across five held-out day folds.

**NOT HELPFUL**

WORTH INCLUDING: >=5% over L3 AND >=3% over shuffled; MARGINAL: >=2% and <5% over L3; NOT HELPFUL otherwise.
Headline improvement over L3: **-24.84%**; over L5_shuffled: **14.34%**.
The gap closed is undefined because LEAKY L5_truegoal does not improve on L3.

Declared heading settings: {"window_minutes": 20, "min_displacement_km": 0.15, "max_angle_deg": 30, "_comment": "Analysis only: trailing observed displacement window; km threshold; bearing tolerance in degrees. Distance bins are fixed at 1.5 km."}; trailing smoothing 5 minutes; L5 settings {"interpolation_k": 20, "shuffle_seed": 2026, "_comment": "Analysis only: L3 prior pseudo-count and deterministic split-local goal permutation seed. No tuning after results."}.
Speed_recent is displacement/window in km/min. Distance bins use zone centres: <=1.5 km and >1.5 km. The L5 cell uses report index, implied goal and moving flag only.
LEAKY L5_truegoal uses hidden current goals solely as an analysis control; finite-sample counting losses need not improve on L3.

## Headline reports 1–5

| Model | CV mean log loss | Fold SD |
|---|---:|---:|
| L3 | 0.584506 | 0.085013 |
| L5 | 0.729722 | 0.090456 |
| L5_shuffled | 0.851848 | 0.094260 |
| L5_truegoal (LEAKY) | 0.810996 | 0.101461 |

## All reports

| Model | CV mean log loss | Fold SD |
|---|---:|---:|
| L3 | 0.674976 | 0.082757 |
| L5 | 0.857592 | 0.079758 |
| L5_shuffled | 0.946958 | 0.082841 |
| L5_truegoal (LEAKY) | 0.818301 | 0.084651 |

## Per report index

| Report | L3 | L5 | Shuffled | Truegoal (LEAKY) |
|---|---:|---:|---:|---:|
| 1 | 0.093354 | 0.593938 | 0.544085 | 0.450011 |
| 2 | 0.520144 | 0.577450 | 0.846564 | 0.922316 |
| 3 | 0.701078 | 0.709239 | 0.709239 | 0.709239 |
| 4 | 0.751598 | 0.813622 | 0.981483 | 0.899449 |
| 5 | 0.856357 | 0.954362 | 1.177872 | 1.073967 |
| 6 | 0.897923 | 1.258899 | 1.260807 | 0.828241 |
| 7 | 0.904380 | 1.095634 | 1.108655 | 0.844881 |

## Moving subsets

headline: 1253 examples (50.12% of this scope).

| Model | CV mean log loss | Fold SD |
|---|---:|---:|
| L3 | 0.487967 | 0.064725 |
| L5 | 0.611851 | 0.069467 |
| L5_shuffled | 0.913132 | 0.052566 |
| L5_truegoal (LEAKY) | 0.906030 | 0.062202 |

all_reports: 1501 examples (42.89% of this scope).

| Model | CV mean log loss | Fold SD |
|---|---:|---:|
| L3 | 0.621330 | 0.083557 |
| L5 | 0.711617 | 0.067990 |
| L5_shuffled | 1.006479 | 0.061321 |
| L5_truegoal (LEAKY) | 0.943951 | 0.066893 |

| Report | Count | Fraction | L3 | L5 | Shuffled | Truegoal (LEAKY) |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 273 | 54.60% | 0.078294 | 0.431338 | 0.515494 | 0.551532 |
| 2 | 315 | 63.00% | 0.368046 | 0.430582 | 0.872816 | 0.977064 |
| 3 | 0 | 0.00% | N/A | N/A | N/A | N/A |
| 4 | 337 | 67.40% | 0.718514 | 0.774739 | 1.042076 | 0.984328 |
| 5 | 328 | 65.60% | 0.709499 | 0.770428 | 1.154245 | 1.054788 |
| 6 | 151 | 30.20% | 1.235829 | 1.207407 | 1.480349 | 1.110102 |
| 7 | 97 | 19.40% | 1.389220 | 1.226817 | 1.479069 | 1.172917 |

## Stationary subsets

headline: 1247 examples (49.88% of this scope).

| Model | CV mean log loss | Fold SD |
|---|---:|---:|
| L3 | 0.685502 | 0.135923 |
| L5 | 0.853619 | 0.160362 |
| L5_shuffled | 0.795040 | 0.153849 |
| L5_truegoal (LEAKY) | 0.719984 | 0.154435 |

all_reports: 1999 examples (57.11% of this scope).

| Model | CV mean log loss | Fold SD |
|---|---:|---:|
| L3 | 0.715923 | 0.101572 |
| L5 | 0.968779 | 0.111344 |
| L5_shuffled | 0.903609 | 0.108251 |
| L5_truegoal (LEAKY) | 0.725019 | 0.106957 |

| Report | Count | Fraction | L3 | L5 | Shuffled | Truegoal (LEAKY) |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 227 | 45.40% | 0.114240 | 0.792156 | 0.580883 | 0.328726 |
| 2 | 185 | 37.00% | 0.800461 | 0.857515 | 0.828005 | 0.857515 |
| 3 | 500 | 100.00% | 0.701078 | 0.709239 | 0.709239 | 0.709239 |
| 4 | 163 | 32.60% | 0.826594 | 0.902050 | 0.861071 | 0.728717 |
| 5 | 172 | 34.40% | 1.166362 | 1.332557 | 1.254777 | 1.142149 |
| 6 | 349 | 69.80% | 0.746653 | 1.275286 | 1.162226 | 0.702239 |
| 7 | 403 | 80.60% | 0.786327 | 1.062796 | 1.018714 | 0.764579 |

## Moving goal inference

all_reports: 588/1501 correct (39.17%).

| Implied \ True | Den | Feeding spot | Hunting ground | Kopje | Plain | Road | Shade | Waterhole |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Den | 12 | 1 | 5 | 15 | 8 | 0 | 8 | 0 |
| Feeding spot | 0 | 27 | 11 | 11 | 107 | 1 | 0 | 3 |
| Hunting ground | 0 | 0 | 111 | 2 | 106 | 0 | 0 | 1 |
| Kopje | 0 | 0 | 2 | 14 | 11 | 1 | 2 | 5 |
| Plain | 0 | 0 | 2 | 5 | 130 | 0 | 1 | 1 |
| Road | 0 | 2 | 6 | 2 | 28 | 2 | 1 | 51 |
| Shade | 1 | 0 | 3 | 3 | 2 | 0 | 164 | 0 |
| Waterhole | 0 | 1 | 1 | 1 | 23 | 0 | 9 | 128 |
| ambiguous | 7 | 12 | 118 | 14 | 75 | 36 | 159 | 49 |

headline: 514/1253 correct (41.02%).

| Implied \ True | Feeding spot | Hunting ground | Kopje | Plain | Road | Shade | Waterhole |
|---|---:|---:|---:|---:|---:|---:|---:|
| Den | 1 | 5 | 0 | 6 | 0 | 8 | 0 |
| Feeding spot | 27 | 11 | 11 | 99 | 0 | 0 | 2 |
| Hunting ground | 0 | 111 | 1 | 60 | 0 | 0 | 1 |
| Kopje | 0 | 2 | 1 | 4 | 1 | 2 | 5 |
| Plain | 0 | 2 | 5 | 95 | 0 | 1 | 1 |
| Road | 2 | 6 | 1 | 26 | 1 | 1 | 47 |
| Shade | 0 | 3 | 0 | 0 | 0 | 164 | 0 |
| Waterhole | 1 | 1 | 0 | 21 | 0 | 9 | 115 |
| ambiguous | 11 | 118 | 2 | 61 | 6 | 159 | 36 |

## Window sensitivity — post hoc

| Window (min) | Headline L5 | All-reports L5 |
|---|---:|---:|
| 10 | 0.734882 | 0.859024 |
| 20 | 0.729722 | 0.857592 |
| 30 | 0.722480 | 0.840471 |

## Method and reproducibility

Exact hidden goal at the report minute, not trip_goal. LEAKY; never exported in targets.
Fixed SeedSequence(seed, fold, split, report); goals permuted separately within training/test report groups; moving flags unchanged.
Training days only; L5=(cell counts+k*p_L3)/(n+k). L3 Laplace smoothing unchanged. Heading cuts fixed before evaluation.
Raw gap fraction, unclipped; undefined if truegoal does not beat L3.
Declared defaults only; sensitivity is post hoc and never selects the main model.

Day-disjoint folds exactly match L0–L4 in stats_report.json. Training/test day lists, fold losses, input hashes and post hoc details are in l5_report.json.
