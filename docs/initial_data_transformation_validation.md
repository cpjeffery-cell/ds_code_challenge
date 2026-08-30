# Initial Data Transformation Validation

The transformation assigns each valid service-request coordinate to the containing validated resolution-8 H3 polygon. The result preserves all service-request rows and adds `h3_level8_index`.

Rows with missing, non-numeric, or out-of-range coordinates receive the string index `"0"`. Valid coordinates with no containing City H3 polygon also receive `"0"`, but are recorded as failed spatial joins.

## Validation Sources

- `sr.csv.gz` is the input service-request dataset.
- The validated resolution-8 polygons returned by Step 1 provide the spatial lookup.
- `sr_hex.csv.gz` is a reference only. It supplies the expected `h3_level8_index` for row-by-row validation and is not used to assign the result.

## Contract Thresholds

`config/data_transformation_contract.yml` is the machine-readable source for both thresholds.

| Measure | Threshold | Reason |
| --- | --- | --- |
| H3 reference-match rate | At least 99.99% | The exploratory run matched 99.9969% of 941,634 rows. Twenty-six mismatches were immediate H3 neighbours, consistent with boundary precision. The threshold permits a small known tolerance while detecting material index-assignment regressions. |
| Failed spatial-join rate | At most 0.01% of valid-coordinate rows | The exploratory run had 3 failed joins among 729,270 valid-coordinate records, or about 0.00041%. This permits limited polygon-coverage edge cases but detects a wrong CRS, coordinate order, or broken polygon lookup. |

The two measures answer different questions. The H3 match rate compares the complete output to the supplied reference. The failed-join rate measures only valid-coordinate rows that did not match any supplied City polygon. A transformation fails when either threshold is breached.

## Reproducibility Rules

The transformation contract also defines the source object names and column mappings, the polygon coordinate column, the `"0"` value for unassigned requests, the `EPSG:4326` coordinate reference system, valid latitude and longitude ranges, and the `within` spatial predicate. It requires each request to match at most one polygon and declares that the supplied service-request files are compared in row order.

`within` intentionally excludes points exactly on a polygon boundary. In exploratory validation, 26 non-identical non-zero H3 results were immediate neighbours, which is consistent with boundary precision. The configured 99.99% H3 match rate accounts for these observed edge cases without concealing material regressions.

## Performance

The source and validation-reference CSV objects download and parse concurrently, as configured by `performance.concurrent_download_workers`. The source dataset is read in full because it is the transformation output. The reference is read with only `inputs.validation_reference_columns` because validation needs only `h3_level8_index`.

The exploratory timing showed S3 download and CSV parsing took 21.78 seconds of a 24.11-second run, while point creation and the spatial join took 2.15 seconds. These changes therefore target the observed bottleneck without changing the spatial-assignment approach.

After applying both changes, the measured run took 21.59 seconds: concurrent S3 download and CSV parsing took 19.09 seconds, the spatial join took 2.33 seconds, and validation took 0.17 seconds. This reduced total runtime by 2.52 seconds (about 10.5%) while preserving the 99.996920% H3 reference-match rate.

The process logs total rows, valid and invalid coordinate counts, failed joins and their rate, reference-match rate, input-load time, total elapsed time, and pass/fail outcome to `logs/data_transformation.log`.