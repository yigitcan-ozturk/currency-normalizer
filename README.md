# currency-normalizer

A lightweight Python CLI for normalizing supplier quotation amounts across currencies.

[![Tests](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml)

## Why currency-normalizer

Supplier quotations often arrive in different currencies, which makes direct price comparison unreliable. `currency-normalizer` converts amounts into a common currency and can also rewrite a quotation JSON file into an `rfqdiff`-ready normalized quote.

The tool uses `Decimal` arithmetic for money calculations and keeps the conversion logic small and transparent.

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

`currency-normalizer` is the normalization input to the quotation-comparison branch:

```text
currency-normalizer ──> rfqdiff ───────────────┐
                                               │
payment-terms-parser ──────────────────────────┼─> supplier-scorecard
                                               │
vendor-risk-engine ────────────────────────────┘
```

## Tests

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the suite automatically on supported Python versions.

## Procurement tooling suite

| Tool | Role |
| --- | --- |
| **[`currency-normalizer`](https://github.com/yigitcan-ozturk/currency-normalizer)** | Normalize quotation values across currencies |
| [`rfqdiff`](https://github.com/yigitcan-ozturk/rfqdiff) | Compare and score normalized quotations |
| [`payment-terms-parser`](https://github.com/yigitcan-ozturk/payment-terms-parser) | Convert payment terms into commercial-risk signals |
| [`vendor-risk-engine`](https://github.com/yigitcan-ozturk/vendor-risk-engine) | Score operational, quality, compliance and dependency risk |
| [`supplier-scorecard`](https://github.com/yigitcan-ozturk/supplier-scorecard) | Combine upstream signals into one supplier recommendation |

## Roadmap

- Batch quotation normalization
- Configurable base currency
- Historical-rate support
- Portfolio normalization manifests
- More explicit provenance/version contracts

## Status

Early-stage project, currently at **v0.2**. This version adds structured JSON output and quotation-file normalization so the result can feed directly into `rfqdiff`.

## License

MIT License. See [`LICENSE`](LICENSE).
