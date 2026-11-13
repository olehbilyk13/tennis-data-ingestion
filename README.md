# Tennis Prediction Engine — Raw CSV Ingestion

Research-only automated ingestion of TennisMyLife raw CSV files, without model or betting changes.

## Schedule
GitHub Actions checks the three sources at **07:00, 10:00, 21:00 Europe/Kyiv** using a summer/winter UTC candidate schedule and a Kyiv-time guard. GitHub scheduled jobs can run late; a sufficiently delayed invocation might be skipped.

- `2025.csv`
- `2026.csv`
- `ongoing_tourneys.csv`

## Verification and history
The runner downloads the actual source bytes and checks HTTP 200, nonempty payload, <=5 MB, UTF-8 CSV, 50 columns, consistent row widths, no exact duplicate rows, SHA-256, byte count, and data row count. Each run writes a manifest containing source metadata and observed UTC time.

A verified SHA-256 with an existing unexpired GitHub Actions artifact is marked `NO_CHANGE` without another upload. New SHA values are archived as **immutable GitHub Actions artifacts**, one per CSV. Logs and a run manifest are also available on each GitHub Actions run.

**Retention limitation:** workflow artifacts expire after up to 90 days (or the repository's shorter configured maximum). This is NOT a permanent historical archive. If an artifact expires, the next run may archive the same SHA again. The checksum identifies content, not source publication time.

## Boundaries
- Does **not** write to Google Drive; a separate authenticated sync mechanism is still needed.
- Does **not** modify frozen models, odds, bets, or operational journals.
- Does **not** claim the provider's historical as-of cutoff or no-lookahead is independently verified; this must be checked downstream.
- This public repository includes code only; consider source redistribution rights before publishing archived source content.

[Actions](https://github.com/olehbilyk13/tennis-data-ingestion/actions)
