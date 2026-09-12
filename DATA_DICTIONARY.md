# Data dictionary

Times ending in `_us` are microseconds; `_ms` means milliseconds. Percentages end in `_pct` or use the percentage label in the column name. A row represents 1 signature, candidate, report, histogram bin or summary group, depending on its file. Identifiers are local to their board/run; do not join records across boots using timestamps alone. The main signing and stage CSVs under `measurements/` preserve their recorded field names.

## Archived measurements

`algorithm`, `operation` and `security_level` identify the measured operation. `time_us` is signing latency and `run_number` is the recorded sample identifier. The deep ESP32 and RP2040 files each contain 10,000 ML-DSA-44 and 10,000 archived FN-DSA-512/Falcon signing measurements. The latter use the archived Falcon implementation. Each inter-unit file has 1,000 ML-DSA signing measurements per parameter set (44, 65 and 87). These builds differ from the controlled campaign described in `settings.json`.

`measurements/archived/x86_iterations.csv` has `parameter_set`, `run_number` and `iterations`, with 10,000 rows per parameter set. The original export stored iteration counts under a generic `time_us` heading; this release gives that column its correct name. These records are loop counts, not microcontroller latencies.

## Controlled signing

| Field | Meaning |
|---|---|
| `board`, `uid`, `set` | Recorded board label, hardware identifier and ML-DSA parameter set |
| `boot_block` or `block` | Reset-separated block, numbered 0 to 4 |
| `key` or `key_id` | Benchmark key identifier, 0 to 9 |
| `message` or `message_id` | Message identifier, 0 to 4 |
| `repetition`, `index`, `invocation_id`, `rand_index` | Recorded repetition, invocation or randomness-stream position; use the field together with its run/block |
| `start_us`, `end_us`, `elapsed_us`, `sign_us`, `verify_us` | Timer values, signing duration and separate verification duration |
| `K` | Number of signing candidates, including the accepted candidate |
| `n_z`, `n_w0`, `n_ct0`, `n_hint` or `reject_*` | Rejection counts at each source-level exit |
| `partition` | Calibration or the specified unseen-key/boot holdout |
| `sign_rc`, `rc`, `verify_rc` | Recorded return codes; 0 indicates success |
| `siglen` | Signature length in bytes |
| `rng_ok`, `k_ok`, `stack_guard` | Recorded integrity checks; 1 indicates a pass where the check is enabled |
| `sha256` | Signature digest recorded after timing |

For main measurements, `K = 1 + n_z + n_w0 + n_ct0 + n_hint`. Calibration uses keys 0 to 7 in blocks 0 to 2. The other partitions contain unseen keys, unseen boots or both. ESP32 block files contain 10,000 rows each; RP2040 files contain 50,000 rows per board/set.

Pilot files retain their own phase/mode fields. RP2040 pilot JSONL preserves `events` (nested checkpoint arrays) and `reject` (counts ordered z, w0, ct0, hint). Mode 0 is plain, 1 counts and 2 stages; warmup rows are labelled separately. Plain-mode rejection counters are disabled, so `K=0` does not mean a signature used zero candidates. ESP32 plain-mode `k_ok=-1` means that check was not enabled. Pilot and warmup rows are excluded from the main signing dataset.

## Stage diagnostics

RP2040 stage rows describe candidates. `attempt` identifies the candidate within `invocation`; `reason` is 0 for acceptance, 1 for z rejection, 2 for w0 rejection, 3 for ct0 rejection and 4 for hint rejection. Checkpoint times end in `_us`; `attempt_us = exit_us - entry_us`. A checkpoint recorded as 0 was not reached. The diagnostic `partition` labels are separate from the main dataset.

