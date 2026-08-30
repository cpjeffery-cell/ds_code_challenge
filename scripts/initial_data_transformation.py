"""Assign service requests to validated resolution-8 H3 polygons."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import logging
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import yaml

from spatial_data import SpatialData

class TransformationValidationError(ValueError):
    """Raised when spatial-join validation breaches its contract."""

    def __init__(
        self,
        message,
        time_seconds,
        match_rate,
        failed_join_rate,
        failed_join_count,
        wrong_h3_assignment_count,
    ):
        super().__init__(message)
        self.time_seconds = time_seconds
        self.match_rate = match_rate
        self.failed_join_rate = failed_join_rate
        self.failed_join_count = failed_join_count
        self.wrong_h3_assignment_count = wrong_h3_assignment_count


class InitialDataTransformation:
    """Assign service-request coordinates to resolution-8 H3 polygons."""

    def __init__(
        self,
        s3_client,
        bucket,
        contract_path="../config/data_transformation_contract.yml",
        log_path="../logs/data_transformation.log",
    ):
        self.s3_client = s3_client
        self.bucket = bucket
        self.contract_path = Path(contract_path)
        self.log_path = Path(log_path)

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("initial_data_transformation")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s"
                )
            )
            self.logger.addHandler(handler)

    def run(self, validated_hexagons):
        """Return requests with H3 indices after contract-based validation."""
        start_time = time.perf_counter()
        self.logger.info("Run started")

        with self.contract_path.open() as file:
            contract = yaml.safe_load(file)

        inputs = contract["inputs"]
        spatial_join_contract = contract["spatial_join"]
        validation = contract["validation"]
        performance = contract["performance"]
        input_load_start_time = time.perf_counter()
        with ThreadPoolExecutor(
            max_workers=performance["concurrent_download_workers"]
        ) as executor:
            service_requests_future = executor.submit(
                self._load_gzip_csv,
                inputs["service_requests_key"],
            )
            expected_requests_future = executor.submit(
                self._load_gzip_csv,
                inputs["validation_reference_key"],
                inputs["validation_reference_columns"],
            )
            service_requests = service_requests_future.result()
            expected_requests = expected_requests_future.result()
        input_load_seconds = time.perf_counter() - input_load_start_time
        joined_requests, valid_coordinates = self._spatial_join(
            service_requests,
            validated_hexagons,
            inputs,
            spatial_join_contract,
        )

        output_column = inputs["output_index_column"]
        zero_index = inputs["zero_index"]
        if len(joined_requests) != len(expected_requests):
            raise ValueError(
                "Cannot validate transformation: sr.csv.gz and sr_hex.csv.gz "
                "have different row counts."
            )
        if output_column not in expected_requests.columns:
            raise ValueError(
                f"Cannot validate transformation: {output_column} is missing "
                "from sr_hex.csv.gz."
            )

        if validation["comparison_method"] != "row_order":
            raise ValueError(
                "Unsupported transformation validation comparison method: "
                f"{validation['comparison_method']}."
            )

        calculated_indexes = joined_requests[output_column].fillna(zero_index)
        expected_indexes = expected_requests[output_column].fillna(zero_index)
        calculated_indexes = calculated_indexes.astype(str)
        expected_indexes = expected_indexes.astype(str)
        matching_indexes = calculated_indexes.eq(expected_indexes)
        match_rate = matching_indexes.mean() * 100

        failed_join_mask = valid_coordinates & calculated_indexes.eq(zero_index)
        failed_join_count = (
            failed_join_mask.sum()
            if validation["count_valid_coordinate_zero_as_failed_join"]
            else 0
        )
        valid_coordinate_count = valid_coordinates.sum()
        failed_join_rate = (
            failed_join_count / max(valid_coordinate_count, 1) * 100
        )
        missing_or_invalid_coordinate_count = (~valid_coordinates).sum()
        wrong_h3_assignment_count = (
            calculated_indexes.ne(zero_index) & ~matching_indexes
        ).sum()
        elapsed_seconds = time.perf_counter() - start_time

        passed = (
            match_rate >= validation["minimum_h3_match_rate"]
            and failed_join_rate <= validation["maximum_failed_join_rate"]
        )
        self.logger.info(
            "Validation | rows=%d | valid_coordinates=%d | "
            "missing_or_invalid_coordinates=%d | failed_joins=%d | "
            "failed_join_rate=%.6f%% | h3_match_rate=%.6f%%",
            len(joined_requests),
            valid_coordinate_count,
            missing_or_invalid_coordinate_count,
            failed_join_count,
            failed_join_rate,
            match_rate,
        )
        self.logger.info(
            "Assignment outcomes | missing_or_invalid_coordinates=%d | "
            "failed_spatial_joins=%d | wrong_h3_assignments=%d",
            missing_or_invalid_coordinate_count,
            failed_join_count,
            wrong_h3_assignment_count,
        )
        self.logger.info(
            "Run finished | input_load_seconds=%.4f | time_seconds=%.4f | "
            "passed=%s",
            input_load_seconds,
            elapsed_seconds,
            passed,
        )

        if not passed:
            raise TransformationValidationError(
                "Initial data transformation failed validation: "
                f"H3 match rate {match_rate:.6f}% requires at least "
                f"{validation['minimum_h3_match_rate']:.6f}%; failed spatial "
                f"join rate {failed_join_rate:.6f}% allows at most "
                f"{validation['maximum_failed_join_rate']:.6f}%.",
                time_seconds=round(elapsed_seconds, 4),
                match_rate=round(match_rate, 6),
                failed_join_rate=round(failed_join_rate, 6),
                failed_join_count=int(failed_join_count),
                wrong_h3_assignment_count=int(wrong_h3_assignment_count),
            )

        return {
            "time_seconds": round(elapsed_seconds, 4),
            "match_rate": round(match_rate, 6),
            "failed_join_rate": round(failed_join_rate, 6),
            "missing_or_invalid_coordinate_count": int(
                missing_or_invalid_coordinate_count
            ),
            "failed_join_count": int(failed_join_count),
            "wrong_h3_assignment_count": int(wrong_h3_assignment_count),
            "passed": passed,
            "data": joined_requests,
        }

    def _load_gzip_csv(self, key, usecols=None):
        response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
        return pd.read_csv(
            BytesIO(response["Body"].read()),
            compression="gzip",
            low_memory=False,
            usecols=usecols,
        )

    @staticmethod
    def _spatial_join(
        service_requests,
        validated_hexagons,
        inputs,
        spatial_join_contract,
    ):
        request_points, valid_coordinates = SpatialData.points_from_coordinates(
            service_requests,
            inputs["latitude_column"],
            inputs["longitude_column"],
            spatial_join_contract["latitude_range"],
            spatial_join_contract["longitude_range"],
            spatial_join_contract["coordinate_reference_system"],
        )

        polygon_index = inputs["polygon_index_column"]
        polygon_coordinates = inputs["polygon_coordinates_column"]
        output_column = inputs["output_index_column"]
        hexagons = gpd.GeoDataFrame(
            validated_hexagons.assign(
                geometry=validated_hexagons[polygon_coordinates].apply(
                    lambda coordinates: shape(
                        {"type": "Polygon", "coordinates": coordinates}
                    )
                )
            ),
            geometry="geometry",
            crs=spatial_join_contract["coordinate_reference_system"],
        )[[polygon_index, "geometry"]].rename(
            columns={polygon_index: output_column}
        )

        joined_requests = service_requests.copy()
        joined_requests[output_column] = inputs["zero_index"]

        spatial_join = gpd.sjoin(
            request_points,
            hexagons,
            how="left",
            predicate=spatial_join_contract["predicate"],
        )
        if (
            spatial_join_contract["require_single_polygon_match"]
            and spatial_join.index.duplicated().any()
        ):
            raise ValueError(
                "A service request matched more than one H3 polygon."
            )

        joined_requests.loc[spatial_join.index, output_column] = (
            spatial_join[output_column]
            .fillna(inputs["zero_index"])
            .astype(str)
        )
        return joined_requests, valid_coordinates