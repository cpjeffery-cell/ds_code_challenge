import json
import urllib.request
from pathlib import Path
import ssl
import boto3
import certifi
from data_extraction import DataExtraction, ExtractionValidationError
from initial_data_transformation import (
    InitialDataTransformation,
    TransformationValidationError,
)
from further_data_transformation import (
    FurtherDataTransformation,
    FurtherTransformationError,
    WindAugmentationError,
    WindDataAugmentation,
)
from data_anonymisation import DataAnonymisation


CREDENTIALS_URL = (
    "https://cct-ds-code-challenge-input-data.s3.af-south-1."
    "amazonaws.com/ds_code_challenge_creds.json"
)

BUCKET = "cct-ds-code-challenge-input-data"
REGION = "af-south-1"


def load_credentials():
    context = ssl.create_default_context(
        cafile=certifi.where()
    )

    with urllib.request.urlopen(
        CREDENTIALS_URL,
        context=context,
    ) as response:
        return json.load(response)["s3"]


def main():
    credentials = load_credentials()

    s3_client = boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"],
    )

    repository_root = Path(__file__).resolve().parent.parent

    extraction = DataExtraction(
        s3_client=s3_client,
        bucket=BUCKET,
        contract_path=repository_root
        / "config"
        / "data_extraction_contract.yml",
        log_path=repository_root
        / "logs"
        / "data_extraction.log",
    )

    print("\nStep 1: Resolution-8 Polygon Extraction")
    try:
        result = extraction.run()
    except ExtractionValidationError as error:
        print(f"Extraction time: {error.time_seconds} seconds")
        print(f"Extraction conformance score: {error.score}/100")
        print("Extraction passed: False")
        raise SystemExit(f"Pipeline failed: {error}") from error

    print(f"Extraction time: {result['time_seconds']} seconds")
    print(f"Extraction conformance score: {result['score']}/100")
    print(f"Extraction passed: {result['passed']}")

    transformation = InitialDataTransformation(
        s3_client=s3_client,
        bucket=BUCKET,
        contract_path=repository_root
        / "config"
        / "data_transformation_contract.yml",
        log_path=repository_root
        / "logs"
        / "data_transformation.log",
    )

    print("\nStep 2: Service Request H3 Assignment")
    try:
        transformation_result = transformation.run(result["features"])
    except TransformationValidationError as error:
        print(f"Transformation time: {error.time_seconds} seconds")
        print(f"H3 reference-match rate: {error.match_rate}%")
        print(f"Failed spatial joins: {error.failed_join_count}")
        print(f"Wrong H3 assignments: {error.wrong_h3_assignment_count}")
        print(f"Failed spatial-join rate: {error.failed_join_rate}%")
        print("Transformation passed: False")
        raise SystemExit(f"Pipeline failed: {error}") from error

    print(f"Transformation time: {transformation_result['time_seconds']} seconds")
    print(
        "H3 reference-match rate: "
        f"{transformation_result['match_rate']}%"
    )
    print(
        "Missing or invalid coordinates: "
        f"{transformation_result['missing_or_invalid_coordinate_count']}"
    )
    print(f"Failed spatial joins: {transformation_result['failed_join_count']}")
    print(
        "Wrong H3 assignments: "
        f"{transformation_result['wrong_h3_assignment_count']}"
    )
    print(
        "Failed spatial-join rate: "
        f"{transformation_result['failed_join_rate']}%"
    )
    print(f"Transformation passed: {transformation_result['passed']}")

    further_transformation = FurtherDataTransformation(
        s3_client=s3_client,
        bucket=BUCKET,
        contract_path=repository_root
        / "config"
        / "further_data_transformation_contract.yml",
        log_path=repository_root
        / "logs"
        / "further_data_transformation.log",
    )

    print("\nStep 5.1: Witsand Centroid Subset")
    try:
        further_result = further_transformation.run(
            service_requests=transformation_result["data"]
        )
    except FurtherTransformationError as error:
        raise SystemExit(f"Pipeline failed: {error}") from error

    print(f"Selected suburb: {further_result['suburb_name']}")
    print(f"Distance radius: {further_result['radius_metres']} m")
    print(f"Selected service requests: {further_result['selected_row_count']}")
    print(f"Step 5.1 time: {further_result['time_seconds']} seconds")

    wind_augmentation = WindDataAugmentation(
        contract_path=repository_root
        / "config"
        / "further_data_transformation_contract.yml",
        log_path=repository_root
        / "logs"
        / "wind_data_augmentation.log",
    )

    print("\nStep 5.2: Atlantis Wind Augmentation")
    try:
        wind_result = wind_augmentation.run(further_result["data"])
    except WindAugmentationError as error:
        raise SystemExit(f"Pipeline failed: {error}") from error

    print(f"Wind observations parsed: {wind_result['observation_count']}")
    print(f"Unmatched service requests: {wind_result['unmatched_row_count']}")
    print(f"Step 5.2 time: {wind_result['time_seconds']} seconds")

    anonymisation = DataAnonymisation(
        contract_path=repository_root
        / "config"
        / "data_anonymisation_contract.yml",
        log_path=repository_root
        / "logs"
        / "data_anonymisation.log",
    )

    print("\nStep 5.3: Witsand Wind Subsample Anonymisation")
    anonymisation_result = anonymisation.run(
        wind_result["data"], repository_root=repository_root
    )

    print(f"Anonymised rows: {anonymisation_result['anonymised_row_count']}")
    print(f"Flagged for manual review: {anonymisation_result['flagged_row_count']}")
    print(f"Anonymised output: {anonymisation_result['anonymised_path']}")
    print(f"Review output: {anonymisation_result['review_path']}")
    print(f"Step 5.3 time: {anonymisation_result['time_seconds']} seconds")

    print("\nPipeline complete: Steps 1, 2, 5.1, 5.2, 5.3 all passed.")


if __name__ == "__main__":
    main()