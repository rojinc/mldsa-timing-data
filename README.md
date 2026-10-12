# ML-DSA timing data


This dataset measures how ML-DSA rejection sampling affects signing latency and the timing of concurrent acquisition tasks on ESP32 and RP2040 microcontrollers. It contains individual measurements, numerical results and the information needed to interpret each field.

| Measurements | Coverage |
|---|---|
| Controlled signing | 350,000 signatures; ESP32 ML-DSA-44 and 2 RP2040 boards at ML-DSA-44, 65 and 87 |
| Archived timing | 26,000 ML-DSA and 20,000 archived Falcon signing latencies |
| Iteration counts | 30,000 instrumented x86 observations |
| Stage diagnostics | 1,000 ESP32 and 6,000 RP2040 signatures |
| Telemetry | 75 runs of 600 s: 57 in the first cohort, including a no-signing baseline on each board, and 18 fresh-input ESP32 runs |
| Validation blocks | 60,000 RP2040 signatures in 12 new boot blocks, testing a calibration rule frozen beforehand |

## Download and read

Download [version 1.1.0](https://github.com/rojinc/mldsa-timing-data/releases/tag/v1.1.0), or use **Code > Download ZIP**. CSV files open directly in spreadsheet and statistical software. RP2040 pilot files use JSONL to retain nested diagnostic events. No code or firmware is required to read the data.

| Folder | Contents |
|---|---|
| [`measurements/`](measurements/) | Individual signing, stage and telemetry records, archived measurements and instrumentation pilots |
| [`controlled-results/`](controlled-results/) | Fitted models, held-out errors, telemetry summaries and completed validation records |
| [`archived-reanalysis/`](archived-reanalysis/) | Archived timing summaries, deadline estimates and sensitivity results |
| [`validation/`](validation/) | The frozen calibration rule (`frozen_rule.json`, its SHA-256) and the validation session record |
| [`analysis/`](analysis/) | Scripts that regenerate every table and figure of the manuscript (`run_all.sh`), with `README.md` and `REPRODUCTION.md` |
| [`references/`](references/) | The NIST FIPS 204 potential-updates spreadsheet used for the repetition counts |
| [`raw/`](raw/) | Raw capture archives of the two v1.1.0 data sets, the telemetry firmware with the fresh-input policy, and the recorded signing-randomness streams of the original RP2040 campaign |

[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) explains units and status codes. [`settings.json`](settings.json) records the experimental settings. [`SOURCE_FILES.csv`](SOURCE_FILES.csv) preserves source-file identities, hashes and format conversions. [`CHECKSUMS.sha256`](CHECKSUMS.sha256) identifies the distributed files.

## Interpretation

The controlled signing design crosses 10 keys, 5 messages and 5 boot blocks. Model fitting uses keys 0 to 7 in blocks 0 to 2; the other key/boot partitions are held out. Pilot and stage runs are separate from the 350,000 main signatures.

The first ESP32 telemetry cohort repeats 64 signing-randomness fixtures per key; the second (`*_fresh.csv`) and the RP2040 use distinct per-request inputs. Inline and worker comparisons are paired within each platform. Acquisition misses and report deadline failures are separate outcomes. The records retain dropped requests and reports unfinished at the observation boundary.

The sensitivity tables contain 27 histogram settings per archived trace and 3 gap thresholds per trace. Sample-size rows are derived resamples, not additional device measurements. Superseded telemetry, incomplete attempts and the duplicate archived Campaign B are excluded.

The deadline calculations use the repetition counts in [NIST's July 31, 2026 potential corrections to FIPS 204](https://csrc.nist.gov/pubs/fips/204/final): 4.36, 5.14 and 3.91. The common geometric reference gives budgets of 32, 64 and 96 iterations at 10^-3, 10^-6 and 10^-9, and a cap reference of 821. NIST labels these as proposed corrections, not an official revision.

Version 1.0.2 adds pooled iteration means, intervals clustered on the 10 shared keys, and a comparison of the recorded rejection counts with simplified and finite-width norm approximations. The set-65 interval maps to 96 to 97 iterations at 10^-9 under the geometric premise. The new result files and their interpretation are described in the data dictionary. All 41 measurement files remain byte-for-byte unchanged from version 1.0.0.

Version 1.0.3 adds device and x86 iteration percentiles, their bootstrap summaries, and the exact shared-key bootstrap distributions. All 9 device percentiles match their corrected per-set references; all 9 pointwise 95% key-bootstrap intervals contain those references. This update adds derived results only. The measurement files and earlier numerical results are unchanged.

Version 1.1.0 adds two measured data sets and the files needed to reproduce the analysis. The fresh-input ESP32 telemetry set (`measurements/telemetry/esp32_reports_fresh.csv`, `esp32_runs_fresh.csv`) repeats the 18 ESP32 telemetry conditions with a distinct message and signing randomness for every request. The validation blocks (`measurements/signing/rp2040/validation/`) are 60,000 new RP2040 signatures on the original keys and messages, captured after the calibration rule in `validation/frozen_rule.json` had been fixed; the session record carries that file's SHA-256. `analysis/run_all.sh` regenerates all manuscript tables and figures from this folder in about ten minutes. All measurement files of version 1.0.3 are unchanged.

## Citation

Rojin Chhetri and Babu Pillai. *ML-DSA timing data*. Version 1.1.0, 2026. https://github.com/rojinc/mldsa-timing-data

GitHub's **Cite this repository** option uses [`CITATION.cff`](CITATION.cff).

## Archived data sources

Earlier public records used in the archived analysis are attributed in the source map:

- [PQC measurements on WSN-class hardware](https://github.com/rojinc/pqc-wsn-measurements/tree/22bb5c8d41ced0a9d1e6dc780fe37b0334d448ad), revision `22bb5c8d`.
- [PQC benchmarks on Cortex-M0](https://github.com/rojinc/pqc-cortex-m0-benchmark/tree/3d75d76a16d05753a5f74ef6e721a8a575df4354), revision `3d75d76a`.

The observations used by the manuscript are included in this release.

## Licence

Copyright 2026 Rojin Chhetri and Babu Pillai. This dataset is licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). See [LICENSE](LICENSE) for the terms. Please credit the authors and identify any changes when reusing the data.
