# Analysis scripts for the revised manuscript

All scripts read the public dataset release (`mldsa-timing-data`, unpacked so that
`<data>/measurements/...` exists) and write CSV results and figures. They need Python 3 with
numpy, pandas, scipy and matplotlib. One command regenerates everything (about 15 minutes on a
recent laptop-class CPU, dominated by the queue replays and the power simulation):

    bash run_all.sh <data> <out> <figures>

Every random draw uses a fixed numpy `default_rng` seed, stated in the table below, so the
outputs are reproducible bit for bit on the same numpy version.

## Scripts

| Script | What it produces | Seeds |
|---|---|---|
| `modes2.py` | Mode extraction on the archived traces, B+/C+, D(n), nested-subset diagnostic (its single-extreme deletion output is no longer reported; Table VII uses `hint_path.py`) | none (bootstraps are enumerated or seeded inside the script) |
| `verify2.py` | Controlled fits (shared/two-cost/separate-exit), hold-out MAE, pooled iteration means and intervals | none |
| `verify3.py`, `verify4.py` | Telemetry outcome counts, censoring rule | none |
| `heterogeneity.py` | Hazard with Wilson intervals, per-key/boot means, variance components, autocorrelation, runs test, mixture tail, exact key bootstrap (full enumeration) | none |
| `fig_hazard.py` | Fig. 7 | none |
| `envelope_controlled.py` | Path-labelled envelope, per-exit costs, exceedances by K, Fig. 9 | none |
| `queue_replay.py` | Simulator (`replay()`), level 1, admission-rule check, level 2a (cross-replicate), 2b (controlled pool), permutation, response curves | level 2a: 1; permutation: 2; 2b: 3; response curves: 5 |
| `fig_replay.py` | Fig. 11 | none |
| `extra_round3.py` | Admission-rule check under alternative rules, two-stage replay intervals, counts of held-out calls by K | two-stage: 11 |
| `utilisation.py` | Partial and complete-server utilisation per run; direction and margin of each admission-rule mismatch | none |
| `round4_stats.py` | Power of the between-key F test (threshold and 80% power), likelihood-ratio test with the common hazard fitted to the inspected risk sets, Pearson chi-square, both calibrated by parametric simulation | power: 2024; calibration: 4042 |
| `quiet_benchmark.py` | Quiet-benchmark counterfactual: RP2040 runs replayed with controlled-campaign signing times | 7 |
| `round7.py` | Counting-mode overhead from the paired pilots (mean difference and its regression on K and on the exits); mean-capacity and share-above-period baselines; held-out exceedance of the prospective deadline at 1e-2 and 1e-3 targets; the ct0 bound per parameter set | none |
| `frozen_rule.py` | The frozen calibration-coverage rule R1 and its pre-registered predictions per configuration, from the original campaign only; writes `frozen_rule.json` and its SHA-256 (must equal the hash recorded in the validation session) | none |
| `ingest_validation.py` | Builds the released validation-block CSVs from a validation session (re-validates every row with the campaign's own checks); run once by the authors | none |
| `validation_blocks.py` | Tests predictions P1-P4 of the frozen rule on the validation blocks (Sec. VIII-F); nothing re-estimated | none |
| `ingest_fresh.py` | Builds `esp32_reports_fresh.csv` and `esp32_runs_fresh.csv` (the two released files of the fresh-input ESP32 set) from the capture folders `telf_r*_*ms`; run once by the authors, not part of `run_all.sh` | none |
| `fresh_esp32.py` | Fresh-input ESP32 runs: outcomes, level-1 and level-2 replays, controlled-pool replay (conditional and independent), baselines (Sec. IX-C, IX-D; Table S10) | other-replicate pools: 13; controlled pool: 17; independent forecast: 19 |
| `fig_telemetry.py` | Fig. 10 (telemetry outcomes, both ESP32 fixture policies) | none |
| `make_figs2.py` | Figs. 4, 5, 6, 8 | none |
| `hint_path.py` | Hint path from accepted candidates (stage diagnostics), ct0 bound, envelope with C+ from accepted candidates on held-out and validation calls, archived upper groups read as the hint path (D(96) and D(821) without them and with the hint cost scaled in), per-unit hint counts and single-hint deficits (Secs. VI-A, VI-C, VIII-C, VIII-D; Table VII last two columns; Tables S1, S12-S14) | none |
| `randomness_check.py` | Hash, record-count, byte-frequency, bit-balance and duplicate checks of the recorded RP2040 signing-randomness streams (Sec. VIII-D; Sec. S-XIII); standard library only | none |

`queue_replay.py` takes the number of Monte Carlo sequences as a third argument (300 in the
manuscript); `round4_stats.py` takes the numbers of power and calibration simulations (2,000 each).
`extra_round3.py`, `utilisation.py`, `round4_stats.py`, `quiet_benchmark.py` and `round7.py` read outputs of the earlier scripts;
`run_all.sh` keeps the order.

## Manuscript-to-output mapping

Table, figure and section numbers follow the manuscript as submitted with this release (13 tables, 11 figures). `REPRODUCTION.md` is a log kept during revision and uses each round's own numbering.

| Manuscript item | Script | Output file(s) |
|---|---|---|
| Tables I, II, IV (scope of earlier work, data sources, scheduler semantics) | none: descriptive; Table II lists the files of this dataset, Table IV comes from the firmware sources and the dataset records | - |
| Tables III, V, VIII; Sec. VIII-B, VIII-C; Table S1 | `modes2.py` (hint-path columns: `hint_path.py`) | `modes.txt`, `hint_path_archived.csv` |
| Table VI; Sec. VI-B (MAE, largest errors) | `verify2.py` | `controlled_fits.txt` |
| Table VII; Sec. VII-A (means, intervals) | `verify2.py` | `controlled_fits.txt` |
| Table XIII (partial and complete-server utilisation) | `utilisation.py` | `utilisation.csv` |
| Sec. IX-B, IX-C (acquisition and report counts) | `verify3.py`, `verify4.py` | `telemetry_counts.txt`, `telemetry_reports.txt` |
| Fig. 7; Sec. VII-B (key bootstrap, Table S7); Sec. VII-D (Wilson intervals, per-key sd, variance component, F, boot F cells, ACF, runs, mixture, leave-one-key-out); Table S5 (per-key means) | `heterogeneity.py` | `hazard.csv`, `per_key.csv`, `per_boot.csv`, `acf.csv`, `loko.csv`, `heterogeneity_summary.csv` |
| Sec. VII-D (LRT G, chi-square, simulated p-values, sensitivity thresholds, power, sd for 80% power); Table S6 | `round4_stats.py` | `round4_stats.csv` |
| Table IX; Fig. 9; Sec. VIII-D (exceedances, increments by K) | `envelope_controlled.py`, `extra_round3.py` | `envelope_controlled.csv`, `envelope_by_K.csv`, `exit_increments.csv`, `round3.txt` |
| Sec. IX-D level 1 (counts, timestamp agreement) | `queue_replay.py` | `replay_level1.csv` |
| Sec. IX-D admission-rule check (28 mismatches, margins, directions); Sec. S-III (alternative rules) | `queue_replay.py`, `utilisation.py`, `extra_round3.py` | `replay_race.csv`, `replay_race_direction.csv`, `replay_race_variants.csv` |
| Fig. 11; Sec. IX-D level 2; Table S2 | `queue_replay.py`, `fig_replay.py` | `replay_level2a.csv`, `response_curves.npz` |
| Sec. IX-D two-stage intervals; Table S3 | `extra_round3.py` | `replay_two_stage.csv` |
| Sec. IX-D ESP32 permutation and controlled-pool replays; Table S4 | `queue_replay.py` | `replay_permutation_esp32.csv`, `replay_level2b_esp32.csv` |
| Sec. IX-D and X quiet-benchmark counterfactual; Sec. S-III | `quiet_benchmark.py` | `quiet_benchmark.csv` |
| Sec. IV-B overhead figures, fit a + b(K-1) and b/R_z; Table S8 | `round7.py` (after `envelope_controlled.py`) | `overhead.csv` |
| Sec. VIII-D frozen rule; Sec. VIII-F validation blocks; Table XII; Sec. S-XII, Table S11 | `frozen_rule.py`, `validation_blocks.py` | `frozen_rule.json`, `validation_blocks.csv` |
| Sec. IX-D baselines; Table S9 | `round7.py` | `baselines.csv` |
| Sec. IV-D, IX-B, IX-C, IX-D (fresh-input ESP32 runs, conditional and independent forecasts); Table XIII fresh rows; Sec. S-XI, Table S10 | `fresh_esp32.py`, `utilisation.py` | `fresh_esp32.csv`, `fresh_esp32_summary.txt`, `utilisation.csv` |
| Fig. 10 | `fig_telemetry.py` | `telemetry_results.pdf`, `telemetry_outcomes_points.csv` |
| Sec. VIII-E, Table XI (attainable-target exceedance) | `round7.py` | `deadline_validation.csv` |
| Sec. VI-A (upper groups as hint path), VI-C (accepted candidates, ct0 bound), VIII-C, VIII-D (hint shares, unit-1 ML-DSA-65 deficit, stage envelope); Table X last row; Tables S12-S14 | `hint_path.py` | `hint_path_stages.csv`, `hint_path_envelope.csv`, `hint_path_archived.csv`, `hint_counts.csv`, `hint_path.txt` |
| Sec. VIII-D and S-XIII randomness checks | `randomness_check.py` (run by `run_all.sh` when both raw archives are present) | `randomness_check.csv`, `randomness_check.txt` |
| Sec. S-VII (Falcon) | `modes2.py` | `modes.txt` |

`REPRODUCTION.md` records the clean end-to-end run made before submission and what it checked.

The RP2040 validation blocks live in `<data>/measurements/signing/rp2040/validation/` (six CSVs with the
columns of the main campaign files, plus `validation_summary.json`; dataset v1.1.0); `run_all.sh` runs
`validation_blocks.py` when that folder is present, after `frozen_rule.py` has regenerated the frozen file.

The fresh-input ESP32 set lives in `<data>/measurements/telemetry/esp32_reports_fresh.csv` and
`esp32_runs_fresh.csv` (dataset v1.1.0); `run_all.sh` runs `fresh_esp32.py` only when the first file is
present, and `fig_telemetry.py` draws Fig. 10 with or without it.

The NIST spreadsheet (reference [11], supplementary Section S-II) is in the release as
`references/fips204-potential-updates.xlsx`; the telemetry firmware with both fixture policies is in
`raw/esp32-telemetry-firmware-fresh-policy.tar.gz`, and the RP2040 campaign firmware and host in
`raw/rp2040-validation-session.tar.gz`; the recorded signing-randomness streams of the original RP2040 campaign are in `raw/rp2040-campaign-randomness.tar.gz`.