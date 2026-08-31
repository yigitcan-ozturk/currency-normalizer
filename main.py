import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


VERSION = "0.5.0-dev"
SCHEMA_VERSION = "1.0"
RATE_SERVICE = "Frankfurter"
RATE_SERVICE_URL = "https://frankfurter.dev"

AMOUNT_SCHEMA = "currency-normalizer.amount"
NORMALIZATION_SCHEMA = "currency-normalizer.normalization"
MANIFEST_SCHEMA = "currency-normalizer.manifest"
POLICY_SCHEMA = "currency-normalizer.portfolio-policy"

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


def validate_currency(value, field_name="currency"):
    currency = str(value).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError(f"{field_name} must use a 3-letter currency code")
    return currency


def validate_portfolio_id(value):
    if value is None:
        return None

    portfolio_id = str(value).strip()
    if not portfolio_id:
        raise ValueError("portfolio_id cannot be empty")
    if len(portfolio_id) > 120:
        raise ValueError("portfolio_id cannot exceed 120 characters")
    if not all(
        character.isalnum() or character in "-_.:/"
        for character in portfolio_id
    ):
        raise ValueError(
            "portfolio_id must use letters, numbers, '-', '_', '.', ':', or '/'"
        )
    return portfolio_id


def canonical_sha256(payload):
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_effective_policy(
    base_currency,
    rate_date=None,
    provider=None,
    portfolio_id=None,
):
    return {
        "schema": POLICY_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "base_currency": validate_currency(base_currency, "base_currency"),
        "rate_date": validate_rate_date(rate_date),
        "provider": validate_provider(provider),
        "portfolio_id": validate_portfolio_id(portfolio_id),
    }


def validate_policy_document(policy):
    if not isinstance(policy, dict):
        raise ValueError("portfolio policy must be a JSON object")

    required = {"schema", "schema_version", "base_currency"}
    missing = sorted(required - set(policy))
    if missing:
        raise ValueError(
            "portfolio policy is missing required field(s): " + ", ".join(missing)
        )

    allowed = {
        "schema",
        "schema_version",
        "base_currency",
        "rate_date",
        "provider",
        "portfolio_id",
    }
    unknown = sorted(set(policy) - allowed)
    if unknown:
        raise ValueError(
            "portfolio policy contains unsupported field(s): " + ", ".join(unknown)
        )

    if policy["schema"] != POLICY_SCHEMA:
        raise ValueError(f"portfolio policy schema must be {POLICY_SCHEMA}")
    if str(policy["schema_version"]) != SCHEMA_VERSION:
        raise ValueError(
            f"portfolio policy schema_version must be {SCHEMA_VERSION}"
        )

    return build_effective_policy(
        policy["base_currency"],
        rate_date=policy.get("rate_date"),
        provider=policy.get("provider"),
        portfolio_id=policy.get("portfolio_id"),
    )


def load_portfolio_policy(path):
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        policy = json.load(handle)
    return validate_policy_document(policy)


def resolve_portfolio_policy(
    policy=None,
    target_currency=None,
    rate_date=None,
    provider=None,
    portfolio_id=None,
):
    policy = policy or {}
    base_currency = target_currency or policy.get("base_currency")
    if not base_currency:
        raise ValueError(
            "batch normalization requires --target-currency "
            "or base_currency in --policy"
        )

    effective_rate_date = (
        rate_date if rate_date is not None else policy.get("rate_date")
    )
    effective_provider = (
        provider if provider is not None else policy.get("provider")
    )
    effective_portfolio_id = (
        portfolio_id
        if portfolio_id is not None
        else policy.get("portfolio_id")
    )

    return build_effective_policy(
        base_currency,
        rate_date=effective_rate_date,
        provider=effective_provider,
        portfolio_id=effective_portfolio_id,
    )


def policy_sha256(policy):
    return canonical_sha256(policy)


def source_fingerprints(paths):
    fingerprints = []
    for path in paths:
        source = Path(path)
        fingerprints.append(
            {
                "name": source.name,
                "sha256": sha256_file(source),
            }
        )
    return sorted(
        fingerprints,
        key=lambda item: (item["name"], item["sha256"]),
    )


def build_run_id(paths, policy):
    identity = {
        "schema": "currency-normalizer.run-identity",
        "schema_version": SCHEMA_VERSION,
        "policy_sha256": policy_sha256(policy),
        "sources": source_fingerprints(paths),
    }
    return "cn-" + canonical_sha256(identity)[:20]


def annotate_batch_items(items, run_id, portfolio_id=None):
    portfolio_id = validate_portfolio_id(portfolio_id)
    for item in items:
        metadata = item["quote"]["normalization"]
        metadata["run_id"] = run_id
        metadata["portfolio_id"] = portfolio_id
    return items


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
    base = validate_currency(base, "base currency")
    quote = validate_currency(quote, "quote currency")
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


def normalize_amount(amount, base, quote, rate_date=None, provider=None, rate_cache=None):
    amount = Decimal(str(amount))
    base = validate_currency(base, "from_currency")
    quote = validate_currency(quote, "to_currency")
    provider = validate_provider(provider)
    rate_date = validate_rate_date(rate_date)
    cache_key = (base, quote, rate_date, provider)

    if rate_cache is not None and cache_key in rate_cache:
        rate, applied_rate_date = rate_cache[cache_key]
    else:
        rate, applied_rate_date = get_rate(
            base,
            quote,
            rate_date,
            provider=provider,
        )
        if rate_cache is not None:
            rate_cache[cache_key] = (rate, applied_rate_date)

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

    quote["currency"] = validate_currency(
        quote["currency"],
        "quotation currency",
    )
    return quote


