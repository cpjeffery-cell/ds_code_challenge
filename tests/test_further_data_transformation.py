"""Tests for the Step 5.1 suburb-centroid subset."""

import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from further_data_transformation import (
    FurtherDataTransformation,
    FurtherTransformationError,
)


class FurtherDataTransformationTest(unittest.TestCase):
    """Verify the configured suburb-centroid subset behavior."""

    def setUp(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.transformation = FurtherDataTransformation(
            s3_client=None,
            bucket="unused",
            contract_path=repository_root
            / "config"
            / "further_data_transformation_contract.yml",
            log_path=Path(tempfile.gettempdir())
            / "further_data_transformation_test.log",
        )
        self.suburb = gpd.GeoDataFrame(
            {"OBJECTID": [1], "OFC_SBRB_NAME": ["WITSAND"]},
            geometry=[
                Polygon(
                    [(-10, -10), (10, -10), (10, 10), (-10, 10)]
                )
            ],
            crs="EPSG:32734",
        )

    def _set_common_mocks(self, points):
        service_requests = pd.DataFrame(
            {"latitude": [-33.5] * len(points), "longitude": [18.5] * len(points)}
        )
        self.transformation._load_suburb = lambda source: self.suburb
        self.transformation._load_gzip_csv = lambda key: service_requests
        import further_data_transformation

        further_data_transformation.SpatialData.points_from_coordinates = (
            lambda *args: (points, pd.Series([True] * len(points)))
        )

    def test_run_returns_requests_within_configured_radius(self):
        points = gpd.GeoDataFrame(
            geometry=[Point(0, 0), Point(100, 0)],
            crs="EPSG:32734",
        )
        self._set_common_mocks(points)

        result = self.transformation.run()

        self.assertEqual(result["suburb_name"], "WITSAND")
        self.assertEqual(result["radius_metres"], 80)
        self.assertEqual(result["selected_row_count"], 1)

    def test_run_fails_when_subset_is_empty(self):
        points = gpd.GeoDataFrame(geometry=[Point(100, 0)], crs="EPSG:32734")
        self._set_common_mocks(points)

        with self.assertRaisesRegex(
            FurtherTransformationError,
            "produced no requests within 80 m",
        ):
            self.transformation.run()