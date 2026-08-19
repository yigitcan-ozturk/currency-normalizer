import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import MagicMock, patch

from main import get_rate, load_quote, normalize_amount, normalize_quote


class CurrencyNormalizerTests(unittest.TestCase):
    def test_same_currency_returns_one_without_network_call(self):
        with patch("main.urlopen") as mocked_urlopen:
            rate, rate_date = get_rate("EUR", "EUR")

        self.assertEqual(rate, Decimal("1"))
        self.assertEqual(rate_date, "same currency")
        mocked_urlopen.assert_not_called()

    def test_rate_response_is_parsed_as_decimal(self):
        response = MagicMock()
        response.read.return_value = b'{"rate": 0.92, "date": "2026-08-19"}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch("main.urlopen", return_value=response):
            rate, rate_date = get_rate("USD", "EUR")

        self.assertEqual(rate, Decimal("0.92"))
        self.assertEqual(rate_date, "2026-08-19")

    def test_http_error_becomes_clear_system_exit(self):
        error = HTTPError(
            url="https://example.test",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )

        with patch("main.urlopen", side_effect=error):
            with self.assertRaisesRegex(SystemExit, "API error: HTTP 429"):
                get_rate("USD", "EUR")

    def test_connection_error_becomes_clear_system_exit(self):
        with patch("main.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(SystemExit, "Connection error: offline"):
                get_rate("USD", "EUR")

    def test_normalize_amount_returns_json_safe_contract(self):
        with patch(
            "main.get_rate",
            return_value=(Decimal("0.92"), "2026-08-19"),
        ):
            result = normalize_amount(Decimal("100"), "usd", "eur")

        self.assertEqual(result["tool"], "currency-normalizer")
        self.assertEqual(result["version"], "0.2")
        self.assertEqual(result["from_currency"], "USD")
        self.assertEqual(result["to_currency"], "EUR")
        self.assertEqual(result["converted_amount"], "92.00")
        json.dumps(result)

    def test_normalize_quote_produces_rfqdiff_ready_quote(self):
        quote = {
            "name": "Supplier USD",
            "currency": "USD",
            "price": 100,
            "lead_time_weeks": 6,
            "payment_days": 30,
        }

        with patch(
            "main.get_rate",
            return_value=(Decimal("0.92"), "2026-08-19"),
        ):
            normalized = normalize_quote(quote, "EUR")

        self.assertEqual(normalized["currency"], "EUR")
        self.assertEqual(normalized["price"], 92.0)
        self.assertEqual(normalized["lead_time_weeks"], 6)
        self.assertEqual(normalized["payment_days"], 30)
        self.assertEqual(
            normalized["normalization"]["original_currency"],
            "USD",
        )

    def test_load_quote_rejects_missing_field(self):
        quote = {
            "name": "Supplier A",
            "currency": "EUR",
            "price": 100,
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quote.json"
            path.write_text(json.dumps(quote), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "lead_time_weeks"):
                load_quote(path)


if __name__ == "__main__":
    unittest.main()
