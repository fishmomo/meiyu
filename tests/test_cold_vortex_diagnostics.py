import numpy as np
from pathlib import Path


def test_area_weighted_mean_uses_only_core_cells():
    from cold_vortex_diagnostics import area_weighted_mean

    field = np.array([[1.0, 2.0], [100.0, 200.0]])
    core = np.array([[True, True], [False, False]])
    area = np.array([[1.0, 3.0], [5.0, 7.0]])

    assert area_weighted_mean(field, core, area) == 1.75


def test_core_summary_keeps_moisture_flux_convergence_sign():
    from cold_vortex_diagnostics import core_summary

    core = np.array([[True, True], [False, False]])
    area = np.ones((2, 2))
    summary = core_summary(
        core_mask=core,
        cell_area_km2=area,
        fields={
            "z500_gpm": np.array([[5500.0, 5510.0], [5520.0, 5530.0]]),
            "mfc850_kg_kg_m_s_inv": np.array([[2e-7, 4e-7], [8e-7, 16e-7]]),
        },
    )

    assert summary["core_area_km2"] == 2.0
    assert summary["z500_gpm"] == 5505.0
    assert summary["mfc850_kg_kg_m_s_inv"] == 3e-7


def test_moisture_flux_convergence_is_positive_for_convergent_flow():
    from cold_vortex_diagnostics import moisture_flux_convergence

    latitude = np.linspace(40.0, 42.0, 9)
    longitude = np.linspace(110.0, 112.0, 9)
    lon2d, lat2d = np.meshgrid(np.deg2rad(longitude), np.deg2rad(latitude))
    u = -(lon2d - lon2d.mean())
    v = -(lat2d - lat2d.mean())

    mfc = moisture_flux_convergence(
        specific_humidity=np.full_like(u, 0.01),
        u=u,
        v=v,
        latitude=latitude,
        longitude=longitude,
        earth_radius_m=1.0,
    )

    assert np.nanmean(mfc[1:-1, 1:-1]) > 0.0


def test_subset_cache_path_is_event_and_time_specific():
    from cold_vortex_subset import subset_cache_path

    root = Path("cache")
    path = subset_cache_path(root, "2021_september", "2021090818")

    assert path == root / "2021_september" / "2021090818_domain_90E_170E_20N_70N.npz"


def test_research_dataset_path_is_a_netcdf_file():
    from cold_vortex_research_data import research_dataset_path

    path = research_dataset_path(Path("derived"), "2021_september", "2021090818")

    assert path == Path("derived") / "2021_september" / "CRA40_2021090818_0P25_90E170E_20N70N.nc"


def test_centroid_separation_is_normalized_by_core_radius():
    from quantify_cold_vortex_coupling import centroid_separation

    separation_km, separation_radius = centroid_separation(
        mfc_latitude=40.0,
        mfc_longitude=110.0,
        ascent_latitude=40.0,
        ascent_longitude=111.0,
        core_equivalent_radius_km=100.0,
    )

    assert 84.0 < separation_km < 86.0
    assert 0.84 < separation_radius < 0.86


def test_conditional_area_weighted_mean_uses_only_selected_cells():
    from quantify_cold_vortex_coupling import conditional_area_weighted_mean

    value = conditional_area_weighted_mean(
        field=np.array([[2.0, 6.0], [10.0, 14.0]]),
        condition=np.array([[True, False], [True, False]]),
        area=np.array([[1.0, 1.0], [3.0, 1.0]]),
    )

    assert value == 8.0


def test_coupling_event_paths_are_event_specific():
    from quantify_cold_vortex_coupling import event_paths

    track_dir, output_dir = event_paths("2021_november")

    assert track_dir.name == "2021_november"
    assert output_dir.name == "2021_november"


def test_diagnostic_level_dataset_is_selected_when_full_dataset_is_absent(tmp_path):
    from cold_vortex_research_data import diagnostic_dataset_path
    from run_cold_vortex_diagnostics import cropped_dataset_path

    diagnostic = diagnostic_dataset_path(tmp_path, "2021_november", "2021110712")
    diagnostic.parent.mkdir(parents=True)
    diagnostic.touch()

    assert cropped_dataset_path(tmp_path, "2021_november", "2021110712") == diagnostic


