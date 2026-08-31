# Changelog

## Unreleased — v0.5.0

- Cache repeated FX lookups per currency pair, rate date and provider within a batch run.
- Fail before writing batch outputs when source files would map to the same normalized filename.
- Add regression coverage for within-run FX consistency and output collision safety.

## v0.4.0 — 2026-08-31

- Add portfolio normalization policy files with explicit base currency, rate date, provider and optional portfolio ID.
- Allow batch CLI values to override policy values without changing the source policy file.
- Add deterministic, order-independent normalization `run_id` values derived from effective policy and source-file SHA-256 fingerprints.
- Add SHA-256 lineage for every batch source and normalized output file.
- Add policy SHA-256 provenance to normalization manifests.
- Attach batch `run_id` and `portfolio_id` to normalized quotation metadata.
- Add JSON Schema contract for portfolio policies and strengthen manifest lineage schema.
- Expand the test suite with reproducibility, policy override and digest-lineage coverage.

## Release candidate — v0.3.0

- Add historical FX rate selection with `--rate-date YYYY-MM-DD`.
- Add batch quotation normalization with `--quotes`.
- Add `--output-dir` batch output and `normalization-manifest.json`.
- Preserve exact decimal strings for original and normalized quotation prices in provenance metadata.
- Add Frankfurter rate-source attribution and optional provider pinning with `--provider`.
- Add explicit schema identifiers and schema version `1.0` to machine-readable outputs.
- Add JSON Schema contracts for normalized quotations and batch manifests.
- Add a real cross-repository `currency-normalizer → rfqdiff` integration test in CI.
- Expand unit/integration coverage to provider policy, source provenance and contract versioning.

## v0.2

- Add structured JSON output.
- Add quotation-file normalization for direct `rfqdiff` handoff.
- Preserve FX normalization provenance.

## v0.1.0

- First public release.
- Add live currency conversion CLI.
- Use Decimal-based money calculations.
- Add API and connection error handling.
