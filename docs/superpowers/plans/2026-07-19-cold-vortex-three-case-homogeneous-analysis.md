# Cold-vortex three-case homogeneous analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the completed September 2021 case as a traceable text record, then run the same core-boundary, position, and conditional-intensity diagnostics for August 2017 and November 2021.

**Architecture:** Event-track CSV and NPZ masks remain the sole source of cold-vortex core geometry. Each event receives an independent 0.25-degree CRA40 diagnostic-level cropped dataset, then the existing lifecycle and coupling code produces event-scoped CSV and PNG outputs. The September Markdown records evidence and limits without extrapolating to a water budget.

**Tech Stack:** Python 3.12, NumPy, xarray/cfgrib, matplotlib, CRA40 GRIB2, NetCDF4, pytest.

## Global Constraints

- Use the existing 90–170E, 20–70N 0.25-degree cropped CRA40 research-data convention.
- Use tracked `core_body` masks only; do not introduce an arbitrary peripheral window.
- Keep the diagnostic scope to circulation, 850-hPa moisture-flux convergence, and 700-hPa pressure vertical velocity; do not infer precipitation or a closed water budget.
- Preserve unrelated workspace changes.

---

### Task 1: Make coupling diagnostics event-selectable

**Files:**
- Modify: `quantify_cold_vortex_coupling.py`
- Test: `tests/test_cold_vortex_diagnostics.py`

- [x] **Step 1: Write a failing test** for `event_paths("2021_november")`, expecting the returned track and output paths to end with that event name.
- [x] **Step 2: Run the single test** with `python -m pytest tests/test_cold_vortex_diagnostics.py -q -p no:cacheprovider`; expect an import failure for `event_paths`.
- [x] **Step 3: Implement** `event_paths(event: str) -> tuple[Path, Path]`, pass event-specific paths through `main(event)`, and add `--event` choices for the three tracked cases.
- [x] **Step 4: Run the test suite**; expect all tests to pass.

### Task 2: Build missing formal diagnostic-level datasets

**Files:**
- Create: `data/derived/cra40_cold_vortex_90E170E_20N70N/diagnostic_levels/2017_august_east/*.nc`
- Create: `data/derived/cra40_cold_vortex_90E170E_20N70N/diagnostic_levels/2021_november/*.nc`

- [x] **Step 1: Run** `build_cold_vortex_research_dataset.py --event 2017_august_east --event 2021_november --diagnostic-levels`.
- [x] **Step 2: Verify** one output file per time in each event-track CSV, and verify each file has the expected event directory and NetCDF suffix.

### Task 3: Run homogeneous lifecycle and coupling diagnostics

**Files:**
- Create: `data/processed/cold_vortex/event_diagnostics/2017_august_east/*`
- Create: `data/processed/cold_vortex/event_diagnostics/2021_november/*`

- [x] **Step 1: Run** `run_cold_vortex_diagnostics.py --event 2017_august_east --event 2021_november` to create lifecycle CSVs and three-stage structural maps.
- [x] **Step 2: Run** `quantify_cold_vortex_coupling.py --event 2017_august_east --event 2021_november` to create coverage, centroid, separation, and conditional-intensity products.
- [x] **Step 3: Inspect** each event's CSV headers, row count, and intensity PNG for valid values and a continuous time axis.

### Task 4: Preserve the September case as research text material

**Files:**
- Create: `docs/cold_vortex_cases/2021_september_descriptive_diagnosis.md`

- [x] **Step 1: Write** the dataset, core-boundary, and diagnostic definitions used in the September case.
- [x] **Step 2: Record** observed lifecycle, coverage/centroid/separation, and conditional-intensity findings with explicit numerical evidence.
- [x] **Step 3: State** the supported interpretation and the boundary that no precipitation, evaporation, or vertically integrated water-budget conclusion is made.

### Task 5: Final verification

**Files:**
- Verify: `tests/test_cold_vortex_diagnostics.py`
- Verify: all three `data/processed/cold_vortex/event_diagnostics/<event>/` directories.

- [x] **Step 1: Run** `python -m pytest tests/test_cold_vortex_diagnostics.py -q -p no:cacheprovider`; expect all tests to pass.
- [x] **Step 2: Report** generated Markdown, cropped-data batches, diagnostic outputs, and any observed cross-case contrasts without making cross-case causal claims before review.
