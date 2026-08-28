# Changelog

## Unreleased — v0.3

- Add historical FX rate selection with `--rate-date YYYY-MM-DD`.
- Add batch quotation normalization with `--quotes`.
- Add `--output-dir` batch output and `normalization-manifest.json`.
- Preserve exact decimal strings for original and normalized quotation prices in provenance metadata.
- Expand test coverage for historical rates, invalid dates, same-currency historical provenance and batch outputs.

## v0.2

- Add structured JSON output.
- Add quotation-file normalization for direct `rfqdiff` handoff.
- Preserve FX normalization provenance.

## v0.1.0

- First public release.
- Add live currency conversion CLI.
- Use Decimal-based money calculations.
- Add API and connection error handling.
