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

## Threshold Selection Rationale

The thresholds are based on the full exploratory run, not selected arbitrarily:

- The observed H3 match rate was 99.996920%, with 29 differences across 941,634 requests. Three were failed spatial joins and 26 were non-zero immediate-neighbour H3 cells. A 99.99% minimum permits at most 94 differences at this volume, giving limited headroom for the investigated boundary cases while remaining only about three times the observed difference count.
- A 99.95% match minimum was considered but rejected because it would permit about 470 differences, over sixteen times the observed 29. That would make a material regression less visible.
- The observed failed spatial-join rate was about 0.00041%: 3 valid-coordinate requests out of 729,270 had no containing City polygon. A 0.01% maximum permits at most 72 failed joins at this volume. This allowance covers a small number of coverage or boundary edge cases while still detecting failures such as reversed coordinates, an incorrect CRS, or unavailable polygons.

These limits deliberately use separate denominators. The H3 match rate uses every request because all output indices are validated against `sr_hex.csv.gz`. The failed-join rate uses only valid-coordinate requests, so required `"0"` values for missing or invalid coordinates do not appear as join failures.

## Assignment Outcomes

Each run reports and logs these separate counts:

- Missing or invalid coordinates: requests with blank, non-numeric, or out-of-range coordinates. These receive the required `"0"` index and are not failed spatial joins.
- Failed spatial joins: requests with valid coordinates for which no City H3 polygon was found. These also receive `"0"`, and their rate is checked against the 0.01% threshold.
- Wrong H3 assignments: requests assigned a non-zero H3 index that differs from `sr_hex.csv.gz`. These contribute to the H3 reference-match rate but are not spatial-join failures.

In the exploratory run, these categories were 212,364 missing or invalid coordinates, 3 failed spatial joins, and 26 wrong H3 assignments. The last category consisted of immediate-neighbour H3 cells and informed the 99.99% match-rate threshold.

## Reproducibility Rules

The transformation contract also defines the source object names and column mappings, the polygon coordinate column, the `"0"` value for unassigned requests, the `EPSG:4326` coordinate reference system, valid latitude and longitude ranges, and the `within` spatial predicate. It requires each request to match at most one polygon and declares that the supplied service-request files are compared in row order.

`within` intentionally excludes points exactly on a polygon boundary. In exploratory validation, 26 non-identical non-zero H3 results were immediate neighbours, which is consistent with boundary precision. The configured 99.99% H3 match rate accounts for these observed edge cases without concealing material regressions.

## Performance

The source and validation-reference CSV objects download and parse concurrently, as configured by `performance.concurrent_download_workers`. The source dataset is read in full because it is the transformation output. The reference is read with only `inputs.validation_reference_columns` because validation needs only `h3_level8_index`.

The exploratory timing showed S3 download and CSV parsing took 21.78 seconds of a 24.11-second run, while point creation and the spatial join took 2.15 seconds. These changes therefore target the observed bottleneck without changing the spatial-assignment approach.

After applying both changes, the measured run took 21.59 seconds: concurrent S3 download and CSV parsing took 19.09 seconds, the spatial join took 2.33 seconds, and validation took 0.17 seconds. This reduced total runtime by 2.52 seconds (about 10.5%) while preserving the 99.996920% H3 reference-match rate.

The process logs total rows, valid and invalid coordinate counts, failed joins and their rate, reference-match rate, input-load time, total elapsed time, and pass/fail outcome to `logs/data_transformation.log`.