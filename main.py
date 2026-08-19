import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def get_rate(base, quote):
    if base == quote:
        return Decimal("1"), "same currency"

    url = f"https://api.frankfurter.dev/v2/rate/{base}/{quote}"

    request = Request(
        url,
        headers={
            "User-Agent": "currency-normalizer/0.1",
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


def main():
    parser = argparse.ArgumentParser(
        description="Normalize currency amounts using current exchange rates."
    )

    parser.add_argument("amount", type=Decimal)
    parser.add_argument("from_currency")
    parser.add_argument("to_currency")

    args = parser.parse_args()

    base = args.from_currency.upper()
    quote = args.to_currency.upper()

    rate, rate_date = get_rate(base, quote)

    converted = (args.amount * rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    print()
    print("CURRENCY NORMALIZER v0.1")
    print("-" * 40)
    print(f"Original  : {args.amount:,.2f} {base}")
    print(f"Rate      : 1 {base} = {rate} {quote}")
    print(f"Converted : {converted:,.2f} {quote}")
    print(f"Rate date : {rate_date}")


if __name__ == "__main__":
    main()
    