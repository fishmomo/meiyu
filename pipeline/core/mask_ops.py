from pathlib import Path

from pipeline.core.time_utils import cra40_front2_subarea_time_token
from project_paths import cra40_front_extend, cra40_front_mask, cra40_front2_subarea

CRA40_FRONT1_V1_TARGET_TIME = "2017-06-22T18"


def _require_existing(path: str) -> str:
    if not Path(path).exists():
        raise FileNotFoundError(path)
    return path


def _require_front1_v1_target_time(target_time: str) -> None:
    if target_time != CRA40_FRONT1_V1_TARGET_TIME:
        raise ValueError(
            f"CRA40 front1 V1 only supports {CRA40_FRONT1_V1_TARGET_TIME}: {target_time}"
        )


def existing_cra40_front1_mask_assets(target_time: str) -> dict[str, str]:
    _require_front1_v1_target_time(target_time)
    return {
        "front_mask": _require_existing(cra40_front_mask(1, target_time)),
        "extend_mask": _require_existing(cra40_front_extend(1, target_time)),
    }


def existing_cra40_front2_mask_assets(target_time: str) -> dict[str, str]:
    compact_label = cra40_front2_subarea_time_token(target_time)
    return {
        "front_mask": _require_existing(cra40_front_mask(2, target_time)),
        "extend_mask": _require_existing(cra40_front_extend(2, target_time)),
        "subarea_mask": _require_existing(
            cra40_front2_subarea(f"area2_lonlat_{compact_label}.nc")
        ),
    }
