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