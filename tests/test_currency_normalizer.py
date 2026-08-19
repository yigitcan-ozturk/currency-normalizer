import unittest
from decimal import Decimal
from urllib.error import HTTPError, URLError
from unittest.mock import MagicMock, patch

from main import get_rate


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


if __name__ == "__main__":
    unittest.main()
