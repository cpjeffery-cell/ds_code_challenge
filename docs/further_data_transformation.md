# Further Data Transformation

## Step 5.1: Witsand Centroid Subset

The transformation downloads the City of Cape Town Official Suburb FeatureServer layer and requests the one official planning-suburb polygon named `WITSAND`. It calculates that polygon's centroid programmatically after projecting it to `EPSG:32734`, a local metre-based coordinate reference system appropriate for Cape Town distance calculations.

`sr_hex.csv.gz` is downloaded from the challenge S3 bucket. Its valid latitude and longitude values are converted to points in the same projected CRS. The subset contains every request whose straight-line distance from the computed Witsand centroid is at most 80 metres.

The 80 m radius is a reproducible approximation of one minute walking at 4.8 km/h:

```text
4.8 km/h * (1 / 60) h = 0.08 km = 80 m
```

The implementation intentionally does not claim this is a road-network travel-time isochrone. A routing service would require an additional external dependency, credentials or billing, and availability handling. The contract requires exactly one returned official-suburb polygon and a non-empty filtered subset. It logs the selected suburb, source object ID, centroid, radius, input rows, invalid-coordinate count, selected-row count, and elapsed time to `logs/further_data_transformation.log`.

The filtered data remains in memory for the Step 5.2 wind-data augmentation. No intermediate artifact is written at this stage.

## Step 5.2: Atlantis Wind Augmentation

The augmentation downloads the City-owned `Wind.xlsx` workbook (2020 wind direction and speed, hourly) from ArcGIS. This endpoint has been observed to be unreliable during development: the README's own `.ods` download-handler URL returned an HTTP 404 page, and the direct CityApps `.ods` URL failed DNS resolution outright. The working ArcGIS URL itself intermittently produced transient connection failures rather than a permanent "not found" response, which is the specific failure pattern retries address well: a permanent failure (bad URL, deleted resource) would not be helped by retrying, but a transient network hiccup or momentary server load often clears within seconds.

For that reason the download is retried up to a configured number of attempts with an increasing delay between attempts, and the response bytes are checked for the XLSX/ZIP signature before use, so a captured error page is never mistaken for a valid workbook. Two alternatives were considered and rejected: (1) caching a last-known-good copy of the workbook on disk, rejected because the assignment requires the download and preparation to happen programmatically within the script on each run, not from a stored artifact; and (2) falling back to a second mirror URL, rejected because no second official source for this dataset was found — inventing one would reintroduce the same "unverified URL" problem already ruled out during source discovery. If every retry attempt is exhausted, the run raises a clear error rather than falling back to fabricated data — a fabricated fallback would silently corrupt the augmented dataset and is not an acceptable substitute for a genuinely unreachable dependency.

The workbook has a 3-row header (station name, measurement type, unit) followed by hourly observations. Rather than hard-coding column positions, the parser locates the "Date & Time" column and the two "Atlantis AQM Site" columns (direction and speed) by matching the configured header labels, so a change in station column order would not silently misassign data.

Each request's `creation_timestamp` is matched to the nearest-in-time wind observation using `pandas.merge_asof`. Because the source is hourly, a configurable maximum time gap (`max_gap_hours`) bounds how far apart a match may be; requests with no observation inside that gap are left with missing wind values rather than assigned a misleadingly distant reading.

All settings — the source URL, retry attempts/delay, workbook header labels, join column names, and the gap tolerance — are defined in the `wind_augmentation` section of `config/further_data_transformation_contract.yml`, not hard-coded in Python.