def test_circulation_crop_keeps_source_tree_and_replaces_grib_suffix():
    from crop_cra40_global_grib_to_china import china_output_path

    source_root = Path("E:/data")
    target_root = Path("data/raw/cra40/cold_vortex_china_circulation_70p125E_165p125E_14p875N_80p125N")
    source = source_root / "2021" / "20210707" / "CRA40_GPH_2021070700_GLB_0P25_HOUR_V1_0_0.grib2"

    assert china_output_path(source, source_root, target_root) == (
        target_root / "2021" / "20210707" / "CRA40_GPH_2021070700_CHN_0P25_HOUR_V1_0_0.nc"
    )


def test_circulation_crop_selects_exact_bounds_with_descending_latitude():
    import xarray as xr
    from crop_cra40_global_grib_to_china import select_china_domain

    dataset = xr.Dataset(
        {"gh": (("latitude", "longitude"), np.zeros((4, 5)))},
        coords={"latitude": [85.0, 80.0, 15.0, 10.0], "longitude": [70.0, 70.25, 165.0, 165.25, 170.0]},
    )
    cropped = select_china_domain(dataset)

    assert cropped.latitude.values.tolist() == [80.0, 15.0]
    assert cropped.longitude.values.tolist() == [70.25, 165.0]


def test_china_crop_job_keeps_the_source_path_in_its_result(monkeypatch):
    from crop_cra40_global_grib_to_china import crop_one_job

    source = Path("E:/data/2021/20210707/test.grib2")
    monkeypatch.setattr(
        "crop_cra40_global_grib_to_china.crop_one",
        lambda *args, **kwargs: ("written", Path("out.nc")),
    )

    assert crop_one_job((source, Path("E:/data"), Path("target"), False)) == (source, "written", Path("out.nc"))


def test_netcdf_ascii_staging_is_removed_after_copy_back_to_project():
    import xarray as xr
    from nc_compat import _staged_name, to_netcdf_compat

    target = Path.cwd() / "data" / ".tmp_staging_cleanup_test.nc"
    staged = _staged_name(target)
    target.unlink(missing_ok=True)
    staged.unlink(missing_ok=True)
    dataset = xr.Dataset({"x": ("point", [1.0, 2.0])})
    try:
        to_netcdf_compat(dataset, target, engine="netcdf4")
        assert target.exists()
        assert not staged.exists()
    finally:
        dataset.close()
        target.unlink(missing_ok=True)
        staged.unlink(missing_ok=True)


def test_xarray_staging_uses_the_project_drive_not_system_c_drive():
    from nc_compat import TMP_ROOT

    assert TMP_ROOT.drive.upper() == Path.cwd().drive.upper()
    assert TMP_ROOT.name == "meiyu_new_xarray_cache"


def test_crop_runtime_temp_root_uses_the_project_drive():
    from crop_cra40_global_grib_to_china import runtime_temp_root

    assert runtime_temp_root(Path.cwd()).drive.upper() == Path.cwd().drive.upper()


def test_resolution_filter_keeps_only_matching_cra40_files(tmp_path):
    from crop_cra40_global_grib_to_china import filter_by_resolution

    files = [
        tmp_path / "CRA40_GPH_2020010100_GLB_2P50_HOUR_V1_0_0.grib2",
        tmp_path / "CRA40_GPH_2020010100_GLB_0P25_HOUR_V1_0_0.grib2",
    ]

    assert filter_by_resolution(files, "2P50") == [files[0]]
    assert filter_by_resolution(files, "0P25") == [files[1]]


def test_land_precipitation_crop_rebuilds_descending_latitude_grid():
    from crop_cra40_global_grib_to_china import crop_land_precipitation_values

    values = np.arange(720 * 1440, dtype=float).reshape(720, 1440)
    cropped = crop_land_precipitation_values(values)

    assert cropped.shape == (262, 381)
    assert cropped.latitude.values[[0, -1]].tolist() == [80.125, 14.875]
    assert cropped.longitude.values[[0, -1]].tolist() == [70.125, 165.125]
    assert cropped.values[0, 0] == values[39, 280]


def test_common_cropped_data_path_is_variable_and_time_specific(tmp_path):
    from cold_vortex_common_data import cropped_field_path

    path = tmp_path / "2019" / "20190424" / "CRA40_GPH_2019042400_CHN_0P25_HOUR_V1_0_0.nc"
    path.parent.mkdir(parents=True)
    path.touch()

    assert cropped_field_path(tmp_path, "GPH", "2019042400") == path


