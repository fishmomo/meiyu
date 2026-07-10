"""Pipeline entrypoint."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from nc_compat import open_dataset_compat
from pipeline.core.cra40_fields import read_cra40_profile_cube
from pipeline.core.cra40_fields import resolve_cra40_profile_input
from pipeline.core.paths import ensure_case_dirs
from pipeline.manifest_loader import build_runtime_config
from pipeline.steps.geometry import build_geometry_from_mask
from pipeline.steps.inventory import build_inventory_report
from pipeline.steps.masks import resolve_case_masks
from pipeline.steps.profiles import build_profile_bundle_from_field
from pipeline.steps.diagnostics import write_front_diagnostics
from pipeline.steps.statistics import build_masked_mean
from pipeline.steps.subareas import build_subarea_mask


def _validate_supported_case(cfg) -> None:
    if cfg.dataset != "cra40":
        raise ValueError("runner only supports CRA40 dataset in this version")
    if cfg.front_id not in ("front1", "front2"):
        raise ValueError("runner only supports front1/front2 in this version")
    try:
        masks = resolve_case_masks(cfg.front_id, cfg.target_time)
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(
            f"no mask assets found for {cfg.front_id} at {cfg.target_time}: {exc}"
        ) from exc
    if not masks:
        raise ValueError(f"no mask assets found for {cfg.front_id} at {cfg.target_time}")
    profile_variables = _get_profile_variables(cfg)
    if cfg.front_id == "front2" and "rh" not in profile_variables:
        raise ValueError("front2 requires at least 'rh' profile variable")
    if cfg.front_id == "front1" and not set(profile_variables).issubset({"rh", "temp", "w"}):
        raise ValueError("front1 only supports rh/temp/w profile variables")


def _validate_supported_profile_variables(cfg: Any) -> list[str]:
    variables = _get_profile_variables(cfg)
    if cfg.front_id == "front2" and "rh" not in variables:
        raise ValueError("front2 runner requires at least 'rh' profile variable")
    if cfg.front_id == "front1" and not set(variables).issubset({"rh", "temp", "w"}):
        raise ValueError("front1 runner only supports rh/temp/w profile variables")
    return variables


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


def _get_profile_variables(cfg: Any) -> list[str]:
    profiles = getattr(cfg, "profiles", None)
    variables = getattr(profiles, "variables", None) if profiles is not None else None
    if variables:
        return [str(variable) for variable in variables]

    profile_variables = getattr(cfg, "profile_variables", [])
    if profile_variables:
        return [str(profile_variables[0])]

    raise ValueError("runner requires at least one profile variable")


def _get_profile_input_path(cfg: Any, variable: str) -> Path:
    resolved_inputs = getattr(cfg, "resolved_inputs", None)
    if resolved_inputs is not None:
        if variable not in resolved_inputs:
            raise ValueError(
                f"manifest is missing explicit input for profile variable: {variable}"
            )
        return Path(resolved_inputs[variable])

    return resolve_cra40_profile_input(variable, cfg.target_time)


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


def _completed_profiles_summary(
    profile_summaries: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "enabled": True,
        "status": "completed",
        "variables": profile_summaries,
    }


def _completed_statistics_summary(
    statistics_by_variable: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "enabled": True,
        "status": "completed",
        "variables": statistics_by_variable,
    }


def _partial_statistics_summary(
    statistics_by_variable: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "enabled": True,
        "status": "partial",
        "variables": statistics_by_variable,
    }


def run_case_from_manifest(
    path: Path,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    return run_case(build_runtime_config(path, overrides=overrides))


def _parse_override_value(text: str) -> object:
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    try:
        return int(text)
    except ValueError:
        pass

    try:
        return float(text)
    except ValueError:
        return text


def _parse_override_pairs(pairs: list[str] | None) -> dict[str, object]:
    overrides: dict[str, object] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"override must use key=value format, got: {pair}")
        key, value = pair.split("=", 1)
        overrides[key] = _parse_override_value(value)
    return overrides


class _CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            raise ValueError(message.strip())
        raise ValueError(
            f"argument parsing failed with status {status}"
        )


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _CliArgumentParser(
            description="Run the verified Meiyu pipeline case",
        )
        parser.add_argument("--manifest", required=True)
        parser.add_argument("--override", action="append", default=[])
        args = parser.parse_args(argv)

        overrides = _parse_override_pairs(args.override)
        summary = run_case_from_manifest(
            Path(args.manifest),
            overrides=overrides,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def run_case(cfg) -> dict[str, object]:
    _validate_supported_case(cfg)
    profile_variables = _validate_supported_profile_variables(cfg)

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

    field_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    if profiles_enabled or statistics_enabled:
        for variable in profile_variables:
            input_path = _get_profile_input_path(cfg, variable)
            field_cache[variable] = read_cra40_profile_cube(
                variable,
                input_path,
                lats,
                lons,
            )

    profile_bundle_cache: dict[str, object] = {}
    if profiles_enabled:
        profile_summaries: dict[str, dict[str, object]] = {}
        for variable in profile_variables:
            field3d, levels = field_cache[variable]
            profile_bundle = build_profile_bundle_from_field(
                variable,
                field3d,
                levels,
                lats,
                lons,
                geometry,
            )
            profile_bundle_cache[variable] = profile_bundle
            profile_summaries[variable] = {
                "bundle_shape": list(profile_bundle.values.shape),
                "status": "completed",
            }
        profiles_summary = _completed_profiles_summary(profile_summaries)
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
        statistics_by_variable: dict[str, dict[str, object]] = {}
        for variable in profile_variables:
            field3d, _ = field_cache[variable]
            statistics_by_variable[variable] = {
                "front_mean": float(build_masked_mean(variable, field3d[0], mask_bool)),
            }
        if subareas_enabled:
            for variable in profile_variables:
                field3d, _ = field_cache[variable]
                statistics_by_variable[variable]["subarea_mean"] = float(
                    build_masked_mean(variable, field3d[0], submask)
                )
            statistics_summary = _completed_statistics_summary(statistics_by_variable)
        else:
            for variable_summary in statistics_by_variable.values():
                variable_summary["subarea_mean"] = None
                variable_summary["subarea_status"] = "skipped"
            statistics_summary = _partial_statistics_summary(statistics_by_variable)
    else:
        statistics_summary = _skipped_summary()

    diagnostics_enabled = _is_step_enabled(cfg, "diagnostics")
    if diagnostics_enabled and profiles_enabled and profile_bundle_cache:
        figure_paths = write_front_diagnostics(
            cfg.case_name,
            output_dirs["diagnostics"],
            geometry,
            profile_bundle_cache,
            statistics_summary,
        )
        diagnostics_summary = {"enabled": True, "status": "completed", "files": figure_paths}
    else:
        diagnostics_summary = _skipped_summary()

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
        "diagnostics": diagnostics_summary,
    }


if __name__ == "__main__":
    raise SystemExit(main())
