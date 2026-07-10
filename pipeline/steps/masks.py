from pipeline.core.mask_ops import existing_cra40_front2_mask_assets


def resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]:
    if front_id != "front2":
        raise ValueError(f"Task 4 only supports CRA40 manual masks for front2: {front_id}")
    return existing_cra40_front2_mask_assets(target_time)
