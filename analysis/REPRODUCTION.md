# Clean reproduction record (round 6)

A fresh copy of this folder was run end to end against the public dataset (`mldsa-timing-data`,
`measurements/` tree as released), with `bash run_all.sh <data> <out> <figures>` into empty output
directories. Environment: Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, matplotlib 3.11.2; wall time about 13 minutes.

## Fixes made during the run

Two defects in the package itself were found and fixed; neither affects any number:

* `run_all.sh` resolved its three path arguments after changing directory, so relative paths failed.
  The paths are now resolved to absolute paths first.
* `verify3.py` accessed the `flags` column as `rr.flags`, which newer pandas versions interpret as
  the DataFrame flags object. It now uses `rr["flags"]`.

## Checks

Every regenerated output was compared with the manuscript and supplement:

| Item | Output | Result |
|---|---|---|
| Table VIII (B+, C+, governing exit, R_z, R_w0, R_h, n_h, D_ctl(96), exceedances) | `envelope_controlled.csv` | all 7 rows match |
| Table IX (partial and complete-server utilisation, all periods) | `utilisation.csv` | all ranges match |
| Sec. VII-D: G, df, chi-square and simulated p-values; Pearson statistics; sensitivity thresholds, power at threshold, SD for 80% power; F and its critical value | `round4_stats.csv` | match to the stated decimals |
| Sec. VII-D: per-key SDs, variance components, F p-values, mixture tail ratio at the set's own budget (1.0–1.8%), leave-one-key-out range, budgets | `heterogeneity_summary.csv` | match |
| Sec. VII-D: 35 autocorrelations (largest 0.011, two beyond 2 SE), runs test | `acf.csv` | match |
| Sec. VII-D boot F tests; Sec. VIII-D held-out counts by K; two-stage coverage 10/10/8 | `round3.txt`, `replay_two_stage.csv` | match |
| Sec. IX-D level 1: 42 runs, counts reproduced, RP2040 timestamps exact, ESP32 ready within 0.12 ms except two runs at 0.57 ms | `replay_level1.csv` | match |
| Sec. IX-D admission-rule check: 28 of 72,000, margins <= 111 us, 21 inline / 7 worker directions, alternative rules 26/27/56/143/282 and 1,651 | `replay_race.csv`, `replay_race_direction.csv`, `replay_race_variants.csv` | match |
| Sec. IX-D level 2: dropped error -3.1 to +2.6%, late within 2.5% (100 ms); late -13.5 to +10.1% (250 ms); conditional coverage 8/12 and 6/12 | `replay_level2a.csv` | match (error defined as observed minus replay median, relative to observed; the text now says so) |
| Sec. IX-D ESP32: cross-replicate 326–464, permutation ranges and <= 11% change, controlled pool 500–608 and 0–7 | `replay_level2a.csv`, `replay_permutation_esp32.csv`, `replay_level2b_esp32.csv` | match |
| Sec. IX-D / X quiet-benchmark counterfactual: -6.9 to -13.1% drops, -17.0 to -35.2% late | `quiet_benchmark.csv` | match |
| Tables II, IV, VII; Sec. VIII-B/C; Table S1 | `modes.txt` | match |
| Tables V, VI; Sec. VI-B | `controlled_fits.txt` | match |
| Sec. IX-B, IX-C counts | `telemetry_counts.txt`, `telemetry_reports.txt` | match |
| Tables S2, S3, S4, S5, S6 | the CSVs above | match |
| Table S7 key-bootstrap supports | `heterogeneity_summary.csv` | two values with weight 6e-5 and 1e-6 were missing from the table and have been added |
| Figs. 4–9, 11 | `<figures>/*.pdf` | text layers identical to the manuscript figures |
| NIST spreadsheet digest (reference [10], Sec. S-II) | `sha256sum` of the retrieved file | 5bc93ce6…7a34c793, matches |

Not checked by this run, because the inputs are outside this folder: the correspondence between
the telemetry firmware sources and Table III (requires the firmware tree), and the contents of the
dataset release tag cited in the manuscript (requires the published release).

## Addendum (round 7)

