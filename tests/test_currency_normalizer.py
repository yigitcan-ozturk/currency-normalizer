import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import MagicMock, patch

from main import (
    AMOUNT_SCHEMA,
    MANIFEST_SCHEMA,
    NORMALIZATION_SCHEMA,
    SCHEMA_VERSION,
    build_rate_source,
    get_rate,
    load_quote,
    normalize_amount,
    normalize_quote,
    normalize_quote_files,
    validate_provider,
    validate_rate_date,
    write_batch_outputs,
)


class CurrencyNormalizerTests(unittest.TestCase):
    def test_same_currency_returns_one_without_network_call(self):
        with patch("main.urlopen") as mocked_urlopen:
            rate, rate_date = get_rate("EUR", "EUR")
        self.assertEqual(rate, Decimal("1"))
        self.assertEqual(rate_date, "same currency")
        mocked_urlopen.assert_not_called()

    def test_same_currency_preserves_requested_rate_date(self):
        with patch("main.urlopen") as mocked_urlopen:
            rate, rate_date = get_rate("EUR", "EUR", "2026-08-01")
        self.assertEqual(rate, Decimal("1"))
        self.assertEqual(rate_date, "2026-08-01")
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

    def test_historical_rate_adds_date_query(self):
        response = MagicMock()
        response.read.return_value = b'{"rate": 0.91, "date": "2026-08-01"}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch("main.urlopen", return_value=response) as mocked_urlopen:
            rate, rate_date = get_rate("USD", "EUR", "2026-08-01")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://api.frankfurter.dev/v2/rate/USD/EUR?date=2026-08-01",
        )
        self.assertEqual(rate, Decimal("0.91"))
        self.assertEqual(rate_date, "2026-08-01")

    def test_provider_pin_is_added_to_query(self):
        response = MagicMock()
        response.read.return_value = b'{"rate": 0.91, "date": "2026-08-01"}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch("main.urlopen", return_value=response) as mocked_urlopen:
            get_rate("USD", "EUR", "2026-08-01", provider="ecb")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://api.frankfurter.dev/v2/rate/USD/EUR?date=2026-08-01&providers=ECB",
        )

    def test_invalid_rate_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            validate_rate_date("01-08-2026")

    def test_invalid_provider_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "letters"):
            validate_provider("ECB!")

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

    def test_normalize_amount_returns_versioned_contract(self):
        with patch(
            "main.get_rate",
            return_value=(Decimal("0.92"), "2026-08-19"),
        ):
            result = normalize_amount(Decimal("100"), "usd", "eur")
        self.assertEqual(result["schema"], AMOUNT_SCHEMA)
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["tool"], "currency-normalizer")
        self.assertEqual(result["version"], "0.4.0")
        self.assertEqual(result["from_currency"], "USD")
        self.assertEqual(result["to_currency"], "EUR")
        self.assertEqual(result["converted_amount"], "92.00")
        self.assertEqual(result["rate_source"]["selection"], "blended")
        json.dumps(result)

    def test_pinned_provider_is_preserved_in_provenance(self):
        with patch(
            "main.get_rate",
            return_value=(Decimal("0.92"), "2026-08-19"),
        ):
            result = normalize_amount(100, "USD", "EUR", provider="ecb")
        self.assertEqual(result["rate_source"]["selection"], "pinned")
        self.assertEqual(result["rate_source"]["provider"], "ECB")

    def test_same_currency_source_is_explicit(self):
        source = build_rate_source("EUR", "EUR", provider="ECB")
        self.assertEqual(source["selection"], "same_currency")
        self.assertIsNone(source["provider"])

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
            normalized = normalize_quote(quote, "EUR", provider="ECB")
        self.assertEqual(normalized["currency"], "EUR")
        self.assertEqual(normalized["price"], 92.0)
        self.assertEqual(normalized["lead_time_weeks"], 6)
        self.assertEqual(normalized["payment_days"], 30)
        metadata = normalized["normalization"]
        self.assertEqual(metadata["schema"], NORMALIZATION_SCHEMA)
        self.assertEqual(metadata["schema_version"], SCHEMA_VERSION)
        self.assertEqual(metadata["original_currency"], "USD")
        self.assertEqual(metadata["original_price"], "100")
        self.assertEqual(metadata["normalized_price"], "92.00")
        self.assertEqual(metadata["rate_source"]["provider"], "ECB")

    def test_load_quote_rejects_missing_field(self):
        quote = {"name": "Supplier A", "currency": "EUR", "price": 100}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quote.json"
            path.write_text(json.dumps(quote), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lead_time_weeks"):
                load_quote(path)

    def test_batch_normalization_writes_outputs_and_manifest(self):
        quote_a = {
            "name": "Supplier A",
            "currency": "USD",
            "price": 100,
            "lead_time_weeks": 6,
            "payment_days": 30,
        }
        quote_b = {
            "name": "Supplier B",
            "currency": "GBP",
            "price": 80,
            "lead_time_weeks": 8,
            "payment_days": 45,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quote_a_path = root / "supplier_a.json"
            quote_b_path = root / "supplier_b.json"
            output_dir = root / "normalized"
            quote_a_path.write_text(json.dumps(quote_a), encoding="utf-8")
            quote_b_path.write_text(json.dumps(quote_b), encoding="utf-8")
            with patch(
                "main.get_rate",
                side_effect=[
                    (Decimal("0.92"), "2026-08-01"),
                    (Decimal("1.17"), "2026-08-01"),
                ],
            ):
                items = normalize_quote_files(
                    [quote_a_path, quote_b_path],
                    "EUR",
                    rate_date="2026-08-01",
                    provider="ECB",
                )
            manifest = write_batch_outputs(
                items,
                output_dir,
                "EUR",
                rate_date="2026-08-01",
                provider="ECB",
            )
            self.assertEqual(len(items), 2)
            self.assertEqual(manifest["schema"], MANIFEST_SCHEMA)
            self.assertEqual(manifest["schema_version"], SCHEMA_VERSION)
            self.assertEqual(manifest["target_currency"], "EUR")
            self.assertEqual(manifest["requested_rate_date"], "2026-08-01")
            self.assertEqual(manifest["rate_source"]["provider"], "ECB")
            self.assertTrue(manifest["run_id"].startswith("cn-"))
            self.assertTrue((output_dir / "supplier_a_eur.json").exists())
            self.assertTrue((output_dir / "supplier_b_eur.json").exists())
            self.assertTrue((output_dir / "normalization-manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