def test_track_records_restores_a_single_six_hour_gap():
    from build_remaining_cold_vortex_cases import track_records

    rows = [
        {"time_utc": "2020010100", "strict_closed_40gpm": "True", "center_latitude_deg_n": "50", "center_longitude_deg_e": "120"},
        {"time_utc": "2020010106", "strict_closed_40gpm": "False"},
        {"time_utc": "2020010112", "strict_closed_40gpm": "True", "center_latitude_deg_n": "52.5", "center_longitude_deg_e": "125"},
    ]

    tracks = track_records(rows)
    assert len(tracks) == 1
    assert [record["time_utc"] for record in tracks[0]] == ["2020010100", "2020010112"]


def test_continuous_event_inherits_one_missing_closed_body_and_adds_terminal_time():
    from finalize_cold_vortex_tracks import continuous_event

    rows = [
        {"track_id": "track", "time_utc": "2020010100", "status": "observed_closed", "refined_center_latitude_deg_n": "50", "refined_center_longitude_deg_e": "120", "refined_center_z500_gpm": "5500", "outermost_closed_contour_gpm": "5560"},
        {"track_id": "track", "time_utc": "2020010106", "status": "no_high_resolution_closed_body", "refined_center_latitude_deg_n": "49.5", "refined_center_longitude_deg_e": "121", "refined_center_z500_gpm": "5505", "outermost_closed_contour_gpm": ""},
        {"track_id": "track", "time_utc": "2020010112", "status": "observed_closed", "refined_center_latitude_deg_n": "49", "refined_center_longitude_deg_e": "122", "refined_center_z500_gpm": "5510", "outermost_closed_contour_gpm": "5560"},
        {"track_id": "track", "time_utc": "2020010118", "status": "observed_closed", "refined_center_latitude_deg_n": "48.5", "refined_center_longitude_deg_e": "123", "refined_center_z500_gpm": "5515", "outermost_closed_contour_gpm": "5560"},
        {"track_id": "track", "time_utc": "2020010200", "status": "observed_closed", "refined_center_latitude_deg_n": "48", "refined_center_longitude_deg_e": "124", "refined_center_z500_gpm": "5520", "outermost_closed_contour_gpm": "5560"},
        {"track_id": "track", "time_utc": "2020010206", "status": "observed_closed", "refined_center_latitude_deg_n": "47.5", "refined_center_longitude_deg_e": "125", "refined_center_z500_gpm": "5525", "outermost_closed_contour_gpm": "5560"},
    ]
    masks = {("track", stamp): np.array([[True, False], [False, False]]) for stamp in ["2020010100", "2020010112", "2020010118", "2020010200", "2020010206"]}
    records, result_masks = continuous_event(rows, masks, np.array([50.0, 49.5]), np.array([120.0, 121.0]), "event")

    assert [record["region_method"] for record in records] == ["observed_closed", "inherited_translated", "observed_closed", "observed_closed", "observed_closed", "observed_closed", "terminal_inherited_translated"]
    assert records[-1]["time_utc"] == "2020010212"
    assert result_masks[1].any()


def test_independent_tracks_discards_a_contained_duplicate_track():
    from finalize_cold_vortex_tracks import independent_tracks

    rows = [
        {"track_id": "short", "time_utc": "2020010100", "refined_center_latitude_deg_n": "50", "refined_center_longitude_deg_e": "120"},
        {"track_id": "short", "time_utc": "2020010106", "refined_center_latitude_deg_n": "49", "refined_center_longitude_deg_e": "121"},
        {"track_id": "long", "time_utc": "2020010100", "refined_center_latitude_deg_n": "50", "refined_center_longitude_deg_e": "120"},
        {"track_id": "long", "time_utc": "2020010106", "refined_center_latitude_deg_n": "49", "refined_center_longitude_deg_e": "121"},
        {"track_id": "long", "time_utc": "2020010112", "refined_center_latitude_deg_n": "48", "refined_center_longitude_deg_e": "122"},
    ]

    tracks = independent_tracks(rows)
    assert len(tracks) == 1
    assert tracks[0][0]["track_id"] == "long"