`round7.py` (overhead, baselines, attainable-target validation, ct0 bound) was added after the run
recorded above. Its outputs `overhead.csv`, `baselines.csv` and `deadline_validation.csv` were
produced by running it once against the same data in the same environment; the numbers in Sections
IV-B, VIII-E and IX-D and Tables IX, S8 and S9 were copied from those files. `run_all.sh` now includes
it, so the next clean run covers it too.

## Addendum (round 8: fresh-input ESP32 telemetry set)

The 18 fresh-input ESP32 runs were captured on 10 October 2026 (one ESP32, ML-DSA-44, inline and
worker at 100, 250 and 1,000 ms, 600 s each, three replicates with keys 1-3, the stored randomised
condition orders of the first set). On the host, `tools/check_report_signatures.py` compared every
report digest with the reference signatures regenerated from the run seeds: 54,000 checked, 0
mismatches, 0 signing errors, 0 length errors. `ingest_fresh.py` then built
`measurements/telemetry/esp32_reports_fresh.csv` (54,000 rows) and `esp32_runs_fresh.csv` (18 rows)
from the capture folders; the reports file is identical to the one assembled on the capture host.

`fresh_esp32.py`, `utilisation.py` and `fig_telemetry.py` were run once against the dataset with
these two files added, in the same environment as the round-6 run, and the manuscript numbers were
copied from their outputs:

| Manuscript item | Output | Checked |
|---|---|---|
| Sec. IX-C: 529/544/515 and 528/544/515 late at 100 ms (8.6-9.1%), 0/3/5 at 250 ms, none at 1,000 ms; share above 100 ms 6.8-7.3% | `fresh_esp32.csv` | match |
| Sec. IX-D: controlled-pool medians 554-557, intervals cover 6 of 6, errors -7.8 to -1.8%; other-replicate errors -5.4 to +2.8%, 6 of 6 covered; level 1 exact; baseline +16.3 to +20.8% | `fresh_esp32.csv`, `fresh_esp32_summary.txt` | match |
| Sec. IX-B: 22,008/21,899/21,927 inline acquisition misses at 100 ms; 0 in worker runs | `esp32_runs_fresh.csv` | match |
| Table III: fresh-input dispatch 0.22-0.23 ms (inline), 0.13-0.14 ms (worker); post-signing 1.56-1.61 ms | `fresh_esp32.csv`, `utilisation.csv` | match |
| Table X fresh rows (47.4-50.6 / 49.1-52.4 ms; 0.49, 0.19-0.20, 0.05; 0.50-0.51, 0.20-0.21, 0.05) | `utilisation.csv` | match |
| Table S10 (18 rows) | `fresh_esp32_summary.txt` | rows copied verbatim |
| Fig. 10 | `telemetry_results.pdf`, `telemetry_outcomes_points.csv` | regenerated; 72 points |

`run_all.sh` now runs `fresh_esp32.py` when `esp32_reports_fresh.csv` is present and always draws
Fig. 10 with `fig_telemetry.py`; the next clean run covers both.

## Addendum (round 9: overhead regression, independent forecast, frozen rule)

Three additions were run once against the same data in the same environment and their outputs
copied into the manuscript: `round7.py` section A now regresses the paired pilot difference on the
candidate count and on the exit counts (Sec. IV-B, Table S8: slopes 0.52/0.70, 10.66/10.28,
72.93/72.75 us per candidate on units 1/2 at 44/65/87, 0.07 on the ESP32; intercepts 3.4/3.4,
-21.5/-20.7, -54.7/-52.8, -29.2); `fresh_esp32.py` adds the independent forecast (controlled-pool
signing times with dispatch and post-signing constants drawn from the other fresh replicates; seed
19; Sec. IX-D and Table S10: medians 550-556, errors -7.9 to -1.1% at 100 ms, 6 of 6 covered; 4 of 6
at 250 ms) and the level-1 timestamp check of the fresh runs (every ready time within 0.1 ms except
the first request of each run, 0.70-0.72 ms); `frozen_rule.py` writes the pre-registered rule and
deadlines (`frozen_rule.json`, sha256 5c90edb53fc3edeb24949294f66ead4eac5315fc5dc1459e9b4d2109e12288ff,
recorded in the validation session before any block was captured). The validation blocks themselves
are recorded in the next addendum once captured.

