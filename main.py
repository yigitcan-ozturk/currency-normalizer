import argparse
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


VERSION = "0.3.0"
SCHEMA_VERSION = "1.0"
RATE_SERVICE = "Frankfurter"
RATE_SERVICE_URL = "https://frankfurter.dev"

AMOUNT_SCHEMA = "currency-normalizer.amount"
NORMALIZATION_SCHEMA = "currency-normalizer.normalization"
MANIFEST_SCHEMA = "currency-normalizer.manifest"

QUOTE_REQUIRED_FIELDS = (
    "name",
    "currency",
    "price",
    "lead_time_weeks",
    "payment_days",
)


def validate_rate_date(value):
    if value is None:
        return None

    value = str(value)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("rate date must use YYYY-MM-DD format") from exc

    return value


def validate_provider(value):
    if value is None:
        return None

    provider = str(value).strip().upper()
    if not provider:
        raise ValueError("provider cannot be empty")
    if not all(character.isalnum() or character in "_-" for character in provider):
        raise ValueError("provider must use letters, numbers, '-' or '_'")
    return provider


def build_rate_source(base, quote, provider=None):
    base = str(base).upper()
    quote = str(quote).upper()
    provider = validate_provider(provider)

    if base == quote:
        selection = "same_currency"
        provider = None
    elif provider:
        selection = "pinned"
    else:
        selection = "blended"

    return {
        "service": RATE_SERVICE,
        "service_url": RATE_SERVICE_URL,
        "selection": selection,
        "provider": provider,
    }


def get_rate(base, quote, requested_date=None, provider=None):
    base = str(base).upper()
    quote = str(quote).upper()
    requested_date = validate_rate_date(requested_date)
    provider = validate_provider(provider)

    if base == quote:
        return Decimal("1"), requested_date or "same currency"

    params = {}
    if requested_date:
        params["date"] = requested_date
    if provider:
        params["providers"] = provider

    url = f"https://api.frankfurter.dev/v2/rate/{base}/{quote}"
    if params:
        url += "?" + urlencode(params)

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


