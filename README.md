# currency-normalizer

**Auditable FX normalization for supplier quotations.**

[![Tests](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`currency-normalizer` converts supplier quotations into a common currency while preserving the FX assumptions, source policy and reproducibility evidence needed for procurement review. It is the FX-normalization boundary of the engineering procurement toolchain.

## Decision boundary

The tool is responsible for **FX normalization only**. It converts current or historical values, preserves provenance and produces `rfqdiff`-ready quotation JSON. It does not rank suppliers, make treasury decisions, assess technical compliance or hide FX assumptions from downstream reviewers.

## Current capabilities

- current and historical FX normalization;
- `Decimal` arithmetic for money calculations;
- Frankfurter blended rates or a pinned provider such as `ECB`, `BOE` or `TCMB`;
- single-quotation and batch normalization;
- explicit schema/version metadata;
- exact original and normalized decimal values in provenance;
- batch normalization manifests;
- portfolio/base-currency policies;
- deterministic batch `run_id` values;
- SHA-256 lineage for source and normalized files;
- direct `currency-normalizer → rfqdiff` integration validation in CI;
- no third-party Python runtime dependency.

## Quick start

### Normalize one amount

```bash
python main.py 10000 USD EUR
```

Machine-readable output:

```bash
python main.py 10000 USD EUR --json
```

Historical rate:

```bash
python main.py 10000 USD EUR \
  --rate-date 2026-08-01 \
  --json
```

Pinned provider:

```bash
python main.py 10000 USD EUR \
  --rate-date 2026-08-01 \
  --provider ECB \
  --json
```

## Normalize one quotation

Input:

```json
{
  "name": "Supplier B",
  "currency": "USD",
  "price": 85000,
  "lead_time_weeks": 10,
  "payment_days": 30
}
```

Run:

```bash
python main.py \
  --quote supplier_b.json \
  --target-currency EUR \
  --provider ECB \
  --output supplier_b_eur.json
```

The commercial fields remain compatible with `rfqdiff`. FX evidence is added under the `normalization` metadata block.

## Batch normalization

```bash
python main.py \
  --quotes supplier_a.json supplier_b.json supplier_c.json \
  --target-currency EUR \
  --rate-date 2026-08-01 \
  --provider ECB \
  --output-dir normalized
```

This writes one normalized quotation per input and:

```text
normalized/normalization-manifest.json
```

## Portfolio policy

The v0.4 development line adds a reusable portfolio normalization policy. Example:

```json
{
  "schema": "currency-normalizer.portfolio-policy",
  "schema_version": "1.0",
  "portfolio_id": "FY2026-EU-SOURCING",
  "base_currency": "EUR",
  "rate_date": "2026-08-01",
  "provider": "ECB"
}
```

Use it in batch mode:

```bash
python main.py \
  --quotes supplier_a.json supplier_b.json supplier_c.json \
  --policy portfolio-policy.json \
  --output-dir normalized
```

CLI values override policy values when explicitly supplied. For example, `--target-currency GBP` or `--provider BOE` can override the policy for a specific run without modifying the source policy file.

The policy contract is documented in [`schemas/portfolio-policy.schema.json`](schemas/portfolio-policy.schema.json).

## Reproducible run identity

Batch runs receive a deterministic ID such as:

```text
cn-3d3bc1a5a3edb8a836d5
```

The ID is derived from:

- the canonical effective portfolio policy;
- the SHA-256 digest of each source quotation;
- source file names;
- schema version.

Input ordering does not change the run ID. Changing a source file or effective policy does.

The batch manifest records:

- `run_id`;
- `portfolio_id`;
- the full effective policy;
- `policy_sha256`;
- source SHA-256 digests;
- normalized-output SHA-256 digests;
- target currency and requested rate date;
- rate-source policy and provider;
- source/output paths and supplier names.

Each normalized quotation written during a batch run also carries the `run_id` and `portfolio_id` in its normalization metadata, linking the quotation back to the manifest.

## Rate-source policy

FX data is retrieved through [Frankfurter](https://frankfurter.dev/).

- Without `--provider`, Frankfurter's blended provider set is used.
- With `--provider`, the named provider is pinned and recorded in provenance.
- Same-currency normalization avoids a network call and records `same_currency`.
- A batch containing different source-selection modes is summarized as `mixed` in the manifest.

Provider pinning is a control/reproducibility feature. The tool does not decide which authority is legally or commercially appropriate for a transaction.

## Contract versioning

Machine-readable contracts currently use `schema_version: "1.0"`.

- amount output: `currency-normalizer.amount`;
- quotation metadata: `currency-normalizer.normalization`;
- batch manifest: `currency-normalizer.manifest`;
- portfolio policy: `currency-normalizer.portfolio-policy`.

Schemas:

- [`schemas/normalized-quote.schema.json`](schemas/normalized-quote.schema.json)
- [`schemas/normalization-manifest.schema.json`](schemas/normalization-manifest.schema.json)
- [`schemas/portfolio-policy.schema.json`](schemas/portfolio-policy.schema.json)

## Pipeline role

```text
currency-normalizer ──> rfqdiff ────────────────┐
                                                 │
payment-terms-parser ───────────────────────────┼──> supplier-scorecard
                                                 │
vendor-risk-engine ─────────────────────────────┤
                                                 │
bidlint ──> technical compliance ───────────────┘
```

## Quality gates

GitHub Actions runs on Python 3.11, 3.12 and 3.13 for pushes to `main` and pull requests. CI checks out `rfqdiff` and executes the real handoff test, so downstream contract drift is detected early.

Local verification:

```bash
python -m unittest discover -s tests -v
```

The cross-repository integration test runs when `RFQDIFF_MAIN` points to an `rfqdiff/main.py` checkout.

## Engineering principles

- **Visible FX provenance** — conversion assumptions remain reviewable.
- **Deterministic money arithmetic** — money calculations use `Decimal` internally.
- **Historical reproducibility** — an explicit rate date can be replayed.
- **Provider reproducibility** — a named authority can be pinned when required.
- **Portfolio policy** — procurement normalization assumptions can be defined once and reused.
- **Content-addressed lineage** — source/output SHA-256 values expose file-level evidence.
- **Stable run identity** — equivalent inputs and policy produce the same batch run ID.
- **Versioned contracts** — downstream tools can identify the data contract explicitly.
- **Single responsibility** — normalization stays separate from scoring and compliance.

## Engineering procurement toolchain

| Tool | Role |
| --- | --- |
| **[`currency-normalizer`](https://github.com/yigitcan-ozturk/currency-normalizer)** | Normalize quotation currencies with explicit FX provenance |
| [`rfqdiff`](https://github.com/yigitcan-ozturk/rfqdiff) | Compare and score normalized quotations |
| [`payment-terms-parser`](https://github.com/yigitcan-ozturk/payment-terms-parser) | Convert payment terms into commercial-risk signals |
| [`vendor-risk-engine`](https://github.com/yigitcan-ozturk/vendor-risk-engine) | Score delivery, quality, commercial, compliance and dependency risk |
| [`bidlint`](https://github.com/yigitcan-ozturk/bidlint) | Produce evidence-backed technical-compliance findings |
| [`supplier-scorecard`](https://github.com/yigitcan-ozturk/supplier-scorecard) | Combine commercial, risk and technical signals into an explainable supplier decision |

## Status

`main` remains the release-ready **v0.3.0** line until its GitHub release is published.

The `feat/v0.4-reproducible-runs` development branch adds portfolio policies and reproducible/content-addressed batch lineage. It should not merge into `main` until the v0.3.0 release is published.

## License

MIT License. See [`LICENSE`](LICENSE).
