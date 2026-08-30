# Data Extraction Validation

This document describes the contract used to validate the resolution-8 extraction from `city-hex-polygons-8-10.geojson` against `city-hex-polygons-8.geojson`.

## Expected Shared Structure

The datasets are expected to share these columns:

| Column | Expected type |
| --- | --- |
| `type` | string |
| `properties_index` | string |
| `properties_centroid_lat` | number |
| `properties_centroid_lon` | number |
| `geometry_type` | string |
| `geometry_coordinates` | array |

The extracted multi-resolution dataset may also contain `properties_resolution`. Therefore, the two datasets are not required to have identical columns.

## Validation Checks

The validation compares:

1. Required shared columns are present in both datasets.
2. The number of extracted rows matches the reference dataset.
3. `properties_index` coverage matches between datasets.
4. `properties_index` is unique in both datasets.

The index comparison is order-independent. Missing and unexpected index counts are written to the run log.

## Pipeline Gate and Downstream Data

The extraction is available to later pipeline steps only when its conformance score meets the configured threshold. A failing score stops the pipeline with an error that includes the score, threshold, and missing and unexpected index counts.

After a successful validation, downstream steps receive only extracted features whose `properties_index` is also present in the standalone resolution-8 reference. This overlap is intentional and observable through the logged mismatch counts; the pipeline does not silently discard differences.

## Conformance Score

Each check produces a value from `0` to `1`:

- Shared columns: `0.15`
- Row count: `0.20`
- Index coverage: `0.45`
- Index uniqueness: `0.20`

The score is calculated as:

```text
score = (
    shared_columns_score * 0.15
    + row_count_score * 0.20
    + index_coverage_score * 0.45
    + index_uniqueness_score * 0.20
) * 100
```

The extraction passes when the score is at least `99.5` out of `100`.

The YAML contract in `config/data_extraction_contract.yml` is the machine-readable source for the checks and scoring rules used by the current class. This document provides the human-readable explanation.