## Addendum (round 9: validation blocks)

Captured 10-11 October 2026, 21:07-00:09 ACDT, session `validation_20261010_210745_0ebafb85`, both RP2040
boards (rp2040_1 = E66368254F75782F, rp2040_2 = E663AC91D321B038, the hardware IDs of the original
session), campaign firmware build 7a8c23b6... (UF2 sha256 cacc9f3e...), host `validate_blocks.py` importing
the unchanged `campaign.py`; package files verified against the original CHECKSUMS.json at start. Smoke
check first (`smoke_20261010_210459_54fb394c`, 50 calls per set and board, all phases COMPLETE). The session
record carries `frozen_rule_sha256 = 5c90edb53fc3edeb24949294f66ead4eac5315fc5dc1459e9b4d2109e12288ff`,
equal to the hash of `frozen_rule.json` written by `frozen_rule.py` from the original campaign before the
session started. Twelve phases (6 per board: sets 65, 44, 87 x boot blocks 5 and 6), each COMPLETE with
5,100 recorded invocations (100 warm-up + 5,000 main); completion.json status COMPLETE, no errors.

`ingest_validation.py` re-validated every main row with the campaign's `validate_result()` and wrote the six
CSVs (10,000 calls each). `validation_blocks.py`, reading B+, C+ and D(n_eps) from the frozen file only, gave
the numbers of Sec. VIII-F and Table X: P1 0 exceedances of D(K) for K>=2 in all six configurations (smallest
margin 0.126-0.204 ms); P2 0 first-candidate exceedances; P3 at 1e-2 21-33 exceedances per 10,000, Wilson
upper bound below 1% everywhere; at 1e-3 1-4 exceedances, upper bound below 0.1% in five, 0.103% for unit 1
ML-DSA-44; all exceedances with K > n_eps; P4 pooled 581 vs 539.3 (1e-2) and 67 vs 55.0 (1e-3), unit 1
ML-DSA-65 19 vs 9.69 at K>32 (one-sided Poisson p = 0.005). The unfrozen original envelope for unit 1
ML-DSA-65 (C+ = 42.697 ms) would have had 6 exceedances on the same calls. The script was run once on the
captured data; nothing in the frozen file was changed afterwards.

## Addendum (round 10: overhead model)

`round7.py` section A now fits the paired pilot difference as `a + b (K - 1)`, so the intercept is the
shift of a first-candidate call, and adds `b / R_z` with R_z from `envelope_controlled.csv` (run
`envelope_controlled.py` first, as `run_all.sh` does). Outputs copied into Sec. IV-B and Table S8:
a = +3.93/+4.14, -10.83/-10.40, +18.25/+19.92 us (units 1/2 at 44/65/87), -29.14 us (ESP32); b unchanged;
b/R_z at most 0.0027%, 0.0310%, 0.1459%, 0.0009%. Mean differences of the K=1 pairs: +3.14/+1.59,
-10.72/-12.63, +19.34/+21.25, -29.00 us. Table S11 (frozen-rule provenance) was generated from
`frozen_rule.json` and the original campaign files.

## Addendum (round 11: clean run of the v1.1.0 release candidate)

On 11 October 2026 the release candidate `mldsa-timing-data-v1.1.0/` was assembled as it will be published:
the v1.0.3 files unchanged, `measurements/telemetry/esp32_*_fresh.csv`, the six validation CSVs and
`validation_summary.json`, `validation/` (frozen rule, its hash, the session record), `references/` (the
NIST spreadsheet, SHA-256 5bc93ce6...7a34c793), `raw/` (three capture/firmware archives with SHA256SUMS)
and this `analysis/` folder. A fresh copy of `analysis/` was run with `bash analysis/run_all.sh
../mldsa-timing-data-v1.1.0 out figs` into empty directories (Python 3.13, numpy/pandas/scipy/matplotlib as
installed; 10 min 14 s; no errors). Compared with the manuscript and the earlier records:

