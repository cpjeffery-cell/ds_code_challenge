"""Create the Step 5.1 suburb-centroid service-request subset."""

from io import BytesIO
import logging
import ssl
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
import geopandas as gpd
import pandas as pd
import yaml

from spatial_data import SpatialData


class FurtherTransformationError(ValueError):
    """Raised when the Step 5.1 subset cannot be produced."""


class WindAugmentationError(ValueError):
    """Raised when the Step 5.2 wind augmentation cannot be produced."""


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

    def run(self, service_requests=None):
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
        # Reuse Step 2's already-downloaded, H3-joined data instead of a redundant re-download.
        if service_requests is None:
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


class WindDataAugmentation:
    """Augment a service-request subset with 2020 Atlantis AQM wind data."""

    def __init__(
        self,
        contract_path="../config/further_data_transformation_contract.yml",
        log_path="../logs/wind_data_augmentation.log",
    ):
        self.contract_path = Path(contract_path)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("wind_data_augmentation")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s"
                )
            )
            self.logger.addHandler(handler)

    def run(self, subset):
        """Return the subset augmented with nearest-in-time wind observations."""
        start_time = time.perf_counter()
        self.logger.info("Run started")
        with self.contract_path.open() as file:
            contract = yaml.safe_load(file)["wind_augmentation"]

        source = contract["source"]
        workbook_contract = contract["workbook"]
        join = contract["join"]
        validation = contract["validation"]

        workbook_bytes = self._download_workbook(
            source["url"],
            source["max_download_attempts"],
            source["retry_delay_seconds"],
        )
        observations = self._parse_observations(workbook_bytes, workbook_contract, join)

        if validation["require_non_empty_observations"] and observations.empty:
            raise WindAugmentationError(
                f"No wind observations were parsed for {workbook_contract['station_name']}."
            )

        augmented = self._join_nearest(subset, observations, join)
        elapsed_seconds = time.perf_counter() - start_time

        self.logger.info(
            "Augmentation | observations=%d | input_rows=%d | "
            "unmatched_rows=%d | time_seconds=%.4f",
            len(observations),
            len(subset),
            int(augmented[join["direction_column"]].isna().sum()),
            elapsed_seconds,
        )

        return {
            "time_seconds": round(elapsed_seconds, 4),
            "observation_count": len(observations),
            "input_row_count": len(subset),
            "unmatched_row_count": int(
                augmented[join["direction_column"]].isna().sum()
            ),
            "data": augmented,
        }

    @staticmethod
    def _download_workbook(url, max_attempts, retry_delay_seconds):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                with urlopen(request, timeout=30, context=ssl_context) as response:
                    workbook_bytes = response.read()

                if not workbook_bytes.startswith(b"PK"):
                    raise ValueError(
                        "Downloaded content is not a valid XLSX workbook."
                    )

                return workbook_bytes

            except (URLError, ValueError) as error:
                last_error = error
                if attempt < max_attempts:
                    time.sleep(retry_delay_seconds * attempt)

        # Retries with backoff, never a synthetic fallback, so an unreliable
        # endpoint fails loudly instead of silently corrupting the dataset.
        raise WindAugmentationError(
            f"Wind data source unavailable after {max_attempts} attempts."
        ) from last_error

    @staticmethod
    def _parse_observations(workbook_bytes, workbook_contract, join):
        probe = pd.read_excel(
            BytesIO(workbook_bytes),
            engine="openpyxl",
            header=None,
            nrows=workbook_contract["header_search_row_count"],
        )

        date_time_label = workbook_contract["date_time_column_label"]
        header_row_matches = probe.eq(date_time_label).any(axis=1)

        # The header block's row position varies: some downloads prepend a
        # title/blank row, so it is located by content, not a fixed offset.
        if not header_row_matches.any():
            raise WindAugmentationError(
                f"Could not locate the '{date_time_label}' header row in "
                "the wind workbook."
            )

        station_row_position = header_row_matches.idxmax()
        station_row = probe.iloc[station_row_position]
        metric_row = probe.iloc[station_row_position + 1]

        date_time_column = probe.columns[
            station_row.eq(date_time_label) | metric_row.eq(date_time_label)
        ]
        station_columns = probe.columns[
            station_row.eq(workbook_contract["station_name"])
        ]
        direction_column = next(
            column
            for column in station_columns
            if metric_row[column] == workbook_contract["direction_label"]
        )
        speed_column = next(
            column
            for column in station_columns
            if metric_row[column] == workbook_contract["speed_label"]
        )

        raw = pd.read_excel(
            BytesIO(workbook_bytes),
            engine="openpyxl",
            header=None,
            skiprows=station_row_position + 3,
        )

        direction_values = pd.to_numeric(raw[direction_column], errors="coerce")
        speed_values = pd.to_numeric(raw[speed_column], errors="coerce")

        # Guard against a column-detection mistake feeding in the wrong station's values.
        direction_values = direction_values.where(direction_values.between(0, 360))
        speed_values = speed_values.where(speed_values.ge(0))

        observations = pd.DataFrame(
            {
                "wind_timestamp": pd.to_datetime(
                    raw[date_time_column[0]],
                    format=workbook_contract["date_time_format"],
                    errors="coerce",
                ),
                join["direction_column"]: direction_values,
                join["speed_column"]: speed_values,
            }
        )

        return (
            observations.dropna(subset=["wind_timestamp"])
            .sort_values("wind_timestamp")
            .reset_index(drop=True)
        )

    @staticmethod
    def _join_nearest(subset, observations, join):
        notification_time_column = join["notification_time_column"]

        left = subset.copy()
        left[notification_time_column] = pd.to_datetime(
            left[notification_time_column]
        ).dt.tz_localize(None)
        left = left.sort_values(notification_time_column)

        augmented = pd.merge_asof(
            left,
            observations,
            left_on=notification_time_column,
            right_on="wind_timestamp",
            direction="nearest",
            tolerance=pd.Timedelta(hours=join["max_gap_hours"]),
        )

        # merge_asof drops the caller's index; reattach it before restoring row order.
        augmented.index = left.index
        return augmented.sort_index().drop(columns=["wind_timestamp"])