"""Create the Step 5.1 suburb-centroid service-request subset."""

from io import BytesIO
import logging
import time
from pathlib import Path
from urllib.parse import urlencode

import geopandas as gpd
import pandas as pd
import yaml

from spatial_data import SpatialData


class FurtherTransformationError(ValueError):
    """Raised when the Step 5.1 subset cannot be produced."""


class FurtherDataTransformation:
    """Filter service requests to a configured distance from an official suburb."""

    def __init__(
        self,
        s3_client,
        bucket,
        contract_path="../config/further_data_transformation_contract.yml",
        log_path="../logs/further_data_transformation.log",
    ):
        self.s3_client = s3_client
        self.bucket = bucket
        self.contract_path = Path(contract_path)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("further_data_transformation")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s"
                )
            )
            self.logger.addHandler(handler)

    def run(self):
        """Return requests within the configured distance of the suburb centroid."""
        start_time = time.perf_counter()
        self.logger.info("Run started")
        with self.contract_path.open() as file:
            contract = yaml.safe_load(file)

        inputs = contract["inputs"]
        source = contract["official_suburb_source"]
        spatial_filter = contract["spatial_filter"]
        validation = contract["validation"]
        suburb = self._load_suburb(source)
        self._validate_suburb(suburb, source, validation)
        service_requests = self._load_gzip_csv(inputs["service_requests_key"])
        request_points, valid_coordinates = SpatialData.points_from_coordinates(
            service_requests,
            inputs["latitude_column"],
            inputs["longitude_column"],
            spatial_filter["latitude_range"],
            spatial_filter["longitude_range"],
            spatial_filter["coordinate_reference_system"],
            spatial_filter["projected_coordinate_reference_system"],
        )
        suburb = suburb.to_crs(
            spatial_filter["projected_coordinate_reference_system"]
        )
        centroid = suburb.geometry.iloc[0].centroid
        distances = request_points.geometry.distance(centroid)
        subset = service_requests.loc[
            distances.index[distances.le(spatial_filter["radius_metres"])]
        ].copy()
        elapsed_seconds = time.perf_counter() - start_time

        self.logger.info(
            "Subset | suburb=%s | suburb_object_id=%s | centroid_x=%.3f | "
            "centroid_y=%.3f | radius_metres=%d | input_rows=%d | "
            "invalid_coordinates=%d | selected_rows=%d | time_seconds=%.4f",
            suburb[source["suburb_name_column"]].iloc[0],
            suburb["OBJECTID"].iloc[0],
            centroid.x,
            centroid.y,
            spatial_filter["radius_metres"],
            len(service_requests),
            (~valid_coordinates).sum(),
            len(subset),
            elapsed_seconds,
        )
        if validation["require_non_empty_subset"] and subset.empty:
            raise FurtherTransformationError(
                "Further data transformation produced no requests within "
                f"{spatial_filter['radius_metres']} m of the computed "
                f"{source['suburb_name']} centroid."
            )

        return {
            "time_seconds": round(elapsed_seconds, 4),
            "suburb_name": suburb[source["suburb_name_column"]].iloc[0],
            "suburb_object_id": int(suburb["OBJECTID"].iloc[0]),
            "centroid_x": round(centroid.x, 3),
            "centroid_y": round(centroid.y, 3),
            "radius_metres": spatial_filter["radius_metres"],
            "input_row_count": len(service_requests),
            "invalid_coordinate_count": int((~valid_coordinates).sum()),
            "selected_row_count": len(subset),
            "data": subset,
        }

    @staticmethod
    def _load_suburb(source):
        fields = ",".join(source["output_fields"])
        where = (
            f"{source['suburb_name_column']} = "
            f"'{source['suburb_name'].replace("'", "''")}'"
        )
        query = urlencode(
            {
                "where": where,
                "outFields": fields,
                "returnGeometry": "true",
                "f": "geojson",
            }
        )
        return gpd.read_file(f"{source['layer_url']}/query?{query}")

    @staticmethod
    def _validate_suburb(suburb, source, validation):
        if suburb.empty:
            raise FurtherTransformationError(
                "The official suburb source returned no polygon for "
                f"{source['suburb_name']}."
            )
        if validation["require_exactly_one_suburb"] and len(suburb) != 1:
            raise FurtherTransformationError(
                "The official suburb source returned "
                f"{len(suburb)} polygons for {source['suburb_name']}; "
                "exactly one is required."
            )

    def _load_gzip_csv(self, key):
        response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
        return pd.read_csv(
            BytesIO(response["Body"].read()),
            compression="gzip",
            low_memory=False,
        )