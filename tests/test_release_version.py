import unittest

import main


class ReleaseVersionTests(unittest.TestCase):
    def test_runtime_version_is_v050(self):
        self.assertEqual(main.VERSION, "0.5.0")

    def test_schema_version_remains_stable(self):
        self.assertEqual(main.SCHEMA_VERSION, "1.0")


if __name__ == "__main__":
    unittest.main()
