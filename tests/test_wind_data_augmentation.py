"""Tests for the Step 5.2 Atlantis wind augmentation."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from further_data_transformation import (
    WindAugmentationError,
    WindDataAugmentation,
)


class WindDataAugmentationTest(unittest.TestCase):
    """Verify workbook parsing and nearest-timestamp join behavior."""

    def setUp(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.augmentation = WindDataAugmentation(
            contract_path=repository_root
            / "config"
            / "further_data_transformation_contract.yml",
            log_path=Path(tempfile.gettempdir())
            / "wind_data_augmentation_test.log",
        )
        self.join = {
            "notification_time_column": "creation_timestamp",
            "direction_column": "wind_direction_deg",
            "speed_column": "wind_speed_ms",
            "max_gap_hours": 3,
        }

    def test_join_nearest_matches_closest_observation(self):
        subset = pd.DataFrame(
            {
                "creation_timestamp": [
                    "2020-01-01 00:50:00+02:00",
                    "2020-01-01 05:00:00+02:00",
                ]
            }
        )
        observations = pd.DataFrame(
            {
                "wind_timestamp": pd.to_datetime(
                    ["2020-01-01 00:00:00", "2020-01-01 01:00:00"]
                ),
                "wind_direction_deg": [170.0, 180.0],
                "wind_speed_ms": [4.0, 4.1],
            }
        )

        augmented = self.augmentation._join_nearest(
            subset, observations, self.join
        )

        self.assertEqual(augmented["wind_direction_deg"].iloc[0], 180.0)
        self.assertTrue(augmented["wind_direction_deg"].isna().iloc[1])

    def test_join_nearest_preserves_original_row_order(self):
        subset = pd.DataFrame(
            {
                "creation_timestamp": [
                    "2020-01-01 05:00:00+02:00",
                    "2020-01-01 00:50:00+02:00",
                ]
            }
        )
        observations = pd.DataFrame(
            {
                "wind_timestamp": pd.to_datetime(["2020-01-01 01:00:00"]),
                "wind_direction_deg": [180.0],
                "wind_speed_ms": [4.1],
            }
        )

        augmented = self.augmentation._join_nearest(
            subset, observations, self.join
        )

        expected_order = pd.to_datetime(
            subset["creation_timestamp"]
        ).dt.tz_localize(None)
        self.assertEqual(
            augmented["creation_timestamp"].tolist(),
            expected_order.tolist(),
        )

    def test_parse_observations_nulls_out_of_range_values(self):
        import further_data_transformation as module

        workbook_contract = {
            "header_search_row_count": 15,
            "date_time_column_label": "Date & Time",
            "station_name": "Atlantis AQM Site",
            "direction_label": "Wind Dir V",
            "speed_label": "Wind Speed V",
            "date_time_format": "%d/%m/%Y %H:%M",
        }

        def fake_read_excel(_source, engine, header, nrows=None, skiprows=None):
            if nrows is not None:
                return pd.DataFrame(
                    [
                        ["Date & Time", "Atlantis AQM Site", "Atlantis AQM Site"],
                        [None, "Wind Dir V", "Wind Speed V"],
                        [None, "Deg", "m/s"],
                    ]
                )
            return pd.DataFrame(
                [["01/01/2020 00:00", 400.0, -1.0]]
            )

        original_read_excel = module.pd.read_excel
        module.pd.read_excel = fake_read_excel

        try:
            observations = self.augmentation._parse_observations(
                b"unused", workbook_contract, self.join
            )
        finally:
            module.pd.read_excel = original_read_excel

        self.assertTrue(observations["wind_direction_deg"].isna().iloc[0])
        self.assertTrue(observations["wind_speed_ms"].isna().iloc[0])

    def test_parse_observations_handles_leading_title_rows(self):
        import further_data_transformation as module

        workbook_contract = {
            "header_search_row_count": 15,
            "date_time_column_label": "Date & Time",
            "station_name": "Atlantis AQM Site",
            "direction_label": "Wind Dir V",
            "speed_label": "Wind Speed V",
            "date_time_format": "%d/%m/%Y %H:%M",
        }

        def fake_read_excel(_source, engine, header, nrows=None, skiprows=None):
            if nrows is not None:
                return pd.DataFrame(
                    [
                        ["MultiStation: ...", None, None],
                        [None, None, None],
                        ["Date & Time", "Atlantis AQM Site", "Atlantis AQM Site"],
                        [None, "Wind Dir V", "Wind Speed V"],
                        [None, "Deg", "m/s"],
                    ]
                )
            self.assertEqual(skiprows, 5)
            return pd.DataFrame([["01/01/2020 00:00", 170.0, 4.1]])

        original_read_excel = module.pd.read_excel
        module.pd.read_excel = fake_read_excel

        try:
            observations = self.augmentation._parse_observations(
                b"unused", workbook_contract, self.join
            )
        finally:
            module.pd.read_excel = original_read_excel

        self.assertEqual(observations["wind_direction_deg"].iloc[0], 170.0)
        self.assertEqual(observations["wind_speed_ms"].iloc[0], 4.1)

    def test_download_workbook_raises_after_exhausting_retries(self):
        def _always_fails(request, timeout, context):
            raise ValueError("boom")

        import further_data_transformation as module

        original_urlopen = module.urlopen
        module.urlopen = lambda *args, **kwargs: _always_fails(None, None, None)

        try:
            with self.assertRaisesRegex(
                WindAugmentationError, "unavailable after 2 attempts"
            ):
                self.augmentation._download_workbook(
                    "https://example.invalid/workbook",
                    max_attempts=2,
                    retry_delay_seconds=0,
                )
        finally:
            module.urlopen = original_urlopen


if __name__ == "__main__":
    unittest.main()
