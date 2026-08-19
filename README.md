# currency-normalizer

A lightweight command-line tool for converting currency amounts using current exchange rates.

Built as a small procurement utility for normalizing supplier quotations that arrive in different currencies.

## Features

- Convert currency amounts from the command line
- Fetch current exchange rates
- Use Decimal arithmetic for money calculations
- Round results to two decimal places
- Handle API and connection errors
- No third-party Python packages required

## Usage

```bash
python main.py 10000 USD EUR