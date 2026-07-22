# Runner CLI Entrypoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为当前受支持的 Meiyu runner 增加一个最小命令行入口，使其可以通过 manifest 和少量 override 直接在终端运行。

**Architecture:** 直接在 `pipeline/runner.py` 中增加一个很薄的 CLI 包装层，只负责参数解析、调用 `run_case_from_manifest(...)`、将 summary 以 JSON 输出到终端。核心科学处理逻辑、支持边界和 summary 结构保持不变，CLI 相关验证通过单元测试和最小文档更新收口。

**Tech Stack:** Python 3.12, `argparse`, `json`, `unittest`, `conda run -n cwr_py312`, existing pipeline modules

## Global Constraints

- CLI 必须直接落在 `pipeline/runner.py`，不新增独立 `cli.py`
- 只支持 `--manifest` 和可重复的 `--override key=value`
- override 仅支持 `bool / int / float / str`
- 成功时返回码必须为 `0`，失败时必须为 `1`
- 成功输出写入 `stdout`，失败信息写入 `stderr`
- JSON 输出必须使用 `ensure_ascii=False`
- 不放宽当前支持边界：仅验证 `CRA40 front2 2017-06-22T18 rh`
- 不改变现有 `run_case()` / `run_case_from_manifest()` 的科学语义与 summary key 结构

---

### Task 1: 为 CLI 行为补失败测试

