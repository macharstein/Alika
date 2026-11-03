# Bounded phase-three calibration

Authorization: user requested addressing the documented S8.3 failures. Acceptance thresholds stay unchanged. Only phase-three movement/model settings may change; event rules, report schedule, latents, GPS noise, stalking/chase and existing phase-two behavior remain fixed.

Movement selection uses **100 days, seed 137**, not the seed-42 confirmation population. Compare the current default (urgency penalty zero) and exactly three declared candidates before selecting one. Files A.json/B.json/C.json are frozen before evaluation. All have stronger urgency-dependent steering, urgency suppression of discretionary detours and modestly faster travel, bounded by the existing 2–4 km/h cap. A has fewer detours; B increases detour incidence; C strengthens steering and speed slightly further. No extra candidates will be searched solely to cross a target threshold. Keep every outcome, including failures.

Selection order: event invariants and hard movement guardrails first, then number of passing movement targets, then distance to missed movement targets. L4 performance is reported but must not select movement coefficients. Confirm the selected candidate once on **500 days, seed 42**, then evaluate its matched 100-day/100-rollout oracle. Failures remain failures; a bounded attempt is not permission to relabel them.

L4 diagnosis is separate. No hidden inputs or future labels may become predictor features. Any learned bins/smoothing must use training days only; no searching held-out losses. Report any departure from the original three-bin implementation and compare with L3 on identical folds.

Package 5.3.0 protects the new urgency-detour configuration contract. Schema remains v5. Default urgency suppression is initially zero for a runnable compatibility increment; selecting a calibrated default follows measurement and a separate commit.

## Recorded extensions after failed initial trials

A/B/C all improved walking but regressed urgency/speed because the multiplicative speed boost saturated the 4 km/h cap; none was adopted. D retained B geometry with speed intercept restored to 0.85 (slope 0.4), and was also rejected as an accepted default: walking and several correlations still missed. All these results remain in the record.

A final E mechanism revision aligns the departure heading toward the first waypoint/goal in proportion to frozen urgency, addressing very short urgent trips starting with an unrelated inherited heading. It also raises planned minimum sideways displacement to 0.6 km so smoothing is less likely to erase the requested 0.4 km visible detour. It uses D's speed/steering settings and the predeclared training-tertile/k=20 counting baseline. E is evaluated on diagnostic seed 137 and independent seed 271 before one seed-42 confirmation. No further geometry candidates are planned in this bounded attempt; any remaining target misses must be reported. These two extensions are explicit departures from the original three-candidate cap, motivated by diagnosed regressions, not concealed searches.
