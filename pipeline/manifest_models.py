from dataclasses import dataclass, field


@dataclass(slots=True)
class ManifestInputRef:
    logical_name: str | None = None
    relative_path: str | None = None


@dataclass(slots=True)
class ManifestGeometryParams:
    degree: int
    dense_points: int
    n_sections: int
    distance: float
    n_points: int
    delta_x: float


@dataclass(slots=True)
class ManifestProfilesParams:
    variables: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ManifestSubareasParams:
    start_section: int
    end_section: int


@dataclass(slots=True)
class ManifestDiagnosticsParams:
    level_hpa: float = 850.0


@dataclass(slots=True)
class ManifestSpec:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    steps: dict[str, bool]
    geometry: ManifestGeometryParams
    profiles: ManifestProfilesParams
    subareas: ManifestSubareasParams
    diagnostics: ManifestDiagnosticsParams
    inputs: dict[str, ManifestInputRef]


@dataclass(slots=True)
class RunnerRuntimeConfig:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    steps: dict[str, bool]
    geometry: ManifestGeometryParams
    profiles: ManifestProfilesParams
    subareas: ManifestSubareasParams
    diagnostics: ManifestDiagnosticsParams
    resolved_inputs: dict[str, str]
