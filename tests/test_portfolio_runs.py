import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from main import (
    POLICY_SCHEMA,
    SCHEMA_VERSION,
    build_run_id,
    load_portfolio_policy,
    normalize_quote_files,
    policy_sha256,
    resolve_portfolio_policy,
    sha256_file,
    write_batch_outputs,
)


class PortfolioRunTests(unittest.TestCase):
    def test_policy_file_is_loaded_and_normalized(self):
        policy = {
            "schema": POLICY_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "portfolio_id": "FY2026-EU",
            "base_currency": "eur",
            "rate_date": "2026-08-01",
            "provider": "ecb",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(policy), encoding="utf-8")
            loaded = load_portfolio_policy(path)

        self.assertEqual(loaded["base_currency"], "EUR")
        self.assertEqual(loaded["provider"], "ECB")
        self.assertEqual(loaded["portfolio_id"], "FY2026-EU")

    def test_cli_values_override_policy(self):
        policy = {
            "schema": POLICY_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "portfolio_id": "BASE",
            "base_currency": "EUR",
            "rate_date": "2026-08-01",
            "provider": "ECB",
        }
        resolved = resolve_portfolio_policy(
            policy,
            target_currency="GBP",
            rate_date="2026-08-02",
            provider="BOE",
            portfolio_id="OVERRIDE",
        )
        self.assertEqual(resolved["base_currency"], "GBP")
        self.assertEqual(resolved["rate_date"], "2026-08-02")
        self.assertEqual(resolved["provider"], "BOE")
        self.assertEqual(resolved["portfolio_id"], "OVERRIDE")

    def test_run_id_is_deterministic_and_order_independent(self):
        policy = resolve_portfolio_policy(
            target_currency="EUR",
            rate_date="2026-08-01",
            provider="ECB",
            portfolio_id="FY2026-EU",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = root / "a.json"
            b = root / "b.json"
            a.write_text('{"a":1}', encoding="utf-8")
            b.write_text('{"b":2}', encoding="utf-8")

            first = build_run_id([a, b], policy)
            second = build_run_id([b, a], policy)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("cn-"))

    def test_run_id_changes_when_source_content_changes(self):
        policy = resolve_portfolio_policy(target_currency="EUR")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quote.json"
            path.write_text('{"v":1}', encoding="utf-8")
            first = build_run_id([path], policy)
            path.write_text('{"v":2}', encoding="utf-8")
            second = build_run_id([path], policy)

        self.assertNotEqual(first, second)

    def test_policy_digest_is_stable(self):
        policy = resolve_portfolio_policy(
            target_currency="EUR",
            provider="ECB",
        )
        self.assertEqual(policy_sha256(policy), policy_sha256(dict(policy)))

    def test_manifest_records_source_and_output_digests_and_lineage(self):
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

        policy = resolve_portfolio_policy(
            target_currency="EUR",
            rate_date="2026-08-01",
            provider="ECB",
            portfolio_id="FY2026-EU",
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = root / "supplier_a.json"
            b = root / "supplier_b.json"
            output = root / "normalized"
            a.write_text(json.dumps(quote_a), encoding="utf-8")
            b.write_text(json.dumps(quote_b), encoding="utf-8")

            with patch(
                "main.get_rate",
                side_effect=[
                    (Decimal("0.92"), "2026-08-01"),
                    (Decimal("1.17"), "2026-08-01"),
                ],
            ):
                items = normalize_quote_files(
                    [a, b],
                    policy["base_currency"],
                    rate_date=policy["rate_date"],
                    provider=policy["provider"],
                )

            manifest = write_batch_outputs(
                items,
                output,
                policy["base_currency"],
                policy=policy,
            )

            self.assertEqual(manifest["portfolio_id"], "FY2026-EU")
            self.assertEqual(manifest["policy"], policy)
            self.assertEqual(manifest["policy_sha256"], policy_sha256(policy))
            self.assertEqual(len(manifest["files"]), 2)
            for file_record in manifest["files"]:
                self.assertEqual(len(file_record["source_sha256"]), 64)
                self.assertEqual(len(file_record["output_sha256"]), 64)
                self.assertEqual(
                    file_record["source_sha256"],
                    sha256_file(file_record["source"]),
                )
                self.assertEqual(
                    file_record["output_sha256"],
                    sha256_file(file_record["output"]),
                )

            for item in items:
                metadata = item["quote"]["normalization"]
                self.assertEqual(metadata["run_id"], manifest["run_id"])
                self.assertEqual(metadata["portfolio_id"], "FY2026-EU")


if __name__ == "__main__":
    unittest.main()
