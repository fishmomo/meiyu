from pathlib import Path

import pytest

from pipeline.core.cra40_fields import resolve_cra40_profile_input
from pipeline.manifest_loader import build_runtime_config
from pipeline.manifest_loader import load_manifest
from pipeline.config import load_case_config


def test_load_manifest_reads_verified_case_defaults():
    manifest = load_manifest(
        Path("manifests/cases/cra40_front2_20170622T18.yml")
    )
    assert manifest.case_name == "cra40_front2_20170622T18"
    assert manifest.dataset == "cra40"
    assert manifest.front_id == "front2"
    assert manifest.target_time == "2017-06-22T18"
    assert manifest.steps["geometry"] is True
    assert manifest.geometry.n_sections == 8
    assert manifest.profiles.variables == ["rh"]
    assert manifest.subareas.start_section == 1
    assert (
        manifest.inputs["rh"].logical_name
        == "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )


def test_build_runtime_config_allows_known_overrides():
    cfg = build_runtime_config(
        Path("manifests/cases/cra40_front2_20170622T18.yml"),
        overrides={
            "params.geometry.n_sections": 6,
            "params.subareas.start_section": 2,
        },
    )
    assert cfg.geometry.n_sections == 6
    assert cfg.subareas.start_section == 2


def test_build_runtime_config_rejects_unknown_override_key():
    with pytest.raises(ValueError, match="unknown override key"):
        build_runtime_config(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={"params.geometry.unknown": 1},
        )


def test_build_runtime_config_resolves_logical_input_name():
    cfg = build_runtime_config(
        Path("manifests/cases/cra40_front2_20170622T18.yml")
    )
    assert cfg.resolved_inputs["rh"].endswith(
        "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )


def test_resolve_cra40_profile_input_supports_front1_v1_variables():
    assert str(resolve_cra40_profile_input("rh")).endswith(
        "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )
    assert str(resolve_cra40_profile_input("temp")).endswith(
        "CRA40_TEM_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )
    assert str(resolve_cra40_profile_input("w")).endswith(
        "CRA40_VVP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )


def test_resolve_cra40_profile_input_rejects_unknown_variable():
    with pytest.raises(ValueError, match="unsupported CRA40 profile variable"):
        resolve_cra40_profile_input("thetae")


def test_build_runtime_config_resolves_cra40_profile_variables_from_mapping(
    tmp_path,
):
    manifest_path = tmp_path / "case.yml"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front1_manifest",
                "dataset: cra40",
                "front_id: front1",
                "target_time: 2017-06-22T18",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - rh",
                "      - temp",
                "      - w",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
                "inputs:",
                "  rh:",
                "    logical_name: CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
                "  temp:",
                "    logical_name: CRA40_TEM_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
                "  w:",
                "    logical_name: CRA40_VVP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
            ]
        ),
        encoding="utf-8",
    )

    cfg = build_runtime_config(manifest_path)

    assert cfg.resolved_inputs["rh"].endswith(
        "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )
    assert cfg.resolved_inputs["temp"].endswith(
        "CRA40_TEM_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )
    assert cfg.resolved_inputs["w"].endswith(
        "CRA40_VVP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )


def test_build_runtime_config_rejects_front1_profile_mapping_without_logical_name(
    tmp_path,
):
    manifest_path = tmp_path / "case.yml"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front1_missing_logical_name",
                "dataset: cra40",
                "front_id: front1",
                "target_time: 2017-06-22T18",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - temp",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
                "inputs:",
                "  temp:",
                "    logical_name:",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires explicit logical_name"):
        build_runtime_config(manifest_path)


def test_build_runtime_config_rejects_front1_profile_mapping_with_wrong_logical_name(
    tmp_path,
):
    manifest_path = tmp_path / "case.yml"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front1_wrong_logical_name",
                "dataset: cra40",
                "front_id: front1",
                "target_time: 2017-06-22T18",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - w",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
                "inputs:",
                "  w:",
                "    logical_name: CRA40_VVEL_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="logical_name mismatch"):
        build_runtime_config(manifest_path)


def test_build_runtime_config_does_not_apply_front1_mapping_to_other_fronts(
    tmp_path,
):
    manifest_path = tmp_path / "case.yml"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front2_temp_manifest",
                "dataset: cra40",
                "front_id: front2",
                "target_time: 2017-06-22T18",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - temp",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
                "inputs:",
                "  temp:",
                "    logical_name: CRA40_TEMP_FRONT2_CUSTOM.grib2",
            ]
        ),
        encoding="utf-8",
    )

    cfg = build_runtime_config(manifest_path)

    assert cfg.resolved_inputs["temp"].endswith("CRA40_TEMP_FRONT2_CUSTOM.grib2")


def test_build_runtime_config_applies_front1_mapping_to_all_supported_times(
    tmp_path,
):
    manifest_path = tmp_path / "case.yml"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front1_other_time_manifest",
                "dataset: cra40",
                "front_id: front1",
                "target_time: 2017-06-22T12",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - w",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
                "inputs:",
                "  w:",
                "    logical_name: CRA40_VVP_2017062212_GLB_0P25_HOUR_V1_0_0.grib2",
            ]
        ),
        encoding="utf-8",
    )

    cfg = build_runtime_config(manifest_path)

    assert cfg.resolved_inputs["w"].endswith(
        "CRA40_VVP_2017062212_GLB_0P25_HOUR_V1_0_0.grib2"
    )


