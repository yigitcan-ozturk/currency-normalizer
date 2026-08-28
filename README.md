# currency-normalizer

**Auditable FX normalization for supplier quotations.**

[![Tests](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`currency-normalizer` converts supplier quotation amounts into a common currency while preserving the original amount, currency, applied rate, rate date and rate-source policy as explicit provenance. It is the FX normalization boundary of the engineering procurement toolchain.

## Why currency-normalizer

Supplier quotations often arrive in different currencies, which makes direct price comparison unreliable. This tool normalizes those amounts before commercial scoring and keeps conversion evidence visible instead of hiding FX assumptions inside a downstream recommendation.

The implementation uses `Decimal` arithmetic for money calculations and deliberately keeps the conversion logic small and inspectable.

## Decision boundary

`currency-normalizer` is responsible for **FX normalization only**.

It does:

- convert supported currency amounts;
- fetch current or historical exchange rates for cross-currency conversion;
- use Frankfurter's blended provider set by default or pin a named provider;
- preserve original amount, currency, applied rate, rate date and source policy;
- normalize one or many quotation JSON files into the shape expected by `rfqdiff`;
- write a versioned normalization manifest for batch runs;
- return machine-readable JSON.

It intentionally does **not**:

- compare or rank suppliers;
- determine whether an exchange rate is commercially acceptable;
- provide treasury, accounting or hedging advice;
- determine technical compliance;
- hide the applied FX rate or rate-source policy from downstream reviewers.

## Features

- Convert currency amounts from the command line
- Fetch current exchange rates
- Request historical rates by date
- Pin a Frankfurter provider such as `ECB`, `BOE` or `TCMB`
- Use `Decimal` arithmetic for money calculations
- Return structured JSON with explicit schema versions
- Normalize a single quotation JSON file
- Batch-normalize multiple quotation JSON files
- Preserve exact decimal strings in normalization provenance
- Produce quotation files that can be passed directly to `rfqdiff`
- Produce a versioned batch normalization manifest
- Validate the `currency-normalizer → rfqdiff` handoff in CI
- Run with Python only — no third-party runtime dependencies

## Quick start

### Requirements

- Python 3.11+
- Internet access for cross-currency conversion

### Normalize one amount

```bash
python main.py 10000 USD EUR
```

Structured output:

```bash
python main.py 10000 USD EUR --json
```

### Use a historical rate

```bash
python main.py 10000 USD EUR --rate-date 2026-08-01 --json
```

### Pin a provider

Frankfurter blends available provider data by default. When a procurement or jurisdiction policy requires a named authority, pin the provider explicitly:

```bash
python main.py 10000 USD EUR \
  --rate-date 2026-08-01 \
  --provider ECB \
  --json
```

The output records whether the rate source was `blended`, `pinned` or `same_currency`, together with the provider key when one was pinned.

### Normalize one rfqdiff quotation

Given:

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

The output preserves the quotation fields expected by `rfqdiff`, changes `price` and `currency`, and adds a versioned `normalization` metadata block with original price, currency, exact normalized decimal value, rate, rate date and rate-source policy.

Then use normalized quotations directly:

```bash
python ../rfqdiff/main.py supplier_a_eur.json supplier_b_eur.json
```

### Batch-normalize supplier quotations

```bash
python main.py \
  --quotes supplier_a.json supplier_b.json supplier_c.json \
  --target-currency EUR \
  --rate-date 2026-08-01 \
  --provider ECB \
  --output-dir normalized
```

This writes one normalized quotation per input plus `normalized/normalization-manifest.json`.

The manifest records the schema version, tool version, target currency, requested historical date, source policy, source paths, output paths and supplier names so a procurement review can trace the batch operation.

## Contract versioning

Machine-readable outputs carry explicit schema identifiers and `schema_version: "1.0"`.

- amount output: `currency-normalizer.amount`
- quotation normalization metadata: `currency-normalizer.normalization`
- batch manifest: `currency-normalizer.manifest`

The normalized quotation contract is documented in [`schemas/normalized-quote.schema.json`](schemas/normalized-quote.schema.json), and the batch manifest contract is documented in [`schemas/normalization-manifest.schema.json`](schemas/normalization-manifest.schema.json).

The top-level normalized quotation remains compatible with `rfqdiff`: required commercial fields stay numeric/unchanged in shape, while normalization evidence lives in an additional metadata block.

## Rate-source policy

FX data is retrieved through [Frankfurter](https://frankfurter.dev/).

- Without `--provider`, Frankfurter's blended provider set is used.
- With `--provider`, the named provider key is passed to Frankfurter and recorded in provenance.
- For same-currency normalization, no network call is made and the source policy is recorded as `same_currency`.

Provider pinning is a reproducibility/control feature; this tool does not decide which authority is legally or commercially appropriate for a given transaction.

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

GitHub Actions runs on Python 3.11, 3.12 and 3.13 for pushes to `main` and pull requests. CI also checks out `rfqdiff` and executes an end-to-end handoff test so cross-tool contract drift is detected early.

Local unit verification:

```bash
python -m unittest discover -s tests -v
```

The cross-repository integration test runs when `RFQDIFF_MAIN` points to an `rfqdiff/main.py` checkout.

## Engineering principles

- **Visible FX provenance** — conversion evidence and source policy remain available.
- **Decimal money arithmetic** — monetary calculations avoid binary floating-point shortcuts internally.
- **Historical reproducibility** — comparisons can be rerun against an explicit rate date.
- **Provider reproducibility** — a named authority can be pinned when policy requires it.
- **Versioned contracts** — downstream tools can identify the normalization schema explicitly.
- **Single responsibility** — normalization stays separate from supplier scoring.
- **Machine-readable handoff** — normalized quotation data feeds directly into `rfqdiff`.
- **Batch auditability** — multi-supplier normalization creates an explicit manifest.

## Engineering procurement toolchain

| Tool | Role |
| --- | --- |
| **[`currency-normalizer`](https://github.com/yigitcan-ozturk/currency-normalizer)** | Normalize quotation currencies with explicit FX provenance |
| [`rfqdiff`](https://github.com/yigitcan-ozturk/rfqdiff) | Compare and score normalized quotations |
| [`payment-terms-parser`](https://github.com/yigitcan-ozturk/payment-terms-parser) | Convert payment terms into commercial-risk signals |
| [`vendor-risk-engine`](https://github.com/yigitcan-ozturk/vendor-risk-engine) | Score delivery, quality, commercial, compliance and dependency risk |
| [`bidlint`](https://github.com/yigitcan-ozturk/bidlint) | Produce evidence-backed technical-compliance findings |
| [`supplier-scorecard`](https://github.com/yigitcan-ozturk/supplier-scorecard) | Combine commercial, risk and technical signals into an explainable supplier decision |

## Roadmap

- Configurable base-currency policy for procurement portfolios
- Portfolio-level run identifiers and stronger manifest lineage
- Contract validation across additional downstream procurement tools
- Provider-policy presets for common procurement contexts

## Status

Development line: **v0.3.0**.

This line includes historical-rate selection, batch normalization, manifests, provider pinning/source provenance, schema-versioned contracts and a real `rfqdiff` integration gate.

The repository's latest published GitHub release may lag the development version until the corresponding release tag is published.

## License

MIT License. See [`LICENSE`](LICENSE).
