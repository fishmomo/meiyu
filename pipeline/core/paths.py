from pathlib import Path

from project_paths import OUTPUT_DIR


def case_output_root(case_name: str) -> Path:
    return OUTPUT_DIR / "figures" / case_name


def ensure_case_dirs(case_name: str) -> dict[str, Path]:
    root = case_output_root(case_name)
    paths = {
        "root": root,
        "diagnostics": root / "diagnostics",
        "profiles": root / "profiles",
        "subareas": root / "subareas",
        "statistics": root / "statistics",
        "logs": OUTPUT_DIR / "logs",
        "manifests": OUTPUT_DIR / "manifests",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
