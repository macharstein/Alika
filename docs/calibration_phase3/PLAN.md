# Bounded phase-three calibration

Authorization: user requested addressing the documented S8.3 failures. Acceptance thresholds stay unchanged. Only phase-three movement/model settings may change; event rules, report schedule, latents, GPS noise, stalking/chase and existing phase-two behavior remain fixed.

Movement selection uses **100 days, seed 137**, not the seed-42 confirmation population. Compare the current default (urgency penalty zero) and exactly three declared candidates before selecting one. Files A.json/B.json/C.json are frozen before evaluation. All have stronger urgency-dependent steering, urgency suppression of discretionary detours and modestly faster travel, bounded by the existing 2–4 km/h cap. A has fewer detours; B increases detour incidence; C strengthens steering and speed slightly further. No extra candidates will be searched solely to cross a target threshold. Keep every outcome, including failures.

Selection order: event invariants and hard movement guardrails first, then number of passing movement targets, then distance to missed movement targets. L4 performance is reported but must not select movement coefficients. Confirm the selected candidate once on **500 days, seed 42**, then evaluate its matched 100-day/100-rollout oracle. Failures remain failures; a bounded attempt is not permission to relabel them.

L4 diagnosis is separate. No hidden inputs or future labels may become predictor features. Any learned bins/smoothing must use training days only; no searching held-out losses. Report any departure from the original three-bin implementation and compare with L3 on identical folds.

Package 5.3.0 protects the new urgency-detour configuration contract. Schema remains v5. Default urgency suppression is initially zero for a runnable compatibility increment; selecting a calibrated default follows measurement and a separate commit.
