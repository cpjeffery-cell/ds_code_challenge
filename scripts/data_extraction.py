"""Extract and validate resolution-8 GeoJSON features."""

import json
import logging
import time
from pathlib import Path

import pandas as pd
import yaml


class ExtractionValidationError(ValueError):
    """Raised when extracted resolution-8 data fails validation."""

    def __init__(self, message, time_seconds, score):
        super().__init__(message)
        self.time_seconds = time_seconds
        self.score = score


class DataExtraction:
    """Extract resolution-8 features and validate them against a reference."""

    def __init__(
        self,
        s3_client,
        bucket,
        contract_path="../config/data_extraction_contract.yml",
        log_path="../logs/data_extraction.log",
    ):
        self.s3_client = s3_client
        self.bucket = bucket
        self.contract_path = Path(contract_path)
        self.log_path = Path(log_path)

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("data_extraction")
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
        """Return the elapsed time, score, and pass/fail result."""
        start_time = time.perf_counter()
        self.logger.info("Run started")

        with self.contract_path.open() as file:
            contract = yaml.safe_load(file)

        # The YAML contract is the source of truth for the comparison key,
        # expected resolution, enabled checks, weights, and pass threshold.
        index_column = contract["comparison"]["index_column"]
        resolution = contract["comparison"]["expected_resolution"]
        threshold = contract["scoring"]["pass_threshold"]
        scale = contract["scoring"]["scale"]
        expected_columns = set(contract["expected_shared_columns"])
        weights = {
            name: check["weight"]
            for name, check in contract["checks"].items()
            if check["enabled"]
        }

        extracted_df = self._extract_resolution_8(resolution)
        reference_df = self._load_reference()

        # The contract allows the extracted data to contain the additional
        # resolution column, so only the listed shared columns are required.
        shared_columns_score = float(
            expected_columns.issubset(extracted_df.columns)
            and expected_columns.issubset(reference_df.columns)
        )

        row_count_score = min(
            len(extracted_df),
            len(reference_df),
        ) / max(len(reference_df), 1)

        extracted_indexes = set(extracted_df[index_column].dropna().astype(str))
        reference_indexes = set(reference_df[index_column].dropna().astype(str))
        missing_indexes = reference_indexes - extracted_indexes
        unexpected_indexes = extracted_indexes - reference_indexes

        # Coverage measures how much of the reference index set was extracted.
        index_coverage_score = len(
            extracted_indexes & reference_indexes
        ) / max(len(reference_indexes), 1)

        index_uniqueness_score = float(
            extracted_df[index_column].is_unique
            and reference_df[index_column].is_unique
        )

        score_components = {
            "shared_columns": shared_columns_score,
            "row_count": row_count_score,
            "index_coverage": index_coverage_score,
            "index_uniqueness": index_uniqueness_score,
        }

        score = sum(
            score_components[name] * weights[name]
            for name in weights
        ) * scale

        elapsed_seconds = time.perf_counter() - start_time
        passed = score >= threshold

        self.logger.info(
            "Validation | shared_columns=%.4f | row_count=%.4f | "
            "index_coverage=%.4f | index_uniqueness=%.4f | "
            "missing_indexes=%d | unexpected_indexes=%d",
            shared_columns_score,
            row_count_score,
            index_coverage_score,
            index_uniqueness_score,
            len(missing_indexes),
            len(unexpected_indexes),
        )
        self.logger.info(
            "Run finished | extracted_rows=%d | reference_rows=%d | "
            "time_seconds=%.4f | score=%.2f | threshold=%.2f | passed=%s",
            len(extracted_df),
            len(reference_df),
            elapsed_seconds,
            score,
            threshold,
            passed,
        )

        if not passed:
            raise ExtractionValidationError(
                "Resolution-8 extraction failed validation: "
                f"score {score:.2f}/100 is below the required "
                f"{threshold:.2f}/100. Missing reference indexes: "
                f"{len(missing_indexes)}; unexpected extracted indexes: "
                f"{len(unexpected_indexes)}. The pipeline stopped before "
                "the spatial join.",
                time_seconds=round(elapsed_seconds, 4),
                score=round(score, 2),
            )

        # Only validated shared indexes are available to downstream steps.
        self.resolution_8_features = extracted_df[
            extracted_df[index_column].astype(str).isin(reference_indexes)
        ].copy()

        return {
            "time_seconds": round(elapsed_seconds, 4),
            "score": round(score, 2),
            "passed": passed,
            "features": self.resolution_8_features,
        }

    def _extract_resolution_8(self, resolution):
        # S3 Select filters the multi-resolution file before it reaches Python.
        query = f"""
            SELECT feature
            FROM S3Object[*].features[*] AS feature
            WHERE feature.properties.resolution = {resolution}
        """

        response = self.s3_client.select_object_content(
            Bucket=self.bucket,
            Key="city-hex-polygons-8-10.geojson",
            ExpressionType="SQL",
            Expression=query,
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": "\n"}},
        )

        records = []
        buffer = ""

        for event in response["Payload"]:
            if "Records" not in event:
                continue

            buffer += event["Records"]["Payload"].decode("utf-8")
            lines = buffer.split("\n")
            buffer = lines.pop()

            for line in lines:
                if line.strip():
                    records.append(json.loads(line)["feature"])

        if buffer.strip():
            records.append(json.loads(buffer)["feature"])

        return pd.json_normalize(records, sep="_")

    def _load_reference(self):
        response = self.s3_client.get_object(
            Bucket=self.bucket,
            Key="city-hex-polygons-8.geojson",
        )

        geojson_data = json.loads(
            response["Body"].read().decode("utf-8")
        )

        return pd.json_normalize(
            geojson_data["features"],
            sep="_",
        )