ESP32 `campaign.csv` contains 1,000 whole-signature records. Its `stage_events.csv` contains 17,100 checkpoint records with `invocation`, `candidate`, `label`, `t_us` and `overflow`. Labels are 0 candidate entry, 1 checkpoint before z-path arithmetic, 2 z check passed, 3 entry to the w0 norm check, 4 z rejection, 5 w0 rejection, 6 ct0 rejection, 7 hint rejection and 8 acceptance. The firmware names label 1 ZSCAN, but its source placement precedes the z arithmetic as well as its norm check. Label 2 to label 3 encloses the additional product, inverse NTT, subtraction and reduction. All recorded overflow values are 0.

## Telemetry

Each condition lasts 600 s and releases 60,000 acquisition jobs. The reporting periods are 100, 250 and 1,000 ms, giving 6,000, 2,400 and 600 report releases per run. Each mode/period has 3 replicates. Replicate numbers in these CSV condition columns are 1 to 3; a baseline has period 0 and replicate 0. `inline` shares the acquisition core, while `worker` signs on the other core. The baseline performs no signing.

ESP32 report rows preserve `rep_id` (the zero-based report identifier), `released_us` and release-relative `started_off_us`/`ready_off_us`. `queue_depth` is recorded occupancy; `fixture_id` selects the repeated fixture. `status=0` means complete. `digest` is the recorded 64-bit SHAKE256 signature digest, compared with host-verified reference signatures. All 54,000 reports complete; a report is late when `ready_off_us > period_ms * 1000`.

ESP32 acquisition histograms have 500 us bins. `hist_bucket_us` is the lower edge; the 15,500 us bin also contains larger values. `start_jitter` and `completion_response` count executed jobs; skipped jobs are excluded. Exact counts for all 19 runs, including the baseline, are in `measurements/telemetry/esp32_runs.csv`. Here `on_time + late + skipped = acquisition_releases` and `late + skipped = acquisition_misses`. The exception file records acquisition index, release-relative start, execution duration and skipped status; a skipped job has `start_off_us=-1`. Exception logging is bounded; use the exact run counters in the results for total misses. The derived ESP32 summary contains 18 signing conditions; the measurement run table includes all 19 runs.

RP2040 report rows use run-relative `release`, `start`, `ready` and `available` timestamps in microseconds. Signing latency is `ready-start`; report response is `ready-release`; `available-ready` includes the post-signing output check. Flags are 1 dropped, 2 completed and verified in-window, 4 unfinished at the observation boundary, and 6 verified completion after that boundary. The absent timestamp sentinel is 4,294,967,295. Late reports have `ready-release > period_ms * 1000`. Window-based failure totals add late in-window reports, drops and censored reports. The 20 flag-6 completions are included among the 115 censored reports, not counted again as in-window completions.

RP2040 histogram bins 0 to 99 represent 100 us response intervals; bin 100 contains responses exactly 10,000 us and bin 101 contains responses greater than 10,000 us. Skipped jobs are excluded from the histogram. In `rp2040_end.csv`, `executed + skipped = acquisition_released`; acquisition misses are `late + skipped`. Exception `response` uses the absent sentinel for skipped jobs. Only the first 1,000 exceptions per run are stored; the end counters cover the full run. `rp2040_start.csv` records the acquisition iterations and duration used for each run.

## Numerical results and source map

`controlled-results/model_coefficients.csv` contains fitted baseline and rejection costs in microseconds. `model_validation.csv` reports errors separately for calibration and each held-out partition. `shared`, `two` and `separate` identify a shared rejection cost, early/late costs and separate observed-exit costs. `B`, `Rz` and `Rlate` denote baseline, early and late costs. Sample maxima and upper residuals are observed quantities. Error quantiles use the reported population and units.

`archived-reanalysis/` contains the archived timing summaries, sample-derived deadline estimates, histogram/gap sensitivity and sample-size results. `B_upper_us` and `C_upper_us` are sample upper costs; `D821_us` is their 821-iteration deadline estimate. Sample-size rows are derived resamples, not additional hardware measurements. Seeds and repetition numbers identify those draws. Summary filenames describe their corresponding manuscript analysis.