def normalize_quote(quote, target_currency, rate_date=None, provider=None, rate_cache=None):
    target_currency = validate_currency(
        target_currency,
        "target_currency",
    )
    source_currency = validate_currency(
        quote["currency"],
        "quotation currency",
    )

    result = normalize_amount(
        quote["price"],
        source_currency,
        target_currency,
        rate_date=rate_date,
        provider=provider,
        rate_cache=rate_cache,
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


def normalize_quote_files(paths, target_currency, rate_date=None, provider=None, rate_cache=None):
    normalized = []
    rate_cache = {} if rate_cache is None else rate_cache

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
                    rate_cache=rate_cache,
                ),
            }
        )

    return normalized


def summarize_rate_source(items):
    sources = [
        item["quote"]["normalization"]["rate_source"]
        for item in items
    ]
    first = sources[0]
    if all(source == first for source in sources[1:]):
        return dict(first)

    return {
        "service": RATE_SERVICE,
        "service_url": RATE_SERVICE_URL,
        "selection": "mixed",
        "provider": None,
    }


def plan_batch_output_paths(items, output_dir, target_currency):
    output_dir = Path(output_dir)
    target_currency = validate_currency(target_currency, "target_currency")
    seen = {}
    destinations = []

    for item in items:
        source = Path(item["source"])
        filename = f"{source.stem}_{target_currency.lower()}.json"
        key = filename.casefold()
        entry = seen.setdefault(
            key,
            {"filename": filename, "sources": []},
        )
        entry["sources"].append(str(source))
        destinations.append(output_dir / filename)

    collisions = [
        entry for entry in seen.values() if len(entry["sources"]) > 1
    ]
    if collisions:
        details = "; ".join(
            f"{entry['filename']}: {', '.join(entry['sources'])}"
            for entry in sorted(
                collisions,
                key=lambda entry: entry["filename"].casefold(),
            )
        )
        raise ValueError(f"batch output filename collision(s): {details}")

    return destinations


def write_batch_outputs(
    items,
    output_dir,
    target_currency,
    rate_date=None,
    provider=None,
    portfolio_id=None,
    policy=None,
):
    output_dir = Path(output_dir)

    effective_policy = policy or build_effective_policy(
        target_currency,
        rate_date=rate_date,
        provider=provider,
        portfolio_id=portfolio_id,
    )
    effective_policy = validate_policy_document(effective_policy)
    destinations = plan_batch_output_paths(
        items,
        output_dir,
        effective_policy["base_currency"],
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = [item["source"] for item in items]
    run_id = build_run_id(sources, effective_policy)
    annotate_batch_items(
        items,
        run_id,
        portfolio_id=effective_policy["portfolio_id"],
    )

    files = []
    for index, item in enumerate(items):
        source = Path(item["source"])
        destination = destinations[index]
        source_digest = sha256_file(source)
        write_json(item["quote"], destination)
        output_digest = sha256_file(destination)
        files.append(
            {
                "source": item["source"],
                "source_sha256": source_digest,
                "output": str(destination),
                "output_sha256": output_digest,
                "supplier": item["quote"]["name"],
            }
        )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "tool": "currency-normalizer",
        "version": VERSION,
        "run_id": run_id,
        "portfolio_id": effective_policy["portfolio_id"],
        "policy": effective_policy,
        "policy_sha256": policy_sha256(effective_policy),
        "target_currency": effective_policy["base_currency"],
        "requested_rate_date": effective_policy["rate_date"],
        "rate_source": summarize_rate_source(items),
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
        "--policy",
        help=(
            "Load a portfolio normalization policy JSON file in batch mode. "
            "CLI target/date/provider/portfolio values override policy values."
        ),
    )
    parser.add_argument(
        "--portfolio-id",
        help="Optional portfolio identifier recorded in batch provenance.",
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
        validate_portfolio_id(args.portfolio_id)
        if args.target_currency:
            validate_currency(args.target_currency, "target_currency")
    except ValueError as exc:
        parser.error(str(exc))

    if args.quote_path and args.quotes:
        parser.error("--quote and --quotes cannot be used together.")

    quotation_mode = bool(args.quote_path or args.quotes)

    if args.policy and not args.quotes:
        parser.error("--policy is only valid with --quotes.")
    if args.portfolio_id and not args.quotes:
        parser.error("--portfolio-id is only valid with --quotes.")

    if quotation_mode:
        if any(
            value is not None
            for value in (args.amount, args.from_currency, args.to_currency)
        ):
            parser.error(
                "quotation mode cannot be combined with amount/from/to positionals."
            )
        if args.quote_path and not args.target_currency:
            parser.error("--quote mode requires --target-currency.")
        if args.quotes and not (args.target_currency or args.policy):
            parser.error(
                "batch quotation mode requires --target-currency or --policy."
            )
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
            policy_document = (
                load_portfolio_policy(args.policy)
                if args.policy
                else None
            )
            effective_policy = resolve_portfolio_policy(
                policy_document,
                target_currency=args.target_currency,
                rate_date=args.rate_date,
                provider=args.provider,
                portfolio_id=args.portfolio_id,
            )

            items = normalize_quote_files(
                args.quotes,
                effective_policy["base_currency"],
                rate_date=effective_policy["rate_date"],
                provider=effective_policy["provider"],
            )

            if args.output_dir:
                manifest = write_batch_outputs(
                    items,
                    args.output_dir,
                    effective_policy["base_currency"],
                    policy=effective_policy,
                )
                print(json.dumps(manifest, indent=2, ensure_ascii=False))
            else:
                run_id = build_run_id(args.quotes, effective_policy)
                annotate_batch_items(
                    items,
                    run_id,
                    portfolio_id=effective_policy["portfolio_id"],
                )
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
