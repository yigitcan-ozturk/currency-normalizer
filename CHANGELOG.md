# Changelog

## Unreleased — v0.3.0

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
