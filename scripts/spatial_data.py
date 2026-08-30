"""Reusable helpers for validating geographic coordinates and making points."""

import geopandas as gpd
import pandas as pd


class SpatialData:
    """Create projected point data from tabular latitude and longitude values."""

    @staticmethod
    def points_from_coordinates(
        data,
        latitude_column,
        longitude_column,
        latitude_range,
        longitude_range,
        coordinate_reference_system,
        projected_coordinate_reference_system=None,
    ):
        """Return valid-coordinate points and a mask aligned to the input rows."""
        latitude = pd.to_numeric(data[latitude_column], errors="coerce")
        longitude = pd.to_numeric(data[longitude_column], errors="coerce")
        valid_coordinates = (
            latitude.notna()
            & longitude.notna()
            & latitude.between(*latitude_range)
            & longitude.between(*longitude_range)
        )
        points = gpd.GeoDataFrame(
            data.loc[valid_coordinates].copy(),
            geometry=gpd.points_from_xy(
                longitude.loc[valid_coordinates],
                latitude.loc[valid_coordinates],
            ),
            crs=coordinate_reference_system,
        )
        if projected_coordinate_reference_system:
            points = points.to_crs(projected_coordinate_reference_system)

        return points, valid_coordinates