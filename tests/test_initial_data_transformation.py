"""Tests for initial data-transformation validation behavior."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from initial_data_transformation import (
    InitialDataTransformation,
    TransformationValidationError,
)


class InitialDataTransformationTest(unittest.TestCase):
    """Verify the transformation's contract thresholds."""

    def setUp(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.transformation = InitialDataTransformation(
            s3_client=None,
            bucket="unused",
            contract_path=repository_root
            / "config"
            / "data_transformation_contract.yml",
            log_path=Path(tempfile.gettempdir())
            / "data_transformation_test.log",
        )

    def test_run_returns_data_when_rates_pass_contract(self):
        service_requests = pd.DataFrame({"latitude": [-33.9], "longitude": [18.4]})
        expected_requests = service_requests.assign(h3_level8_index="expected")
        self.transformation._load_gzip_csv = lambda key, usecols=None: (
            service_requests if key == "sr.csv.gz" else expected_requests
        )
        self.transformation._spatial_join = (
            lambda requests, hexagons, inputs, spatial_join_contract: (
                expected_requests,
                pd.Series([True]),
            )
        )

        result = self.transformation.run(pd.DataFrame())

        self.assertTrue(result["passed"])
        self.assertEqual(result["match_rate"], 100.0)
        self.assertEqual(result["failed_join_rate"], 0.0)

    def test_run_fails_when_h3_match_rate_is_below_contract(self):
        service_requests = pd.DataFrame({"latitude": [-33.9], "longitude": [18.4]})
        expected_requests = service_requests.assign(h3_level8_index="expected")
        calculated_requests = service_requests.assign(h3_level8_index="actual")
        self.transformation._load_gzip_csv = lambda key, usecols=None: (
            service_requests if key == "sr.csv.gz" else expected_requests
        )
        self.transformation._spatial_join = (
            lambda requests, hexagons, inputs, spatial_join_contract: (
                calculated_requests,
                pd.Series([True]),
            )
        )

        with self.assertRaisesRegex(
            TransformationValidationError,
            "H3 match rate 0.000000% requires at least 99.990000%",
        ):
            self.transformation.run(pd.DataFrame())

    def test_run_fails_when_failed_join_rate_exceeds_contract(self):
        service_requests = pd.DataFrame({"latitude": [-33.9], "longitude": [18.4]})
        expected_requests = service_requests.assign(h3_level8_index="0")
        self.transformation._load_gzip_csv = lambda key, usecols=None: (
            service_requests if key == "sr.csv.gz" else expected_requests
        )
        self.transformation._spatial_join = (
            lambda requests, hexagons, inputs, spatial_join_contract: (
                expected_requests,
                pd.Series([True]),
            )
        )

        with self.assertRaisesRegex(
            TransformationValidationError,
            "failed spatial join rate 100.000000% allows at most 0.010000%",
        ):
            self.transformation.run(pd.DataFrame())


if __name__ == "__main__":
    unittest.main()