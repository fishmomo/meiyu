from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from pipeline.manifest_models import (
    ManifestGeometryParams,
    ManifestInputRef,
    ManifestProfilesParams,
    ManifestSpec,
    ManifestSubareasParams,
    RunnerRuntimeConfig,
)
from project_paths import cra40_file


ALLOWED_OVERRIDE_KEYS = {
    "steps.profiles",
    "steps.subareas",
    "steps.statistics",
    "params.geometry.n_sections",
    "params.geometry.delta_x",
    "params.subareas.start_section",
    "params.subareas.end_section",
    "params.profiles.variables",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_manifest(path: Path) -> ManifestSpec:
    parsed = _parse_manifest_yaml(path)
    return ManifestSpec(
        case_name=str(parsed["case_name"]),
        dataset=str(parsed["dataset"]),
        front_id=str(parsed["front_id"]),
        target_time=str(parsed["target_time"]),
        steps={key: bool(value) for key, value in parsed["steps"].items()},
        geometry=ManifestGeometryParams(**parsed["params"]["geometry"]),
        profiles=ManifestProfilesParams(
            variables=list(parsed["params"]["profiles"]["variables"])
        ),
        subareas=ManifestSubareasParams(**parsed["params"]["subareas"]),
        inputs={
            key: ManifestInputRef(
                logical_name=value.get("logical_name"),
                relative_path=value.get("relative_path"),
            )
            for key, value in parsed.get("inputs", {}).items()
        },
    )


def build_runtime_config(
    path: Path,
    overrides: dict[str, object] | None = None,
) -> RunnerRuntimeConfig:
    manifest = load_manifest(path)
    data = _manifest_to_mutable_dict(manifest)
    _apply_overrides(data, overrides or {})
    resolved_inputs = {
        key: _resolve_input_path(data["dataset"], ref)
        for key, ref in manifest.inputs.items()
    }
    return RunnerRuntimeConfig(
        case_name=str(data["case_name"]),
        dataset=str(data["dataset"]),
        front_id=str(data["front_id"]),
        target_time=str(data["target_time"]),
        steps={key: bool(value) for key, value in data["steps"].items()},
        geometry=ManifestGeometryParams(**data["params"]["geometry"]),
        profiles=ManifestProfilesParams(
            variables=list(data["params"]["profiles"]["variables"])
        ),
        subareas=ManifestSubareasParams(**data["params"]["subareas"]),
        resolved_inputs=resolved_inputs,
    )


def _parse_manifest_yaml(path: Path) -> dict[str, Any]:
    payload = _parse_yaml_subset(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a mapping: {path}")
    return payload


def _manifest_to_mutable_dict(manifest: ManifestSpec) -> dict[str, Any]:
    return {
        "case_name": manifest.case_name,
        "dataset": manifest.dataset,
        "front_id": manifest.front_id,
        "target_time": manifest.target_time,
        "steps": deepcopy(manifest.steps),
        "params": {
            "geometry": {
                "degree": manifest.geometry.degree,
                "dense_points": manifest.geometry.dense_points,
                "n_sections": manifest.geometry.n_sections,
                "distance": manifest.geometry.distance,
                "n_points": manifest.geometry.n_points,
                "delta_x": manifest.geometry.delta_x,
            },
            "profiles": {
                "variables": list(manifest.profiles.variables),
            },
            "subareas": {
                "start_section": manifest.subareas.start_section,
                "end_section": manifest.subareas.end_section,
            },
        },
    }


def _apply_overrides(data: dict[str, Any], overrides: dict[str, object]) -> None:
    for key, value in overrides.items():
        if key not in ALLOWED_OVERRIDE_KEYS:
            raise ValueError(f"unknown override key: {key}")
        cursor: Any = data
        parts = key.split(".")
        for part in parts[:-1]:
            cursor = cursor[part]
        cursor[parts[-1]] = value


def _resolve_input_path(dataset: str, ref: ManifestInputRef) -> str:
    if ref.relative_path:
        return str((PROJECT_ROOT / ref.relative_path).resolve())
    if ref.logical_name:
        if dataset != "cra40":
            raise ValueError(f"unsupported dataset for logical_name: {dataset}")
        return cra40_file(ref.logical_name)
    raise ValueError("input reference must define relative_path or logical_name")


def _parse_yaml_subset(text: str) -> Any:
    lines = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append((len(raw_line) - len(raw_line.lstrip(" ")), raw_line.rstrip()))
    if not lines:
        return {}
    value, next_index = _parse_block(lines, 0, lines[0][0])
    if next_index != len(lines):
        raise ValueError("unexpected trailing content in yaml subset")
    return value


def _parse_block(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    if lines[index][1].lstrip().startswith("- "):
        items: list[Any] = []
        while index < len(lines):
            line_indent, raw_line = lines[index]
            if line_indent < indent:
                break
            if line_indent != indent or not raw_line.lstrip().startswith("- "):
                raise ValueError("invalid list indentation in yaml subset")
            item_text = raw_line.lstrip()[2:].strip()
            items.append(_parse_scalar(item_text))
            index += 1
        return items, index

    mapping: dict[str, Any] = {}
    while index < len(lines):
        line_indent, raw_line = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent:
            raise ValueError("invalid mapping indentation in yaml subset")
        content = raw_line.strip()
        if ":" not in content:
            raise ValueError(f"invalid yaml line: {raw_line}")
        key, value_text = content.split(":", 1)
        value_text = value_text.strip()
        index += 1
        if value_text:
            mapping[key] = _parse_scalar(value_text)
            continue
        if index >= len(lines) or lines[index][0] <= line_indent:
            mapping[key] = {}
            continue
        nested_value, index = _parse_block(lines, index, lines[index][0])
        mapping[key] = nested_value
    return mapping, index


def _parse_scalar(value: str) -> Any:
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
