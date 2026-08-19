import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VERSION = "0.2"

QUOTE_REQUIRED_FIELDS = (
    "name",
    "currency",
    "price",
    "lead_time_weeks",
    "payment_days",
)


def get_rate(base, quote):
    base = str(base).upper()
    quote = str(quote).upper()

    if base == quote:
        return Decimal("1"), "same currency"

    url = f"https://api.frankfurter.dev/v2/rate/{base}/{quote}"

    request = Request(
        url,
        headers={
            "User-Agent": f"currency-normalizer/{VERSION}",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(
                response.read().decode("utf-8"),
                parse_float=Decimal,
            )

    except HTTPError as error:
        raise SystemExit(
            f"API error: HTTP {error.code}"
        ) from error

    except URLError as error:
        raise SystemExit(
            f"Connection error: {error.reason}"
        ) from error

    return data["rate"], data["date"]


def normalize_amount(amount, base, quote):
    amount = Decimal(str(amount))
    base = str(base).upper()
    quote = str(quote).upper()

    rate, rate_date = get_rate(base, quote)

    converted = (amount * rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return {
        "tool": "currency-normalizer",
        "version": VERSION,
        "original_amount": str(amount),
        "from_currency": base,
        "to_currency": quote,
        "rate": str(rate),
        "converted_amount": str(converted),
        "rate_date": rate_date,
    }


def load_quote(path):
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        quote = json.load(handle)

    missing = [name for name in QUOTE_REQUIRED_FIELDS if name not in quote]
    if missing:
        raise ValueError(
            "quotation is missing required field(s): " + ", ".join(missing)
        )

    return quote


def normalize_quote(quote, target_currency):
    target_currency = str(target_currency).upper()
    source_currency = str(quote["currency"]).upper()

    result = normalize_amount(
        quote["price"],
        source_currency,
        target_currency,
    )

    normalized = dict(quote)
    normalized["currency"] = target_currency
    normalized["price"] = float(Decimal(result["converted_amount"]))
    normalized["normalization"] = {
        "tool": result["tool"],
        "version": result["version"],
        "original_price": float(Decimal(result["original_amount"])),
        "original_currency": source_currency,
        "target_currency": target_currency,
        "rate": result["rate"],
        "rate_date": result["rate_date"],
    }

    return normalized


def write_json(payload, path):
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def print_report(result):
    original = Decimal(result["original_amount"])
    converted = Decimal(result["converted_amount"])

    print()
    print(f"CURRENCY NORMALIZER v{VERSION}")
    print("-" * 40)
    print(f"Original  : {original:,.2f} {result['from_currency']}")
    print(
        f"Rate      : 1 {result['from_currency']} = "
        f"{result['rate']} {result['to_currency']}"
    )
    print(f"Converted : {converted:,.2f} {result['to_currency']}")
    print(f"Rate date : {result['rate_date']}")


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Normalize currency amounts or convert a quotation JSON file "
            "into an rfqdiff-ready target currency."
        )
    )

    parser.add_argument("amount", nargs="?", type=Decimal)
    parser.add_argument("from_currency", nargs="?")
    parser.add_argument("to_currency", nargs="?")

    parser.add_argument(
        "--json",
        action="store_true",
        help="Return structured JSON in amount mode.",
    )
    parser.add_argument(
        "--output",
        help="Write JSON output to a file.",
    )
    parser.add_argument(
        "--quote",
        dest="quote_path",
        help="Normalize the price inside an rfqdiff quotation JSON file.",
    )
    parser.add_argument(
        "--target-currency",
        help="Target currency for --quote mode.",
    )

    return parser


def validate_cli_mode(parser, args):
    if args.quote_path:
        if any(
            value is not None
            for value in (args.amount, args.from_currency, args.to_currency)
        ):
            parser.error(
                "--quote mode cannot be combined with amount/from/to positionals."
            )
        if not args.target_currency:
            parser.error("--quote mode requires --target-currency.")
        return

    if args.target_currency:
        parser.error("--target-currency is only valid with --quote.")

    if args.amount is None or not args.from_currency or not args.to_currency:
        parser.error(
            "amount mode requires: amount, from_currency and to_currency."
        )


def main():
    parser = build_parser()
    args = parser.parse_args()
    validate_cli_mode(parser, args)

    try:
        if args.quote_path:
            quote = load_quote(args.quote_path)
            payload = normalize_quote(quote, args.target_currency)

            if args.output:
                write_json(payload, args.output)
            else:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        payload = normalize_amount(
            args.amount,
            args.from_currency,
            args.to_currency,
        )

        if args.output:
            write_json(payload, args.output)

        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print_report(payload)

    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
