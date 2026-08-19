# currency-normalizer

A lightweight Python CLI for normalizing supplier quotation amounts across currencies.

[![Tests](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/yigitcan-ozturk/currency-normalizer/actions/workflows/tests.yml)

## Why currency-normalizer

Supplier quotations often arrive in different currencies, which makes direct price comparison unreliable. `currency-normalizer` converts an amount from one currency to another using a current exchange rate so quotations can be compared on a common basis.

The tool uses `Decimal` arithmetic for money calculations and keeps the conversion logic small and transparent.

## Features

- Convert currency amounts from the command line
- Fetch current exchange rates
- Use `Decimal` arithmetic for money calculations
- Round converted values to two decimal places
- Handle API and connection errors
- Return a 1:1 rate for same-currency comparisons
- Run with Python only — no third-party runtime dependencies

## Quick start

### Requirements

- Python 3.11+
- Internet access for cross-currency conversion

### Run

```bash
python main.py 10000 USD EUR
```

Example output format:

```text
CURRENCY NORMALIZER v0.1
----------------------------------------
Original  : 10,000.00 USD
Rate      : 1 USD = <rate> EUR
Converted : <amount> EUR
Rate date : <date>
```

For identical currencies, no external exchange-rate request is needed:

```bash
python main.py 10000 EUR EUR
```

## How it works

1. Normalize currency codes to uppercase.
2. Fetch the requested exchange rate when the currencies differ.
3. Multiply the source amount by the rate using `Decimal` arithmetic.
4. Round the converted amount to two decimal places using `ROUND_HALF_UP`.
5. Print the rate and rate date alongside the converted value.

Exchange-rate data is requested from the Frankfurter API.

## Tests

Run the test suite locally with:

```bash
python -m unittest discover -s tests -v
```

The tests mock network responses, so CI does not depend on a live exchange-rate service. GitHub Actions runs the suite automatically on supported Python versions.

## Procurement tooling suite

`currency-normalizer` is part of a small set of transparent Python tools for supplier and procurement decision support:

| Tool | Role |
| --- | --- |
| [`rfqdiff`](https://github.com/yigitcan-ozturk/rfqdiff) | Compare and score supplier quotations |
| **[`currency-normalizer`](https://github.com/yigitcan-ozturk/currency-normalizer)** | Normalize quotation values across currencies |
| [`payment-terms-parser`](https://github.com/yigitcan-ozturk/payment-terms-parser) | Convert payment terms into commercial-risk signals |
| [`vendor-risk-engine`](https://github.com/yigitcan-ozturk/vendor-risk-engine) | Score operational, commercial, compliance and dependency risk |

A typical decision flow is:

```text
currency-normalizer -> payment-terms-parser -> rfqdiff -> vendor-risk-engine
```

Each tool can run independently. The suite roadmap is to combine their outputs into a composite supplier scorecard.

## Roadmap

- Batch quotation normalization
- Configurable base currency
- Historical rate support
- Structured JSON output
- Integration with `rfqdiff`
- Composite supplier scorecard integration

## Status

Early-stage project, currently at **v0.1**. The core single-amount conversion workflow is functional.

## License

MIT License. See [`LICENSE`](LICENSE).
