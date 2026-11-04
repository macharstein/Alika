# Known limitations — frozen simulator 6.0.0

`sim-v6.0.0-frozen` freezes reproducible code, not scientific acceptance. The
seed **3003**, **500-day** measurement has these remaining limitations:

| Metric | Measured | Revised target |
|---|---:|---:|
| Zone entries/day | 7.38 | >=7.5 |
| Events/day | 18.3 | >=19 |
| Top-five zone-sequence share, N=500 | 0.258 | <=0.25 |
| Event-token unique fraction, fixed N=200 | 0.779 | >=0.85 |
| Hot-day shade advance versus overcast | 41.8 min | >=45 min |
| Hot-day waterhole fraction | 0.789 | >=0.85 |

The matched **100-day, 100-rollout-per-report** oracle/L0 headline ratio is
**0.285**, inside the requested0.28–0.45 range. L3w is only about **0.4% better
than L3** (headline losses0.828229 versus0.831862). Weather therefore adds little
incremental signal to this counting baseline, although several weather traces are
visible. These are synthetic measurements, not field validation of lion behaviour.

Seeds **42, 2026 and 3003 were inspected during calibration** and must not be
presented as unseen validation/test data. The dataset plan also forbids137,271
and9999 for main/robustness generation. Seed9999 is allowed only in the explicitly
labelled smoke role; smoke outputs must never be merged into a release dataset.

The declared phase-six checks were26 PASS,4 WARN,3 FAIL. Two failures concern
low events and zone entries; the third is an aggregate flag for the same new
zone-entry hard-failure status. No previously passing correlation deteriorated.
No behaviour, threshold or parameter was changed to create this frozen release.

Full measurement and definitions: [PHASE6_RESULTS.md](PHASE6_RESULTS.md).
The main dataset size N remains unspecified until explicitly supplied; this
checkpoint authorizes only the20-day smoke test, not full generation.