`SOURCE_FILES.csv` maps released files to preserved source records, source identifiers, SHA-256 digests and conversions. Rows marked `manuscript-derived-20260911` or `derived-results-20260912` are derived results saved for the revised manuscript, rather than a Git commit identifier. Source labels identify recorded inputs; the supplied measurements are self-contained. The label `measurement-record` identifies a recorded experimental input rather than a public Git revision.

`envelope_exceedances.csv` lists 29 held-out calls above the two-increment calibration envelope. `separate_envelope_exceedances.csv` lists the 5 corresponding exceedances of the separate-exit model, calculated from the supplied coefficients and main records. These are different model envelopes.

Version 1.0.1 uses NIST's July 2026 potential corrections for derived deadlines. In `deadline_estimates_reproduced.csv`, `n_errata_cap` and `deadline_errata_cap_ms` replace the former `n_fips` and `deadline_fips_ms` fields. The primary budgets are 32, 64 and 96; the corrected cap reference is 821. Sample-size and extreme-sensitivity column names now contain `821` in place of `814`. The measurements and fitted stage costs are unchanged.

`iteration_summary_reproduced.csv` retains `fips_expected_iterations` for the published August 2024 values and adds `errata_expected_iterations` for the proposed corrections. `errata_geom_*` and `errata_common_geom_*` replace the former nominal/conservative quantile fields and use the corrected per-set and common references. In `iteration_budget_sensitivity.csv`, `tail_at_95` and `tail_at_96` are geometric extrapolations, with ratios explicitly labelled against the published 2024 or corrected reference. They are not empirical rare-event frequencies.

`controlled-results/mldsa65_iteration_reference.csv` summarizes each RP2040 set-65 record and their pool. `signatures` is the number of accepted signatures; `candidates` is the sum of K; rejection totals sum the recorded exit counters. The pooled row contains the same observations as the 2 unit rows and must not be added to them. `hint_rejections_per_candidate` divides hint rejections by all candidates; `hint_rejections_per_post_norm_candidate` divides them by accepted signatures plus hint rejections, since no ct0 rejection occurred.

Version 1.0.2 adds 4 files under `controlled-results/`:

- `pooled_iteration_intervals.csv`: 1 row per parameter set. `mean_iterations` uses all signatures in the specified device pool. `cluster_ci_lo` and `cluster_ci_hi` are pointwise 95% t intervals across 10 shared key means, with 9 degrees of freedom; `cluster_se` is the standard error. `naive_ci_*` treats calls independently and is included as a sensitivity comparison. `n_1e9_*` maps the point mean or unrounded clustered endpoints to geometric iteration budgets.
- `iteration_key_clusters.csv`: 1 row per parameter set and shared key identity. Counts and sums allow reconstruction of the pooled means and clustered intervals. Each key pools all its measured boards, messages and boots. Set 44 uses the same 10 key fixtures on ESP32 and both RP2040 units; it therefore has 10 clusters, not 20 or 30.
- `rejection_mechanism_comparison.csv`: 1 row per set, retaining parameters, counts, measured hint rates, simplified and finite-width norm means, and residual intervals. The simplified mean is `(1-beta/gamma1)^(-256*l) * (1-beta/gamma2)^(-256*k)`. The finite-width mean replaces `beta` by `beta+0.5` in both factors to retain the strict norm inequalities' integer endpoints. These remain approximations based on uniform and independent coefficients.
- `iteration_analysis_notes.json`: interval formulas, conditioning, shared-key identity check and primary sources.

In the mechanism comparison, the conditional hint rate is `H/(N+H)`, where `N` is accepted signatures and `H` is hint rejections; no ct0 rejection was observed. Each norm prediction is divided by `1-h` for the measured hint adjustment. The residual interval is calculated from per-signature `Y = K - M_finite_width*(1+n_hint)` using the same key clustering, which retains covariance between K and the hint count. It tests the mean discrepancy rather than treating the hint-rate estimate as independently known. These intervals do not establish universal acceptance probabilities or independently measured rare-event rates.
