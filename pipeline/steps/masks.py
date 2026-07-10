from pipeline.core.mask_ops import existing_cra40_front1_mask_assets, existing_cra40_front2_mask_assets


def resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]:
    if front_id == "front1":
        return existing_cra40_front1_mask_assets(target_time)
    if front_id == "front2":
        return existing_cra40_front2_mask_assets(target_time)
    raise ValueError(f"unsupported front id: {front_id}")
