# currency-normalizer

**Auditable FX normalization for supplier quotations.**

[![Tests](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml)

`currency-normalizer` converts supplier quotation amounts into a common currency while preserving the original amount, currency, rate and rate date as explicit provenance. It is the FX normalization boundary of the engineering procurement toolchain.

## Why currency-normalizer

Supplier quotations often arrive in different currencies, which makes direct price comparison unreliable. The tool normalizes those amounts before commercial comparison and keeps conversion evidence visible rather than hiding FX assumptions inside downstream scoring.

The implementation uses `Decimal` arithmetic for money calculations and keeps the conversion logic small and transparent.

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

## Tests

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the suite automatically on supported Python versions.

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