def test_build_runtime_config_prefers_relative_input_path(tmp_path):
    manifest_path = tmp_path / "case.yml"
    relative_input = "tests/data/custom-input.grib2"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front2_custom",
                "dataset: cra40",
                "front_id: front2",
                "target_time: 2017-06-22T18",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - rh",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
                "inputs:",
                "  rh:",
                f"    relative_path: {relative_input}",
                "    logical_name: CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
            ]
        ),
        encoding="utf-8",
    )
    cfg = build_runtime_config(manifest_path)
    assert cfg.resolved_inputs["rh"].endswith("tests\\data\\custom-input.grib2")


def test_load_case_config_uses_manifest_shape_entry(tmp_path):
    manifest_path = tmp_path / "case.yml"
    manifest_path.write_text(
        "\n".join(
            [
                "case_name: cra40_front2_manifest",
                "dataset: cra40",
                "front_id: front2",
                "target_time: 2017-06-22T18",
                "steps:",
                "  inventory: true",
                "  masks: true",
                "  geometry: true",
                "  profiles: true",
                "  subareas: true",
                "  statistics: true",
                "params:",
                "  geometry:",
                "    degree: 4",
                "    dense_points: 1000",
                "    n_sections: 8",
                "    distance: 1.0",
                "    n_points: 9",
                "    delta_x: 0.1",
                "  profiles:",
                "    variables:",
                "      - rh",
                "  subareas:",
                "    start_section: 1",
                "    end_section: 4",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_case_config(manifest_path)
    assert cfg.case_name == "cra40_front2_manifest"
    assert cfg.dataset == "cra40"
    assert cfg.front_id == "front2"
    assert cfg.target_time == "2017-06-22T18"
    assert cfg.profile_variables == ["rh"]


def test_load_case_config_keeps_legacy_simple_config_even_with_params_key(
    tmp_path,
):
    legacy_path = tmp_path / "legacy.yml"
    legacy_path.write_text(
        "\n".join(
            [
                "case_name: legacy_case",
                "dataset: cra40",
                "front_id: front2",
                "target_time: 2017-06-22T18",
                "profile_variables:",
                "  - rh",
                "params: legacy-only-marker",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_case_config(legacy_path)
    assert cfg.case_name == "legacy_case"
    assert cfg.dataset == "cra40"
    assert cfg.front_id == "front2"
    assert cfg.target_time == "2017-06-22T18"
    assert cfg.profile_variables == ["rh"]
