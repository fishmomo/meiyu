from dataclasses import dataclass, field
from pathlib import Path

from pipeline.manifest_loader import _parse_yaml_subset, build_runtime_config


@dataclass(slots=True)
class PipelineCaseConfig:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    profile_variables: list[str] = field(default_factory=list)


def _parse_simple_yaml(path: Path) -> dict[str, object]:
    payload = _parse_yaml_subset(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"config must be a mapping: {path}")
    return payload


def _is_manifest_shape(parsed: dict[str, object]) -> bool:
    steps = parsed.get("steps")
    params = parsed.get("params")
    if not isinstance(steps, dict) or not isinstance(params, dict):
        return False
    geometry = params.get("geometry")
    profiles = params.get("profiles")
    subareas = params.get("subareas")
    if not isinstance(geometry, dict):
        return False
    if not isinstance(profiles, dict):
        return False
    if not isinstance(subareas, dict):
        return False
    required_geometry_keys = {
        "degree",
        "dense_points",
        "n_sections",
        "distance",
        "n_points",
        "delta_x",
    }
    return required_geometry_keys.issubset(geometry)


def load_case_config(path: Path) -> PipelineCaseConfig:
    parsed = _parse_simple_yaml(path)
    if _is_manifest_shape(parsed):
        runtime = build_runtime_config(path)
        return PipelineCaseConfig(
            case_name=runtime.case_name,
            dataset=runtime.dataset,
            front_id=runtime.front_id,
            target_time=runtime.target_time,
            profile_variables=list(runtime.profiles.variables),
        )
    return PipelineCaseConfig(
        case_name=str(parsed["case_name"]),
        dataset=str(parsed["dataset"]),
        front_id=str(parsed["front_id"]),
        target_time=str(parsed["target_time"]),
        profile_variables=list(parsed.get("profile_variables", [])),
    )
