"""Check signed access to the challenge GeoJSON objects."""

import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError


BUCKET = "cct-ds-code-challenge-input-data"
REGION = "af-south-1"
OBJECT_KEYS = (
    "city-hex-polygons-8-10.geojson",
    "city-hex-polygons-8.geojson",
)
PREVIEW_BYTES = 2048


def require_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def preview_object(s3_client, object_key: str) -> None:
    metadata = s3_client.head_object(Bucket=BUCKET, Key=object_key)
    print(
        f"{object_key}: accessible; "
        f"size={metadata.get('ContentLength')}; "
        f"content_type={metadata.get('ContentType')}; "
        f"etag={metadata.get('ETag')}"
    )

    response = s3_client.get_object(
        Bucket=BUCKET,
        Key=object_key,
        Range=f"bytes=0-{PREVIEW_BYTES - 1}",
    )
    preview = response["Body"].read(PREVIEW_BYTES).decode("utf-8", errors="replace")
    print(f"{object_key}: preview={preview[:200]!r}")


def main() -> int:
    access_key = require_environment("AWS_ACCESS_KEY_ID")
    secret_key = require_environment("AWS_SECRET_ACCESS_KEY")

    s3_client = boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    for object_key in OBJECT_KEYS:
        preview_object(s3_client, object_key)

    print("S3 connectivity check passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BotoCoreError, ClientError, RuntimeError) as error:
        print(f"S3 connectivity check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