**Files:**
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\tests\test_runner_step.py`
- Test: `H:\邢台观测站\CWR_project\meiyu_new\tests\test_runner_step.py`

**Interfaces:**
- Consumes: `pipeline.runner.main(argv: list[str] | None = None) -> int`
- Produces: CLI 契约测试，覆盖成功路径、override 解析、坏输入和错误返回码

- [ ] **Step 1: 在测试文件中增加 CLI 成功用例的失败测试**

```python
    def test_runner_main_returns_zero_and_prints_json_for_manifest(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        from pipeline.runner import main

        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "--manifest",
                    "manifests/cases/cra40_front2_20170622T18.yml",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn('"case_name"', stdout.getvalue())
        self.assertIn('"statistics"', stdout.getvalue())
```

- [ ] **Step 2: 运行单测并确认它先失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py::RunnerStepTest::test_runner_main_returns_zero_and_prints_json_for_manifest -v`
Expected: FAIL，原因是 `pipeline.runner` 中还没有 `main`

- [ ] **Step 3: 在测试文件中增加 override 解析与错误路径测试**

```python
    def test_runner_main_applies_cli_overrides(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        from pipeline.runner import main

        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "--manifest",
                    "manifests/cases/cra40_front2_20170622T18.yml",
                    "--override",
                    "steps.subareas=false",
                    "--override",
                    "steps.statistics=true",
                    "--override",
                    "params.geometry.n_sections=6",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn('"status": "partial"', stdout.getvalue())
        self.assertIn('"section_shape": [', stdout.getvalue())

    def test_runner_main_returns_one_for_bad_override_pair(self) -> None:
        from io import StringIO
        from contextlib import redirect_stderr

        from pipeline.runner import main

        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(
                [
                    "--manifest",
                    "manifests/cases/cra40_front2_20170622T18.yml",
                    "--override",
                    "badpair",
                ]
            )

        self.assertEqual(code, 1)
        self.assertIn("ERROR:", stderr.getvalue())

    def test_runner_main_returns_one_for_unsupported_cli_case(self) -> None:
        from io import StringIO
        from contextlib import redirect_stderr

        from pipeline.runner import main

        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(
                [
                    "--manifest",
                    "manifests/cases/cra40_front2_20170622T18.yml",
                    "--override",
                    "params.profiles.variables=temp",
                ]
            )

        self.assertEqual(code, 1)
        self.assertIn("ERROR:", stderr.getvalue())
        self.assertIn("verified CRA40 front2 2017-06-22T18 rh", stderr.getvalue())
```

- [ ] **Step 4: 运行新增 CLI 测试并确认它们先失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -k "runner_main" -v`
Expected: FAIL，至少有一条因为 `main` 缺失而失败

- [ ] **Step 5: Commit**

```bash
git add tests/test_runner_step.py
git commit -m "test: add runner cli contract coverage"
```

### Task 2: 在 runner 中实现最小 CLI 包装层

**Files:**
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\pipeline\runner.py`
- Test: `H:\邢台观测站\CWR_project\meiyu_new\tests\test_runner_step.py`

**Interfaces:**
- Consumes: `run_case_from_manifest(path: Path, overrides: dict[str, object] | None = None) -> dict[str, object]`
- Produces:
  - `_parse_override_value(text: str) -> object`
  - `_parse_override_pairs(pairs: list[str] | None) -> dict[str, object]`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: 在 `pipeline/runner.py` 中先写最小 CLI 实现**

```python
import argparse
import json
import sys


def _parse_override_value(text: str) -> object:
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    try:
        return int(text)
    except ValueError:
        pass

    try:
        return float(text)
    except ValueError:
        return text


def _parse_override_pairs(pairs: list[str] | None) -> dict[str, object]:
    overrides: dict[str, object] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"override must use key=value format, got: {pair}")
        key, value = pair.split("=", 1)
        overrides[key] = _parse_override_value(value)
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the verified Meiyu pipeline case")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--override", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        summary = run_case_from_manifest(
            Path(args.manifest),
            overrides=_parse_override_pairs(args.override),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 运行 CLI 相关测试并确认转绿**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -k "runner_main" -v`
Expected: PASS

- [ ] **Step 3: 运行现有 runner 测试，确认没有回归**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_runner_step.py -v`
Expected: PASS

- [ ] **Step 4: 做最小静态校验**

Run: `python -m py_compile pipeline\runner.py tests\test_runner_step.py`
Expected: 无输出，返回码 `0`

- [ ] **Step 5: Commit**

```bash
git add pipeline/runner.py tests/test_runner_step.py
git commit -m "feat: add runner cli entrypoint"
```

### Task 3: 更新命令行使用文档

**Files:**
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\docs\pipeline_quickstart_zh.md`
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\README.md`
- Test: `H:\邢台观测站\CWR_project\meiyu_new\pipeline\runner.py`

**Interfaces:**
- Consumes: `python -m pipeline.runner --manifest <path> [--override key=value]`
- Produces: 面向使用者的最小 CLI 文档入口

- [ ] **Step 1: 在 quickstart 中增加“命令行运行”小节**

```markdown
## 命令行运行

当前可以直接通过 runner 的模块入口执行已验证 case：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml
```

关闭 `subareas` 但保留 `statistics`：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml --override steps.subareas=false --override steps.statistics=true
```

修改几何切分数：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml --override params.geometry.n_sections=6
```
```

- [ ] **Step 2: 在 README 中增加一段短入口说明**

```markdown
## 命令行入口

除在 IDE 中直接调用 `run_case_from_manifest(...)` 外，现在也可以直接从终端运行：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml
```

更完整的使用示例见 [docs/pipeline_quickstart_zh.md](docs/pipeline_quickstart_zh.md)。
```

- [ ] **Step 3: 运行一次最小真实命令确认文档示例可用**

Run: `conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml`
Expected: 输出格式化 JSON，包含 `"case_name"` 和 `"statistics"`

- [ ] **Step 4: 复查文档与实际行为一致**

Run: `rg -n "python -m pipeline.runner|命令行运行|命令行入口" README.md docs\pipeline_quickstart_zh.md`
Expected: 能看到 README 和 quickstart 中的 CLI 入口文字与示例命令

- [ ] **Step 5: Commit**

```bash
git add README.md docs/pipeline_quickstart_zh.md
git commit -m "docs: add runner cli usage examples"
```
