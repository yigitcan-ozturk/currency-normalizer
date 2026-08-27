# currency-normalizer

**Auditable FX normalization for supplier quotations.**

[![Tests](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`currency-normalizer` converts supplier quotation amounts into a common currency while preserving the original amount, currency, rate and rate date as explicit provenance. It is the FX normalization boundary of the engineering procurement toolchain.

## Why currency-normalizer

Supplier quotations often arrive in different currencies, which makes direct price comparison unreliable. This tool normalizes those amounts before commercial scoring and keeps the conversion evidence visible instead of hiding FX assumptions inside a downstream recommendation.

The implementation uses `Decimal` arithmetic for money calculations and deliberately keeps the conversion logic small and inspectable.

## Decision boundary

`currency-normalizer` is responsible for **FX normalization only**.

It does:

- convert supported currency amounts;
- fetch a current exchange rate for cross-currency conversion;
- preserve original amount, currency, applied rate and rate date;
- normalize quotation JSON into the shape expected by `rfqdiff`;
- return machine-readable JSON.

It intentionally does **not**:

- compare or rank suppliers;
- determine whether an exchange rate is commercially acceptable;
- provide treasury, accounting or hedging advice;
- determine technical compliance;
- hide the applied FX rate from downstream reviewers.

## Features

- Convert currency amounts from the command line
- Fetch current exchange rates
- Use `Decimal` arithmetic for money calculations
- Return structured JSON
- Normalize an entire quotation JSON file
- Preserve original currency/rate metadata
- Produce quotation files that can be passed directly to `rfqdiff`
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

Or write it to a file:

```bash
python main.py 10000 USD EUR --output fx.json
```

### Normalize an rfqdiff quotation

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
  --output supplier_b_eur.json
```

The output preserves the quotation fields expected by `rfqdiff`, changes `price` and `currency`, and adds a `normalization` metadata block with the original price, currency, rate and rate date.

Then use the normalized quote directly:

```bash
python ../rfqdiff/main.py supplier_a_eur.json supplier_b_eur.json
```

## Pipeline role

`currency-normalizer` is the normalization input to the commercial quotation branch. Technical compliance remains independently owned by `bidlint`.

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

GitHub Actions runs the unit-test suite on Python 3.11, 3.12 and 3.13 for pushes to `main` and pull requests.

Local verification:

```bash
python -m unittest discover -s tests -v
```

## Engineering principles

- **Visible FX provenance** — the original value and applied conversion evidence remain available.
- **Decimal money arithmetic** — monetary calculations avoid binary floating-point shortcuts.
- **Single responsibility** — normalization stays separate from supplier scoring.
- **Machine-readable handoff** — normalized quotation data can feed directly into `rfqdiff`.
- **Reviewable assumptions** — the applied FX rate is evidence, not hidden state.

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

- Batch quotation normalization
- Configurable base currency
- Historical-rate support
- Portfolio normalization manifests
- More explicit provenance/version contracts

## Status

Early-stage project, currently at **v0.2**. This version provides structured JSON output and quotation-file normalization so the result can feed directly into `rfqdiff`.

## License

MIT License. See [`LICENSE`](LICENSE).
