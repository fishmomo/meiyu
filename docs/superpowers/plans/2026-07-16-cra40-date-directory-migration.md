# CRA40 Date Directory Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Organize existing June 2017 CRA40 files by date without changing the data paths consumed by the existing Meiyu pipelines.

**Architecture:** Keep `data/raw/cra40/<year>/<YYYYMMDD>/` as the canonical layout. Add a single resolver in `project_paths.py` that accepts root-level legacy files first, then finds a uniquely matching file in the date directory. Extend the legacy glob helper to cover the new tree, then migrate only after resolver tests pass.

**Tech Stack:** Python 3.12, `pathlib`, `unittest`, PowerShell file moves.

## Global Constraints

- Preserve all unrelated dirty-worktree changes.
- Do not change CRA40 field naming, manifests, masks, diagnostics, or scientific calculations.
- A filename must resolve to one path only; duplicate recursive matches are an error.
- Keep `.idx` sidecars beside their GRIB or GRIB2 source file.

---

### Task 1: Add CRA40 location compatibility tests and resolver

**Files:**
- Modify: `tests/test_pipeline_paths.py`
- Modify: `project_paths.py`

**Interfaces:**
- Produces `cra40_file(filename: str) -> str` which returns a root-level match first, otherwise a unique dated match.
- Produces `cra40_glob(pattern: str) -> str` which returns a recursive pattern for callers that use `glob(..., recursive=True)`.

- [ ] **Step 1: Write failing tests for dated lookup and duplicate protection**

```python
    def test_cra40_file_finds_unique_dated_file_when_root_file_is_absent(self) -> None:
        import project_paths

        with TemporaryDirectory() as tmpdir:
            raw = Path(tmpdir)
            target = raw / "2017" / "20170622" / "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
            target.parent.mkdir(parents=True)
            target.touch()
            with patch.object(project_paths, "RAW_CRA40_DIR", raw):
                self.assertEqual(project_paths.cra40_file(target.name), str(target))

    def test_cra40_file_rejects_multiple_dated_matches(self) -> None:
        import project_paths

        with TemporaryDirectory() as tmpdir:
            raw = Path(tmpdir)
            filename = "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
            for folder in (raw / "2017" / "20170622", raw / "backup" / "20170622"):
                folder.mkdir(parents=True)
                (folder / filename).touch()
            with patch.object(project_paths, "RAW_CRA40_DIR", raw):
                with self.assertRaisesRegex(RuntimeError, "multiple CRA40 files"):
                    project_paths.cra40_file(filename)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_paths -v`

Expected: the dated-file assertion fails because the current helper only returns `RAW_CRA40_DIR / filename`; the duplicate assertion fails because no error is raised.

- [ ] **Step 3: Implement minimal root-first, unique recursive lookup**

```python
def cra40_file(filename: str) -> str:
    direct = RAW_CRA40_DIR / filename
    if direct.exists():
        return str(direct)
    matches = sorted(RAW_CRA40_DIR.rglob(filename))
    if len(matches) == 1:
        return str(matches[0])
    if len(matches) > 1:
        raise RuntimeError(f"multiple CRA40 files named {filename}: {matches}")
    return str(direct)


def cra40_glob(pattern: str) -> str:
    return str(RAW_CRA40_DIR / "**" / pattern)
```

- [ ] **Step 4: Run resolver tests to verify they pass**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_paths -v`

Expected: all path tests pass.

### Task 2: Verify legacy glob behavior and migrate June 2017 files

**Files:**
- Modify: `tests/test_pipeline_paths.py`
- Modify: `frontal_processing_CRA40.py:30`
- Move: every root-level `CRA40_*201706*.nc`, `CRA40_*201706*.grib`, `CRA40_*201706*.grib2`, and matching `.idx` file into `data/raw/cra40/2017/YYYYMMDD/`

**Interfaces:**
- Consumes `cra40_glob("CRA40*.nc")`.
- Produces an unchanged legacy file list when passed to `glob(..., recursive=True)`.

- [ ] **Step 1: Write a failing glob-layout test**

```python
    def test_cra40_glob_includes_dated_subdirectories(self) -> None:
        import project_paths

        with TemporaryDirectory() as tmpdir:
            raw = Path(tmpdir)
            dated = raw / "2017" / "20170622"
            dated.mkdir(parents=True)
            (dated / "CRA40_2017062218.nc").touch()
            with patch.object(project_paths, "RAW_CRA40_DIR", raw):
                pattern = project_paths.cra40_glob("CRA40*.nc")
            self.assertIn("**", pattern)
            self.assertEqual(glob(pattern, recursive=True), [str(dated / "CRA40_2017062218.nc")])
```

Add `from glob import glob` to the test module.

- [ ] **Step 2: Run the glob test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_paths.PipelinePathsTest.test_cra40_glob_includes_dated_subdirectories -v`

Expected: failure because the original pattern does not contain `**` and cannot locate the dated file.

- [ ] **Step 3: Make the glob helper recursive and re-run all path tests**

```python
file_list = sorted(glob(cra40_glob("CRA40*.nc"), recursive=True))
```

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_paths -v`

Expected: all path tests pass.

- [ ] **Step 4: Preflight the migration without changing files**

Run a Python command that parses each root-level CRA40 June 2017 filename, prints `source -> data/raw/cra40/2017/YYYYMMDD/filename`, verifies each target does not already exist, and counts both source and planned target files.

Expected: every candidate has one valid ten-digit timestamp and every destination is unique.

- [ ] **Step 5: Move files by parsed timestamp**

Use a Python or PowerShell migration command that handles `CRA40_*.nc`, `CRA40_*201706*.grib`, `CRA40_*201706*.grib2`, and their `.idx` sidecars. Create `data/raw/cra40/2017/YYYYMMDD/` before each move. Do not move files without a valid `YYYYMMDDHH` token.

- [ ] **Step 6: Verify migration inventory**

Run: `Get-ChildItem -LiteralPath data\raw\cra40 -File -Filter 'CRA40*'`

Expected: no root-level CRA40 raw data remains. Then count recursive CRA40 source files and compare it with the preflight count; the counts must match.

### Task 3: Run Meiyu regression checks against moved data

**Files:**
- No additional production files.

**Interfaces:**
- Consumes `manifests/cases/cra40_front2_20170622T18.yml` and existing CRA40 assets.

- [ ] **Step 1: Run focused unit tests**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_paths tests.test_manifest_loader tests.test_profiles_step -v`

Expected: all tests pass.

- [ ] **Step 2: Resolve the existing Meiyu input files from their canonical names**

Run: `conda run -n cwr_py312 python -c "from pipeline.core.cra40_fields import resolve_cra40_profile_input; print(resolve_cra40_profile_input('rh')); print(resolve_cra40_profile_input('temp')); print(resolve_cra40_profile_input('w'))"`

Expected: all three printed paths point under `data/raw/cra40/2017/20170622/`.

- [ ] **Step 3: Run the real Meiyu smoke case**

Run: `conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml`

Expected: completed summary with resolved profile inputs in the dated directory and no input-file errors.

- [ ] **Step 4: Inspect only task-owned changes before handoff**

Run: `git diff -- project_paths.py tests/test_pipeline_paths.py docs/superpowers/specs/2026-07-16-cra40-date-directory-migration-design.md docs/superpowers/plans/2026-07-16-cra40-date-directory-migration.md`

Expected: the diff contains only compatibility, tests, and documentation. Do not stage or commit because the worktree contains unrelated user changes.
