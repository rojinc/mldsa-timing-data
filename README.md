# ML-DSA timing data


This dataset measures how ML-DSA rejection sampling affects signing latency and the timing of concurrent acquisition tasks on ESP32 and RP2040 microcontrollers. It contains individual measurements, numerical results and the information needed to interpret each field.

| Measurements | Coverage |
|---|---|
| Controlled signing | 350,000 signatures; ESP32 ML-DSA-44 and 2 RP2040 boards at ML-DSA-44, 65 and 87 |
| Archived timing | 26,000 ML-DSA and 20,000 archived Falcon signing latencies |
| Iteration counts | 30,000 instrumented x86 observations |
| Stage diagnostics | 1,000 ESP32 and 6,000 RP2040 signatures |
| Telemetry | 57 runs of 600 s, including a no-signing baseline on each board |

## Download and read

Download [version 1.0.2](https://github.com/rojinc/mldsa-timing-data/releases/tag/v1.0.2), or use **Code > Download ZIP**. CSV files open directly in spreadsheet and statistical software. RP2040 pilot files use JSONL to retain nested diagnostic events. No code or firmware is required to read the data.

| Folder | Contents |
|---|---|
| [`measurements/`](measurements/) | Individual signing, stage and telemetry records, archived measurements and instrumentation pilots |
| [`controlled-results/`](controlled-results/) | Fitted models, held-out errors, telemetry summaries and completed validation records |
| [`archived-reanalysis/`](archived-reanalysis/) | Archived timing summaries, deadline estimates and sensitivity results |

[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) explains units and status codes. [`settings.json`](settings.json) records the experimental settings. [`SOURCE_FILES.csv`](SOURCE_FILES.csv) preserves source-file identities, hashes and format conversions. [`CHECKSUMS.sha256`](CHECKSUMS.sha256) identifies the distributed files.

## Interpretation

The controlled signing design crosses 10 keys, 5 messages and 5 boot blocks. Model fitting uses keys 0 to 7 in blocks 0 to 2; the other key/boot partitions are held out. Pilot and stage runs are separate from the 350,000 main signatures.

ESP32 telemetry repeats 64 signing-randomness fixtures per key; RP2040 uses distinct per-request fixtures. Inline and worker comparisons are paired within each platform. Acquisition misses and report deadline failures are separate outcomes. The records retain dropped requests and reports unfinished at the observation boundary.

The sensitivity tables contain 27 histogram settings per archived trace and 3 gap thresholds per trace. Sample-size rows are derived resamples, not additional device measurements. Superseded telemetry, incomplete attempts and the duplicate archived Campaign B are excluded.

The deadline calculations use the repetition counts in [NIST's July 31, 2026 potential corrections to FIPS 204](https://csrc.nist.gov/pubs/fips/204/final): 4.36, 5.14 and 3.91. The common geometric reference gives budgets of 32, 64 and 96 iterations at 10^-3, 10^-6 and 10^-9, and a cap reference of 821. NIST labels these as proposed corrections, not an official revision.

Version 1.0.2 adds pooled iteration means, intervals clustered on the 10 shared keys, and a comparison of the recorded rejection counts with simplified and finite-width norm approximations. The set-65 interval maps to 96 to 97 iterations at 10^-9 under the geometric premise. The new result files and their interpretation are described in the data dictionary. All 43 measurement files remain byte-for-byte unchanged from version 1.0.0.

## Citation

Rojin Chhetri and Babu Pillai. *ML-DSA timing data*. Version 1.0.2, 2026. https://github.com/rojinc/mldsa-timing-data

GitHub's **Cite this repository** option uses [`CITATION.cff`](CITATION.cff).

## Archived data sources

Earlier public records used in the archived analysis are attributed in the source map:

- [PQC measurements on WSN-class hardware](https://github.com/rojinc/pqc-wsn-measurements/tree/22bb5c8d41ced0a9d1e6dc780fe37b0334d448ad), revision `22bb5c8d`.
- [PQC benchmarks on Cortex-M0](https://github.com/rojinc/pqc-cortex-m0-benchmark/tree/3d75d76a16d05753a5f74ef6e721a8a575df4354), revision `3d75d76a`.

The observations used by the manuscript are included in this release.

## Licence

Copyright 2026 Rojin Chhetri and Babu Pillai. This dataset is licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). See [LICENSE](LICENSE) for the terms. Please credit the authors and identify any changes when reusing the data.
