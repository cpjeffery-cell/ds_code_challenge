import json
import urllib.request
from pathlib import Path
import ssl
import boto3
import certifi
from data_extraction import DataExtraction


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

    result = extraction.run()

    print(f"Time: {result['time_seconds']} seconds")
    print(f"Score: {result['score']}/100")
    print(f"Passed: {result['passed']}")


if __name__ == "__main__":
    main()