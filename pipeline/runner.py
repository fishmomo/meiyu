"""Pipeline entrypoint."""

from pathlib import Path
from typing import Any

import numpy as np

from nc_compat import open_dataset_compat
from pipeline.core.paths import ensure_case_dirs
from pipeline.manifest_loader import build_runtime_config
from pipeline.steps.geometry import build_geometry_from_mask
from pipeline.steps.inventory import build_inventory_report
from pipeline.steps.masks import resolve_case_masks
from pipeline.steps.profiles import build_profile_bundle_from_field
from pipeline.steps.statistics import build_masked_mean
from pipeline.steps.subareas import build_subarea_mask
from project_paths import cra40_file


def _validate_supported_case(cfg) -> None:
    if (
        cfg.dataset != "cra40"
        or cfg.front_id != "front2"
        or cfg.target_time != "2017-06-22T18"
    ):
        raise ValueError(
            "runner only supports the verified CRA40 front2 2017-06-22T18 pipeline in this version"
        )


def _validate_supported_profile_variable(cfg: Any) -> str:
    variable = _get_profile_variable(cfg)
    if variable != "rh":
        raise ValueError(
            "runner only supports the verified CRA40 front2 2017-06-22T18 rh pipeline in this version"
        )
    return variable


def _load_bool_mask(path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ds = open_dataset_compat(Path(path))
    return (
        ds["ind_area_bool"].values.astype(bool),
        ds["lon"].values,
        ds["lat"].values,
    )


def _get_geometry_param(cfg: Any, field: str, default: Any) -> Any:
    geometry = getattr(cfg, "geometry", None)
    if geometry is None:
        return default
    return getattr(geometry, field, default)


def _get_profile_variable(cfg: Any) -> str:
    profiles = getattr(cfg, "profiles", None)
    if profiles is not None and getattr(profiles, "variables", None):
        return str(profiles.variables[0])

    profile_variables = getattr(cfg, "profile_variables", [])
    if profile_variables:
        return str(profile_variables[0])

    raise ValueError("runner requires at least one profile variable")


def _get_profile_input_path(cfg: Any, variable: str) -> Path:
    resolved_inputs = getattr(cfg, "resolved_inputs", None)
    if resolved_inputs and variable in resolved_inputs:
        return Path(resolved_inputs[variable])

    if variable != "rh":
        raise ValueError(f"runner only supports the verified rh profile input, got: {variable}")

    return Path(cra40_file("CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"))


def _get_subarea_sections(cfg: Any) -> tuple[int, int]:
    subareas = getattr(cfg, "subareas", None)
    if subareas is None:
        return 1, 4
    return (
        int(getattr(subareas, "start_section", 1)),
        int(getattr(subareas, "end_section", 4)),
    )


def _is_step_enabled(cfg: Any, step_name: str) -> bool:
    steps = getattr(cfg, "steps", None)
    if not isinstance(steps, dict):
        return True
    return bool(steps.get(step_name, True))


def _skipped_summary() -> dict[str, object]:
    return {"enabled": False, "status": "skipped"}


def run_case_from_manifest(
    path: Path,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    return run_case(build_runtime_config(path, overrides=overrides))


def run_case(cfg) -> dict[str, object]:
    _validate_supported_case(cfg)
    profile_variable = _validate_supported_profile_variable(cfg)

    output_dirs = ensure_case_dirs(cfg.case_name)
    inventory = build_inventory_report()
    masks = resolve_case_masks(cfg.front_id, cfg.target_time)

    mask_bool, lons, lats = _load_bool_mask(masks["front_mask"])
    geometry = build_geometry_from_mask(
        mask_bool,
        lons,
        lats,
        degree=_get_geometry_param(cfg, "degree", 4),
        dense_points=_get_geometry_param(cfg, "dense_points", 1000),
        n_sections=_get_geometry_param(cfg, "n_sections", 8),
        distance=_get_geometry_param(cfg, "distance", 1.0),
        n_points=_get_geometry_param(cfg, "n_points", 9),
        delta_x=_get_geometry_param(cfg, "delta_x", 0.1),
    )

    start_section, end_section = _get_subarea_sections(cfg)
    profiles_enabled = _is_step_enabled(cfg, "profiles")
    subareas_enabled = _is_step_enabled(cfg, "subareas")
    statistics_enabled = _is_step_enabled(cfg, "statistics")

    rh_ds = None
    field3d = None
    levels = None
    if profiles_enabled or statistics_enabled:
        rh_path = _get_profile_input_path(cfg, profile_variable)
        rh_ds = open_dataset_compat(Path(rh_path))
        field3d = rh_ds["r"].isel(isobaricInhPa=slice(0, 37)).sel(
            latitude=lats,
            longitude=lons,
            method="nearest",
        ).values
        levels = rh_ds["isobaricInhPa"].isel(isobaricInhPa=slice(0, 37)).values

    if profiles_enabled:
        profile_bundle = build_profile_bundle_from_field(
            profile_variable,
            field3d,
            levels,
            lats,
            lons,
            geometry,
        )
        profiles_summary = {
            "variable": profile_bundle.variable,
            "bundle_shape": list(profile_bundle.values.shape),
            "status": "completed",
        }
    else:
        profiles_summary = _skipped_summary()

    if subareas_enabled:
        mask_lon2d, mask_lat2d = np.meshgrid(lons, lats)
        submask = build_subarea_mask(
            mask_lon2d,
            mask_lat2d,
            mask_bool,
            geometry,
            start_section=start_section,
            end_section=end_section,
        )
        subareas_summary = {
            "mask_shape": list(submask.shape),
            "selected_points": int(submask.sum()),
            "start_section": start_section,
            "end_section": end_section,
            "status": "completed",
        }
    else:
        subareas_summary = _skipped_summary()

    if statistics_enabled:
        front_mean = build_masked_mean(profile_variable, field3d[0], mask_bool)
        if subareas_enabled:
            subarea_mean = build_masked_mean(profile_variable, field3d[0], submask)
            statistics_summary = {
                "front_mean": float(front_mean),
                "subarea_mean": float(subarea_mean),
                "status": "completed",
            }
        else:
            statistics_summary = {
                "enabled": True,
                "status": "partial",
                "front_mean": float(front_mean),
                "subarea_mean": None,
                "subarea_status": "skipped",
            }
    else:
        statistics_summary = _skipped_summary()

    return {
        "case_name": cfg.case_name,
        "inventory": inventory,
        "masks": masks,
        "outputs": {key: str(value) for key, value in output_dirs.items()},
        "geometry": {
            "centerline_points": int(geometry.centerline_x.shape[0]),
            "section_shape": list(geometry.sampled_dx.shape),
        },
        "profiles": profiles_summary,
        "subareas": subareas_summary,
        "statistics": statistics_summary,
    }
