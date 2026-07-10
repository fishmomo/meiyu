from pathlib import Path


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
STATIC_DIR = DATA_DIR / "static"

# 原始资料
RAW_ERA5_DIR = RAW_DIR / "era5"
RAW_CRA40_DIR = RAW_DIR / "cra40"

# 掩膜资料
MASK_DIR = INTERIM_DIR / "manual_masks"
ERA5_MASK_DIR = MASK_DIR / "era5"
CRA40_MASK_DIR = MASK_DIR / "cra40"

# 统计结果与图件输出
MASK_STATS_DIR = PROCESSED_DIR / "mask_statistics"
OUTPUT_DIR = BASE_DIR / "outputs"
LEGACY_FIGURE_DIR = OUTPUT_DIR / "legacy_figures"
ANIMATION_DIR = OUTPUT_DIR / "animations"

# 静态底图
CHINA_SHP_PATH = STATIC_DIR / "shapefiles" / "china" / "china.shp"


def ensure_dir(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def era5_file(filename: str) -> str:
    return str(RAW_ERA5_DIR / filename)


def cra40_glob(pattern: str) -> str:
    return str(RAW_CRA40_DIR / pattern)


def cra40_file(filename: str) -> str:
    return str(RAW_CRA40_DIR / filename)


def era5_front_mask(front_no: int, dt: str) -> str:
    return str(ERA5_MASK_DIR / f"front{front_no}" / f"{dt}.nc")


def find_era5_mask(dt: str) -> str:
    # 兼容旧脚本中“未区分锋面1/锋面2”的读法，优先返回存在的掩膜文件。
    for front_no in (1, 2):
        candidate = Path(era5_front_mask(front_no, dt))
        if candidate.exists():
            return str(candidate)
    return str(Path(era5_front_mask(1, dt)))


def cra40_front_mask(front_no: int, dt: str) -> str:
    return str(CRA40_MASK_DIR / f"front{front_no}" / f"{dt}.nc")


def cra40_front_extend(front_no: int, dt: str) -> str:
    if front_no == 1:
        return str(CRA40_MASK_DIR / "front1" / "extend" / f"{dt}.nc")
    return str(CRA40_MASK_DIR / "front2_extend" / f"{dt}.nc")


def cra40_front2_subarea(filename: str) -> str:
    return str(CRA40_MASK_DIR / "front2_subareas" / filename)


def cra40_front2_offset(filename: str) -> str:
    return str(CRA40_MASK_DIR / "front2_offset" / filename)


def mask_stats_glob(*parts: str) -> str:
    return str(MASK_STATS_DIR.joinpath(*parts))


def legacy_figure_path(*parts: str, filename: str) -> str:
    folder = LEGACY_FIGURE_DIR.joinpath(*parts)
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)


def animation_path(*parts: str, filename: str) -> str:
    folder = ANIMATION_DIR.joinpath(*parts)
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)
