"""Tests for resolution-8 extraction validation behavior."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_extraction import DataExtraction, ExtractionValidationError


class DataExtractionTest(unittest.TestCase):
    """Verify validation gates and downstream feature selection."""

    def setUp(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.extraction = DataExtraction(
            s3_client=None,
            bucket="unused",
            contract_path=repository_root
            / "config"
            / "data_extraction_contract.yml",
            log_path=Path(tempfile.gettempdir()) / "data_extraction_test.log",
        )

    @staticmethod
    def _features(*indexes):
        return pd.DataFrame(
            {
                "type": "Feature",
                "properties_index": indexes,
                "properties_centroid_lat": 0.0,
                "properties_centroid_lon": 0.0,
                "geometry_type": "Polygon",
                "geometry_coordinates": [[] for _ in indexes],
            }
        )

    def test_run_stops_when_score_is_below_threshold(self):
        self.extraction._extract_resolution_8 = lambda resolution: self._features(
            "a"
        )
        self.extraction._load_reference = lambda: self._features("a", "b")

        with self.assertRaisesRegex(
            ExtractionValidationError,
            "pipeline stopped before the spatial join",
        ) as context:
            self.extraction.run()

        self.assertGreaterEqual(context.exception.time_seconds, 0)
        self.assertEqual(context.exception.score, 67.5)

    def test_run_exposes_only_shared_indexes_after_passing(self):
        self.extraction._extract_resolution_8 = lambda resolution: self._features(
            "a", "b", "unexpected"
        )
        self.extraction._load_reference = lambda: self._features("a", "b")

        result = self.extraction.run()

        self.assertTrue(result["passed"])
        self.assertEqual(
            set(result["features"]["properties_index"]),
            {"a", "b"},
        )


if __name__ == "__main__":
    unittest.main()