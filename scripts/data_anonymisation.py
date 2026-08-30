"""Anonymise the Step 5.2 augmented Witsand wind subsample."""

import logging
import time
from pathlib import Path

import pandas as pd
import yaml


class DataAnonymisationError(ValueError):
    """Raised when the Step 5.3 anonymisation cannot be produced."""


class DataAnonymisation:
    """Generalise location/time and split out re-identifiable rows for review."""

    def __init__(
        self,
        contract_path="../config/data_anonymisation_contract.yml",
        log_path="../logs/data_anonymisation.log",
    ):
        self.contract_path = Path(contract_path)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("data_anonymisation")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s"
                )
            )
            self.logger.addHandler(handler)

    def run(self, data, repository_root="."):
        """Return the anonymised subset and write it, plus a flagged review set, to disk."""
        start_time = time.perf_counter()
        self.logger.info("Run started")
        with self.contract_path.open() as file:
            contract = yaml.safe_load(file)

        location = contract["location"]
        time_contract = contract["time"]
        k_anonymity = contract["k_anonymity"]
        outputs = contract["outputs"]

        generalised = data.drop(
            columns=[
                column
                for column in contract["direct_identifier_columns"]
                if column in data.columns
            ]
            + [
                column
                for column in location["columns_to_drop"]
                if column in data.columns
            ]
        ).copy()

        for column in time_contract["columns_to_generalize"]:
            if column in generalised.columns:
                generalised[column] = pd.to_datetime(
                    generalised[column], errors="coerce"
                ).dt.floor(f"{time_contract['bucket_hours']}h")

        anonymised, flagged = self._split_by_k_anonymity(
            generalised, k_anonymity
        )

        repository_root = Path(repository_root)
        anonymised_path = repository_root / outputs["anonymised_path"]
        review_path = repository_root / outputs["review_path"]
        anonymised_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        anonymised.to_csv(anonymised_path, index=False)
        flagged.to_csv(review_path, index=False)

        elapsed_seconds = time.perf_counter() - start_time

        self.logger.info(
            "Anonymisation | input_rows=%d | anonymised_rows=%d | "
            "flagged_rows=%d | time_seconds=%.4f",
            len(data),
            len(anonymised),
            len(flagged),
            elapsed_seconds,
        )

        return {
            "time_seconds": round(elapsed_seconds, 4),
            "input_row_count": len(data),
            "anonymised_row_count": len(anonymised),
            "flagged_row_count": len(flagged),
            "anonymised_path": anonymised_path,
            "review_path": review_path,
            "anonymised_data": anonymised,
            "flagged_data": flagged,
        }

    @staticmethod
    def _split_by_k_anonymity(generalised, k_anonymity):
        base_columns = k_anonymity["base_quasi_identifier_columns"]
        generalization_column = k_anonymity["generalization_column"]
        cause_hierarchy = [
            level
            for level in k_anonymity["generalization_hierarchy"]
            if level in generalised.columns
        ]
        time_column = k_anonymity["time_column"]
        time_hierarchy = k_anonymity.get("time_generalization_hierarchy", [])
        minimum_group_size = k_anonymity["minimum_group_size"]

        anonymised_parts = []
        remaining = generalised.copy()

        # Try the already-configured time bucket first, then progressively
        # coarser ones, only for rows the cause-code hierarchy could not rescue.
        for time_offset in [None] + list(time_hierarchy):
            if remaining.empty:
                break

            working = remaining.copy()
            if time_offset is not None:
                working[time_column] = pd.to_datetime(
                    working[time_column], errors="coerce"
                ).dt.floor(time_offset)

            working = DataAnonymisation._apply_cause_hierarchy(
                working,
                base_columns,
                generalization_column,
                cause_hierarchy,
                minimum_group_size,
                anonymised_parts,
            )

            # Rows still unresolved carry forward at their original (finer) time value.
            remaining = remaining.loc[working.index]

        anonymised = (
            pd.concat(anonymised_parts).sort_index()
            if anonymised_parts
            else generalised.iloc[0:0].copy()
        )
        return anonymised, remaining

    @staticmethod
    def _apply_cause_hierarchy(
        working,
        base_columns,
        generalization_column,
        cause_hierarchy,
        minimum_group_size,
        anonymised_parts,
    ):
        # Try each level of the hierarchy (finest to coarsest) before full suppression.
        for level_column in cause_hierarchy:
            if working.empty:
                break

            group_columns = base_columns + [level_column]
            group_sizes = working.groupby(
                group_columns, dropna=False
            )[group_columns[0]].transform("size")

            passed_rows = working.loc[group_sizes.ge(minimum_group_size)].copy()
            if not passed_rows.empty:
                passed_rows[generalization_column] = passed_rows[level_column]
                anonymised_parts.append(passed_rows)

            working = working.loc[group_sizes.lt(minimum_group_size)].copy()

        # Last resort: suppress the generalizable attribute and regroup by location/time alone.
        if not working.empty:
            group_sizes = working.groupby(
                base_columns, dropna=False
            )[base_columns[0]].transform("size")

            passed_rows = working.loc[group_sizes.ge(minimum_group_size)].copy()
            if not passed_rows.empty:
                passed_rows[generalization_column] = "REDACTED"
                anonymised_parts.append(passed_rows)

            working = working.loc[group_sizes.lt(minimum_group_size)].copy()

        return working

