import unittest
from decimal import Decimal


def reconcile(unit_price, quantity, supplier_total):
    computed = Decimal(unit_price) * Decimal(quantity)
    stated = Decimal(supplier_total)
    difference = stated - computed
    return computed, difference, difference == 0


class CommercialQuoteRegressionScenarios(unittest.TestCase):
    """Anonymized scenarios derived from real-world RFQ structures."""

    def test_per_unit_freight_reconciles_to_confirmed_total(self):
        computed, difference, matches = reconcile("3900", "2", "7800")
        self.assertEqual(computed, Decimal("7800"))
        self.assertEqual(difference, Decimal("0"))
        self.assertTrue(matches)

    def test_conditional_charges_are_not_part_of_comparable_total(self):
        components = [
            {"status": "included", "amount": Decimal("2500")},
            {"status": "included", "amount": Decimal("320")},
            {"status": "included", "amount": Decimal("6300")},
            {"status": "conditional", "amount": Decimal("320")},
            {"status": "conditional", "amount": Decimal("530")},
        ]
        comparable = sum(
            item["amount"] for item in components if item["status"] == "included"
        )
        self.assertEqual(comparable, Decimal("9120"))

    def test_flat_rate_service_is_single_included_component(self):
        components = [
            {
                "type": "equipment",
                "status": "included",
                "currency": "USD",
                "supplier_total": Decimal("38500"),
            }
        ]
        self.assertEqual(components[0]["supplier_total"], Decimal("38500"))


if __name__ == "__main__":
    unittest.main()
