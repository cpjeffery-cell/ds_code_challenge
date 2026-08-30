"""Tests for the Step 5.3 anonymisation of the augmented Witsand subsample."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_anonymisation import DataAnonymisation


class DataAnonymisationTest(unittest.TestCase):
    """Verify column generalisation and the k-anonymity split."""

    def setUp(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.anonymisation = DataAnonymisation(
            contract_path=repository_root
            / "config"
            / "data_anonymisation_contract.yml",
            log_path=Path(tempfile.gettempdir())
            / "data_anonymisation_test.log",
        )
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def test_run_drops_identifiers_and_generalises_columns(self):
        data = pd.DataFrame(
            {
                "Unnamed: 0": [0, 1, 2, 3, 4],
                "notification_number": [1, 2, 3, 4, 5],
                "reference_number": ["a", "b", "c", "d", "e"],
                "latitude": [-33.5] * 5,
                "longitude": [18.5] * 5,
                "h3_level8_index": ["hex1"] * 5,
                "creation_timestamp": [
                    "2020-01-01 01:00:00",
                    "2020-01-01 02:00:00",
                    "2020-01-01 03:00:00",
                    "2020-01-01 04:00:00",
                    "2020-01-01 05:00:00",
                ],
                "completion_timestamp": ["2020-01-02 01:00:00"] * 5,
                "cause_code": ["c1"] * 5,
            }
        )

        result = self.anonymisation.run(data, repository_root=self.tempdir.name)
        anonymised = result["anonymised_data"]

        self.assertNotIn("Unnamed: 0", anonymised.columns)
        self.assertNotIn("notification_number", anonymised.columns)
        self.assertNotIn("reference_number", anonymised.columns)
        self.assertNotIn("latitude", anonymised.columns)
        self.assertNotIn("longitude", anonymised.columns)
        self.assertTrue(
            (anonymised["creation_timestamp"].dt.hour % 6 == 0).all()
        )
        self.assertTrue(Path(result["anonymised_path"]).exists())
        self.assertTrue(Path(result["review_path"]).exists())

    def test_small_groups_are_flagged_for_review(self):
        data = pd.DataFrame(
            {
                "h3_level8_index": ["hex1"] * 5 + ["hex2"],
                "creation_timestamp": ["2020-01-01 00:00:00"] * 6,
                "cause_code": ["c1"] * 5 + ["c2"],
            }
        )

        result = self.anonymisation.run(data, repository_root=self.tempdir.name)

        self.assertEqual(result["anonymised_row_count"], 5)
        self.assertEqual(result["flagged_row_count"], 1)
        self.assertEqual(result["flagged_data"]["h3_level8_index"].iloc[0], "hex2")

    def test_generalization_hierarchy_rescues_rows_from_review(self):
        data = pd.DataFrame(
            {
                "h3_level8_index": ["hex1"] * 5,
                "creation_timestamp": ["2020-01-01 00:00:00"] * 5,
                "cause_code": ["c1", "c2", "c3", "c4", "c5"],
                "cause_code_group": ["grp_a"] * 5,
            }
        )

        result = self.anonymisation.run(data, repository_root=self.tempdir.name)

        self.assertEqual(result["anonymised_row_count"], 5)
        self.assertEqual(result["flagged_row_count"], 0)
        self.assertTrue(
            (result["anonymised_data"]["cause_code"] == "grp_a").all()
        )

    def test_time_hierarchy_rescues_rows_spread_across_one_day(self):
        data = pd.DataFrame(
            {
                "h3_level8_index": ["hex1"] * 5,
                "creation_timestamp": [
                    "2020-01-01 00:00:00",
                    "2020-01-01 06:00:00",
                    "2020-01-01 12:00:00",
                    "2020-01-01 18:00:00",
                    "2020-01-01 23:00:00",
                ],
                "cause_code": ["c1", "c2", "c3", "c4", "c5"],
            }
        )

        result = self.anonymisation.run(data, repository_root=self.tempdir.name)

        self.assertEqual(result["anonymised_row_count"], 5)
        self.assertEqual(result["flagged_row_count"], 0)
        self.assertTrue(
            (result["anonymised_data"]["cause_code"] == "REDACTED").all()
        )
        self.assertTrue(
            (result["anonymised_data"]["creation_timestamp"].dt.hour == 0).all()
        )


if __name__ == "__main__":
    unittest.main()
