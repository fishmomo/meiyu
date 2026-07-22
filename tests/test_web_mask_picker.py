import numpy as np
import xarray as xr
from io import BytesIO

from web_mask_picker.app import build_mask_dataset


def test_exported_mask_preserves_source_grid():
    source = xr.Dataset(
        {"thetae_gradient": (("lat", "lon"), np.ones((2, 3)))},
        coords={"lat": [35.0, 34.75], "lon": [110.0, 110.25, 110.5]},
    )
    result = build_mask_dataset(source, "thetae_gradient", {}, np.array([[1, 0, 1], [0, 1, 0]]))
    assert result.meiyu_front_mask.dtype == bool
    assert result.meiyu_front_mask.shape == (2, 3)
    np.testing.assert_array_equal(result.lat, source.lat)
    np.testing.assert_array_equal(result.lon, source.lon)


def test_exported_mask_round_trips_as_netcdf():
    source = xr.Dataset({"x": (("lat", "lon"), np.zeros((1, 2)))}, coords={"lat": [30.0], "lon": [120.0, 121.0]})
    result = build_mask_dataset(source, "x", {}, np.array([[True, False]]))
    restored = xr.open_dataset(BytesIO(result.to_netcdf()))
    assert restored.meiyu_front_mask.values.tolist() == [[True, False]]
