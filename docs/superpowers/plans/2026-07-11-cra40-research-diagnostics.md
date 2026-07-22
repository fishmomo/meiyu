# CRA40 Research Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CRA40 legacy-style research diagnostics to single-case runner output.

**Architecture:** Extend `pipeline.steps.diagnostics` with array-driven plotting helpers and call them from `pipeline.runner` only for CRA40 cases. Keep scientific computation in runner/core outputs unchanged; diagnostics consume existing masks, geometry, subareas, and field caches.

**Tech Stack:** Python, NumPy, Matplotlib Agg, MetPy, pygrib, existing `nc_compat` and `project_paths`.

## Global Constraints

- First version targets CRA40 only.
- Existing minimal diagnostics must continue to be produced.
- New diagnostics must be optional; missing optional inputs must not break non-CRA40 cases.
- No ERA5 generalization in this version.

---

### Task 1: Add Array-Driven Research Diagnostic Tests

**Files:**
- Modify: `tests/test_diagnostics_step.py`

**Interfaces:**
- Consumes: `GeometryResult`, `ProfileBundle`
- Produces expected API: `write_cra40_research_diagnostics(case_name, output_dir, geometry, mask_bool, lons, lats, submask, profile_bundles, field_cache)`

- [ ] Write failing tests asserting the CRA40 research helper emits overlay, section, and combined-section PNG files from synthetic arrays.
- [ ] Run `conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -v` and confirm failure because the helper is missing.

### Task 2: Implement CRA40 Research Diagnostic Helper

**Files:**
- Modify: `pipeline/steps/diagnostics.py`

**Interfaces:**
- Produces: `write_cra40_research_diagnostics(...) -> list[str]`

- [ ] Implement map overlay helpers for theta-e gradient, precipitation, and subarea relationship.
- [ ] Implement per-variable all-section profile panel plots.
- [ ] Implement RH+theta-e and W+theta-e combined section panel plots.
- [ ] Run `conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -v` and confirm pass.

### Task 3: Connect Runner CRA40 Inputs

**Files:**
- Modify: `pipeline/runner.py`
- Modify: `tests/test_runner_step.py`

**Interfaces:**
- Consumes: `field_cache`, `profile_bundle_cache`, `submask`, `mask_bool`, `geometry`
- Produces: diagnostics summary including new research PNG files for CRA40 runs

- [ ] Add runner test expecting a CRA40 run to include at least the first-version research diagnostic filenames.
- [ ] Run the targeted runner test and confirm failure.
- [ ] Call `write_cra40_research_diagnostics(...)` in the diagnostics block for `cfg.dataset == "cra40"`.
- [ ] Run targeted runner tests and confirm pass.

### Task 4: Smoke the Real Case

**Files:**
- Read: `manifests/cases/cra40_front2_20170628T18.yml`
- Output: `outputs/figures/cra40_front2_20170628T18/diagnostics/`

- [ ] Run `conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170628T18.yml`.
- [ ] Verify the diagnostics list contains the expanded CRA40 research PNG files.
- [ ] Read the statistics CSV and report the final output paths.