| Check | Result |
|---|---|
| `frozen_rule.json` regenerated from the main campaign | byte-identical to the pre-registered file; SHA-256 5c90edb5...e12288ff, equal to `validation/session.json` |
| Table X (validation blocks) | all six rows identical to the manuscript (`validation_blocks.txt`) |
| Sec. VIII-F numbers (margins, rates, Wilson limits, 581/539, 67/55, 19 vs 9.69) | identical to `validation_blocks.csv` of the round-9 analysis |
| Sec. IV-B and Table S8 (overhead, fit a + b(K-1), b/R_z) | `overhead.csv` identical; all seven Table S8 rows regenerate verbatim |
| Sec. IX-D and Table S10 (fresh-input forecasts, conditional and independent) | `fresh_esp32.csv` identical; all 18 Table S10 rows regenerate verbatim |
| Table IX (held-out attainable targets) | all seven rows regenerate verbatim |
| Table S9 (baselines) | all 30 printed rows regenerate verbatim (the 6 ESP32 250 ms rows with zero observed are not printed) |
| Table XI (utilisation) | first-cohort rows unchanged from round 6; fresh-input rows give the printed ranges |
| The 30 outputs of the round-6 clean run | identical (byte-for-byte or numerically) |
| Figs. 4-11 | text layers identical to the manuscript figures |

The raw archives were checked separately: `ingest_validation.py`, run on the session extracted from
`raw/rp2040-validation-session.tar.gz` with the campaign's own `validate_result()` re-applied to every row,
rebuilt the six validation CSVs byte for byte; `ingest_fresh.py`, run on the capture folders extracted from
`raw/esp32-fresh-telemetry-captures.tar.gz`, rebuilt both fresh-input CSVs exactly.

Not reproducible from this folder alone: the device measurements themselves (they need the boards), and the
firmware builds (they need ESP-IDF 5.2.1 and the Pico SDK; sources and build records are in `raw/` and in the
v1.0 release's firmware references).

## Addendum (round 13: hint path and randomness streams)

Two scripts were added. `hint_path.py` measures the hint path from the stage diagnostics (accepted
candidates do the same work as hint-rejected ones up to the hint-count check), tests the envelope with
that cost on the held-out and validation calls, reads the separated upper groups of the archived traces as
the hint path (D(96) and D(821) without them and with the hint cost scaled in) and counts hint rejections
per unit. `randomness_check.py` checks the recorded RP2040 signing-randomness streams; it uses only the
Python standard library. `raw/` gains a fourth archive, `rp2040-campaign-randomness.tar.gz` (the 42 stream
files of the original campaign with their sidecars, SHA-256 ebe5b564...fa064f82); the validation session's
streams were already in `raw/rp2040-validation-session.tar.gz`. `make_figs2.py` now labels the four upper
observations of Fig. 4b as hint-path observations.

On 11 October 2026 a fresh copy of `analysis/` was run with `bash run_all.sh` on the updated release
candidate into empty directories (no errors). Compared with the manuscript and the round-11 run:

| Check | Result |
|---|---|
| The outputs of the round-11 clean run | all byte-identical |
| `frozen_rule.json` | SHA-256 5c90edb5...e12288ff, unchanged |
| Table VII last two columns, Table S1, Table IV n_h | regenerate from `hint_path_archived.csv` |
| Sec. VI-C numbers (medians and maxima, 68 hint rejections, mid-rank mean 0.532, KS p = 0.395, ratios, ct0 offsets); Table S12 | `hint_path_stages.csv`, `hint_path.txt` |
| Sec. VIII-D stage envelope (0 exceedances held-out and validation; C+_stage vs C+_cal); Table S13 | `hint_path_envelope.csv` |
| Sec. VI-B and VIII-D hint shares, unit-1 ML-DSA-65 counts; Table S14 | `hint_counts.csv`, `hint_path.txt` |
| Sec. VIII-C probabilities of a hint observation in 1,000 signatures (0.60, 0.16, 0.41) | `hint_path.txt` |
| Sec. VIII-D and S-XIII randomness checks (54 files, 378,000 records, 0 duplicates, chi-square p 0.002-0.963) | `randomness_check.txt`, identical to the check run on the original capture folders |
| Figs. 4-11 | text layers identical to the manuscript figures |
