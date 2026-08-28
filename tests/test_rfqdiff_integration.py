import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import normalize_quote, write_json


class RfqdiffIntegrationTests(unittest.TestCase):
    def test_normalized_quotes_are_accepted_by_rfqdiff(self):
        rfqdiff_main = os.environ.get("RFQDIFF_MAIN")
        if not rfqdiff_main:
            self.skipTest("RFQDIFF_MAIN is not configured")

        quote_a = {
            "name": "Supplier A",
            "currency": "EUR",
            "price": 100,
            "lead_time_weeks": 6,
            "payment_days": 30,
        }
        quote_b = {
            "name": "Supplier B",
            "currency": "EUR",
            "price": 105,
            "lead_time_weeks": 5,
            "payment_days": 45,
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path_a = root / "supplier_a_eur.json"
            path_b = root / "supplier_b_eur.json"
            write_json(normalize_quote(quote_a, "EUR"), path_a)
            write_json(normalize_quote(quote_b, "EUR"), path_b)

            completed = subprocess.run(
                [
                    sys.executable,
                    rfqdiff_main,
                    str(path_a),
                    str(path_b),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["tool"], "rfqdiff")
        self.assertEqual(payload["currency"], "EUR")
        self.assertEqual(len(payload["suppliers"]), 2)
        for supplier in payload["suppliers"]:
            self.assertIn("normalization", supplier)
            self.assertEqual(
                supplier["normalization"]["schema_version"],
                "1.0",
            )


if __name__ == "__main__":
    unittest.main()