def normalize_amount(amount, base, quote, rate_date=None, provider=None):
    amount = Decimal(str(amount))
    base = str(base).upper()
    quote = str(quote).upper()
    provider = validate_provider(provider)

    rate, applied_rate_date = get_rate(
        base,
        quote,
        rate_date,
        provider=provider,
    )

    converted = (amount * rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return {
        "schema": AMOUNT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "tool": "currency-normalizer",
        "version": VERSION,
        "original_amount": str(amount),
        "from_currency": base,
        "to_currency": quote,
        "rate": str(rate),
        "converted_amount": str(converted),
        "rate_date": applied_rate_date,
        "rate_source": build_rate_source(base, quote, provider),
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


def normalize_quote(quote, target_currency, rate_date=None, provider=None):
    target_currency = str(target_currency).upper()
    source_currency = str(quote["currency"]).upper()

    result = normalize_amount(
        quote["price"],
        source_currency,
        target_currency,
        rate_date=rate_date,
        provider=provider,
    )

    normalized = dict(quote)
    normalized["currency"] = target_currency
    normalized["price"] = float(Decimal(result["converted_amount"]))
    normalized["normalization"] = {
        "schema": NORMALIZATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "tool": result["tool"],
        "version": result["version"],
        "original_price": result["original_amount"],
        "original_currency": source_currency,
        "target_currency": target_currency,
        "rate": result["rate"],
        "rate_date": result["rate_date"],
        "normalized_price": result["converted_amount"],
        "rate_source": result["rate_source"],
    }

    return normalized


def normalize_quote_files(paths, target_currency, rate_date=None, provider=None):
    normalized = []

    for path in paths:
        quote_path = Path(path)
        quote = load_quote(quote_path)
        normalized.append(
            {
                "source": str(quote_path),
                "quote": normalize_quote(
                    quote,
                    target_currency,
                    rate_date=rate_date,
                    provider=provider,
                ),
            }
        )

    return normalized


def write_batch_outputs(
    items,
    output_dir,
    target_currency,
    rate_date=None,
    provider=None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for item in items:
        source = Path(item["source"])
        destination = output_dir / (
            f"{source.stem}_{str(target_currency).lower()}.json"
        )
        write_json(item["quote"], destination)
        files.append(
            {
                "source": item["source"],
                "output": str(destination),
                "supplier": item["quote"]["name"],
            }
        )

    provider = validate_provider(provider)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "tool": "currency-normalizer",
        "version": VERSION,
        "target_currency": str(target_currency).upper(),
        "requested_rate_date": validate_rate_date(rate_date),
        "rate_source": {
            "service": RATE_SERVICE,
            "service_url": RATE_SERVICE_URL,
            "selection": "pinned" if provider else "blended",
            "provider": provider,
        },
        "files": files,
    }
    write_json(manifest, output_dir / "normalization-manifest.json")

    return manifest


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
    source = result["rate_source"]
    provider = source["provider"] or source["selection"]
    print(f"Rate source: {source['service']} ({provider})")


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Normalize currency amounts or quotation JSON files "
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
        help="Normalize one rfqdiff quotation JSON file.",
    )
    parser.add_argument(
        "--quotes",
        nargs="+",
        help="Normalize multiple rfqdiff quotation JSON files.",
    )
    parser.add_argument(
        "--target-currency",
        help="Target currency for quotation modes.",
    )
    parser.add_argument(
        "--rate-date",
        help="Use a historical FX rate date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--provider",
        help=(
            "Pin a Frankfurter provider key such as ECB, BOE or TCMB. "
            "Omit to use Frankfurter's blended provider set."
        ),
    )
    parser.add_argument(
        "--output-dir",
        help="Write batch-normalized quotation files and a manifest here.",
    )

    return parser


def validate_cli_mode(parser, args):
    try:
        validate_rate_date(args.rate_date)
        validate_provider(args.provider)
    except ValueError as exc:
        parser.error(str(exc))

    if args.quote_path and args.quotes:
        parser.error("--quote and --quotes cannot be used together.")

    quotation_mode = bool(args.quote_path or args.quotes)

    if quotation_mode:
        if any(
            value is not None
            for value in (args.amount, args.from_currency, args.to_currency)
        ):
            parser.error(
                "quotation mode cannot be combined with amount/from/to positionals."
            )
        if not args.target_currency:
            parser.error("quotation mode requires --target-currency.")
        if args.quotes and args.output:
            parser.error("batch --quotes mode uses --output-dir, not --output.")
        if args.quote_path and args.output_dir:
            parser.error("--output-dir is only valid with --quotes.")
        return

    if args.target_currency:
        parser.error("--target-currency is only valid with --quote or --quotes.")

    if args.output_dir:
        parser.error("--output-dir is only valid with --quotes.")

    if args.amount is None or not args.from_currency or not args.to_currency:
        parser.error(
            "amount mode requires: amount, from_currency and to_currency."
        )


def main():
    parser = build_parser()
    args = parser.parse_args()
    validate_cli_mode(parser, args)

    try:
        if args.quotes:
            items = normalize_quote_files(
                args.quotes,
                args.target_currency,
                rate_date=args.rate_date,
                provider=args.provider,
            )

            if args.output_dir:
                manifest = write_batch_outputs(
                    items,
                    args.output_dir,
                    args.target_currency,
                    rate_date=args.rate_date,
                    provider=args.provider,
                )
                print(json.dumps(manifest, indent=2, ensure_ascii=False))
            else:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            return

        if args.quote_path:
            quote = load_quote(args.quote_path)
            payload = normalize_quote(
                quote,
                args.target_currency,
                rate_date=args.rate_date,
                provider=args.provider,
            )

            if args.output:
                write_json(payload, args.output)
            else:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        payload = normalize_amount(
            args.amount,
            args.from_currency,
            args.to_currency,
            rate_date=args.rate_date,
            provider=args.provider,
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
