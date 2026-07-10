# Runner Override And Step Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `pipeline.runner` 真正消费 manifest override，并为 `profiles / subareas / statistics` 增加稳定的 step gating 与显式摘要状态。

**Architecture:** 保持 `inventory / masks / geometry` 作为必跑基础链，只对 `profiles / subareas / statistics` 引入 gating。先用测试固定默认基线与 override 行为，再最小修改 runner，把 `completed / partial / skipped` 显式写入模块摘要，最后同步更新中文使用文档与架构映射。

**Tech Stack:** Python 3.12, unittest/pytest, project-local manifest loader, pipeline runner, Markdown docs

## Global Constraints

- 只正式支持当前已验证案例：`CRA40 front2 2017-06-22T18 rh`
- 顶层摘要 key 必须保持稳定：`case_name / inventory / masks / outputs / geometry / profiles / subareas / statistics`
- `inventory / masks / geometry` 不纳入本轮 step 开关
- `profiles / subareas / statistics` 关闭时必须返回显式状态对象，不能靠缺 key 表达
- `statistics` 在 `subareas = false` 且 `statistics = true` 时必须返回 `partial` 语义
- 保持 legacy `run_case(cfg)` 兼容入口不回退
- 文档与代码注释使用中文说明关键行为边界
- 当前工作目录不是可用 git 仓库；所有“Commit”步骤改为“完成检查点记录”，不执行 git commit

---

## File Structure

- `tests/test_runner_step.py`
  当前 runner 行为回归测试入口；本轮新增 override 与 step gating 行为测试。
- `pipeline/runner.py`
  当前 manifest/legacy 兼容运行入口；本轮新增 step 开关读取、可选步骤跳过/部分完成摘要、默认基线兼容。
- `docs/pipeline_quickstart_zh.md`
  面向使用者的运行说明；本轮补充 step 开关、跳过状态和部分统计语义。
- `docs/pipeline_architecture_mapping_zh.md`
  面向维护者的结构说明；本轮补充 runner 第二阶段边界与 override/gating 语义。
- `.superpowers/sdd/progress.md`
  在没有 git 提交条件下记录本轮任务完成检查点。

### Task 1: 用测试固定 override 与 step gating 目标行为

**Files:**
- Modify: `tests/test_runner_step.py`
- Test: `tests/test_runner_step.py`

**Interfaces:**
- Consumes: `pipeline.runner.run_case_from_manifest(path: Path, overrides: dict[str, object] | None = None) -> dict[str, object]`
- Produces: 失败中的行为断言，覆盖 `n_sections`、`subareas` section override、`steps.profiles`、`steps.subareas`、`steps.statistics`

- [ ] **Step 1: 在 `tests/test_runner_step.py` 添加 override 行为测试**

```python
    def test_run_case_from_manifest_applies_geometry_override(self) -> None:
        from pathlib import Path
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={"params.geometry.n_sections": 6},
        )

        self.assertEqual(summary["geometry"]["section_shape"], [6, 9])
        self.assertEqual(summary["profiles"]["bundle_shape"], [6, 9, 37])

    def test_run_case_from_manifest_applies_subarea_section_override(self) -> None:
        from pathlib import Path
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={
                "params.subareas.start_section": 2,
                "params.subareas.end_section": 5,
            },
        )

        self.assertEqual(summary["subareas"]["status"], "completed")
        self.assertEqual(summary["subareas"]["start_section"], 2)
        self.assertEqual(summary["subareas"]["end_section"], 5)
        self.assertGreater(summary["subareas"]["selected_points"], 0)
```

- [ ] **Step 2: 在 `tests/test_runner_step.py` 添加 step gating 行为测试**

```python
    def test_run_case_from_manifest_skips_profiles_when_disabled(self) -> None:
        from pathlib import Path
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={"steps.profiles": False},
        )

        self.assertEqual(summary["geometry"]["section_shape"], [8, 9])
        self.assertEqual(
            summary["profiles"],
            {"enabled": False, "status": "skipped"},
        )

    def test_run_case_from_manifest_returns_partial_statistics_without_subareas(
        self,
    ) -> None:
        from pathlib import Path
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={
                "steps.subareas": False,
                "steps.statistics": True,
            },
        )

        self.assertEqual(summary["subareas"], {"enabled": False, "status": "skipped"})
        self.assertEqual(summary["statistics"]["enabled"], True)
        self.assertEqual(summary["statistics"]["status"], "partial")
        self.assertIsNone(summary["statistics"]["subarea_mean"])
        self.assertEqual(summary["statistics"]["subarea_status"], "skipped")

    def test_run_case_from_manifest_skips_statistics_when_disabled(self) -> None:
        from pathlib import Path
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={"steps.statistics": False},
        )

        self.assertEqual(
            summary["statistics"],
            {"enabled": False, "status": "skipped"},
        )
```

- [ ] **Step 3: 跑新增测试，确认当前实现先失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`

Expected: FAIL，至少包含以下一种失败信号：
- 断言里找不到 `enabled` 或 `status`
- `section_shape` 没有按 override 变化
- `statistics` 仍返回旧结构而不是 `partial/skipped`

- [ ] **Step 4: 补一个默认基线不回退的断言**

```python
    def test_run_case_from_manifest_default_summary_keeps_completed_status(self) -> None:
        from pathlib import Path
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
        )

        self.assertEqual(summary["profiles"]["status"], "completed")
        self.assertEqual(summary["subareas"]["status"], "completed")
        self.assertEqual(summary["statistics"]["status"], "completed")
```

- [ ] **Step 5: 完成检查点记录**

在 `.superpowers/sdd/progress.md` 追加一行：

```text
Task 5: test scaffolding for runner override and step gating added; expected red-state captured before runner changes
```

### Task 2: 最小改动 runner 以支持 override 生效与显式状态摘要

**Files:**
- Modify: `pipeline/runner.py`
- Test: `tests/test_runner_step.py`

**Interfaces:**
- Consumes: `RunnerRuntimeConfig.steps`, `RunnerRuntimeConfig.profiles`, `RunnerRuntimeConfig.subareas`, `run_case_from_manifest(...)`
- Produces:
  - `run_case(cfg) -> dict[str, object]`
  - `run_case_from_manifest(path, overrides=None) -> dict[str, object]`
  - 显式状态摘要：
    - `profiles: {"enabled": bool, "status": str, ...}`
    - `subareas: {"enabled": bool, "status": str, ...}`
    - `statistics: {"enabled": bool, "status": str, ...}`

- [ ] **Step 1: 在 `pipeline/runner.py` 增加读取 step 开关的最小辅助函数**

```python
def _is_step_enabled(cfg: Any, name: str, default: bool = True) -> bool:
    steps = getattr(cfg, "steps", None)
    if steps is None:
        return default
    value = getattr(steps, name, default)
    return bool(value)


def _skipped_summary() -> dict[str, object]:
    return {"enabled": False, "status": "skipped"}
```

- [ ] **Step 2: 重构 `run_case` 中的 profiles 分支，保留默认基线并支持跳过**

```python
    profiles_enabled = _is_step_enabled(cfg, "profiles", True)
    if profiles_enabled:
        profile_variable = _get_profile_variable(cfg)
        field_path = _get_profile_input_path(cfg, profile_variable)
        profile_bundle = build_profile_bundle_from_field(
            field_path,
            geometry,
            variable=profile_variable,
        )
        profiles_summary = {
            "enabled": True,
            "status": "completed",
            "variable": profile_variable,
            "bundle_shape": list(profile_bundle.values.shape),
        }
    else:
        profile_bundle = None
        profiles_summary = _skipped_summary()
```

- [ ] **Step 3: 重构 `run_case` 中的 subareas 分支，保留默认基线并支持跳过**

```python
    subareas_enabled = _is_step_enabled(cfg, "subareas", True)
    if subareas_enabled:
        start_section, end_section = _get_subarea_sections(cfg)
        subarea_mask = build_subarea_mask(
            mask=front_mask,
            geometry=geometry,
            start_section=start_section,
            end_section=end_section,
        )
        subareas_summary = {
            "enabled": True,
            "status": "completed",
            "mask_shape": list(subarea_mask.shape),
            "selected_points": int(subarea_mask.sum()),
            "start_section": start_section,
            "end_section": end_section,
        }
    else:
        subarea_mask = None
        subareas_summary = _skipped_summary()
```

- [ ] **Step 4: 重构 `run_case` 中的 statistics 分支，支持 completed / partial / skipped**

```python
    statistics_enabled = _is_step_enabled(cfg, "statistics", True)
    if not statistics_enabled:
        statistics_summary = _skipped_summary()
    else:
        front_mean = float(build_masked_mean(field_2d, front_mask))
        if subarea_mask is None:
            statistics_summary = {
                "enabled": True,
                "status": "partial",
                "front_mean": front_mean,
                "subarea_mean": None,
                "subarea_status": "skipped",
            }
        else:
            subarea_mean = float(build_masked_mean(field_2d, subarea_mask))
            statistics_summary = {
                "enabled": True,
                "status": "completed",
                "front_mean": front_mean,
                "subarea_mean": subarea_mean,
                "subarea_status": "completed",
            }
```

- [ ] **Step 5: 组装最终摘要时统一使用新摘要对象**

```python
    return {
        "case_name": cfg.case_name,
        "inventory": inventory_summary,
        "masks": masks_summary,
        "outputs": outputs_summary,
        "geometry": geometry_summary,
        "profiles": profiles_summary,
        "subareas": subareas_summary,
        "statistics": statistics_summary,
    }
```

- [ ] **Step 6: 跑 runner 测试，确认从红到绿**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`

Expected: PASS，默认基线与 override/gating 新测试全部通过。

- [ ] **Step 7: 跑 manifest + runner 回归测试**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_runner_step.py -v`

Expected: PASS，manifest 兼容路径不回退。

- [ ] **Step 8: 做一次真实 smoke，确认摘要语义与计划一致**

Run: `conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; import pprint; pprint.pp(run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml'), overrides={'steps.subareas': False, 'steps.statistics': True}))"`

Expected: 输出里包含：
- `subareas == {'enabled': False, 'status': 'skipped'}`
- `statistics['status'] == 'partial'`
- `statistics['subarea_mean'] is None`

- [ ] **Step 9: 完成检查点记录**

在 `.superpowers/sdd/progress.md` 追加一行：

```text
Task 6: runner override and step gating implemented; tests and partial-statistics smoke passed
```

### Task 3: 同步中文文档与维护文档，说明新 runner 语义

**Files:**
- Modify: `docs/pipeline_quickstart_zh.md`
- Modify: `docs/pipeline_architecture_mapping_zh.md`
- Modify: `.superpowers/sdd/progress.md`
- Test: `docs/pipeline_quickstart_zh.md`

**Interfaces:**
- Consumes: `pipeline.runner.run_case_from_manifest(...)` 的最新摘要结构
- Produces:
  - quickstart 中关于 step 开关和摘要状态的使用说明
  - architecture mapping 中关于 runner 第二阶段边界的维护说明

- [ ] **Step 1: 在 quickstart 中补充 step 开关示例命令**

```markdown
你也可以通过 override 暂时关闭后半段分析链中的某一步，例如只保留完整锋面统计、跳过子区域：

```python
from pathlib import Path
from pipeline.runner import run_case_from_manifest

summary = run_case_from_manifest(
    Path("manifests/cases/cra40_front2_20170622T18.yml"),
    overrides={
        "steps.subareas": False,
        "steps.statistics": True,
    },
)
```
```

- [ ] **Step 2: 在 quickstart 中明确摘要状态语义**

```markdown
当前 `runner` 的可选分析步骤不会再通过“字段消失”表达未执行，而会显式返回：

- `status == "completed"`：该步骤已完整执行
- `status == "skipped"`：该步骤被配置关闭
- `status == "partial"`：该步骤被请求执行，但只完成了独立可完成的部分

例如当 `subareas` 被关闭而 `statistics` 仍开启时，`statistics` 会保留 `front_mean`，同时把 `subarea_mean` 置为 `None`。
```

- [ ] **Step 3: 在架构映射文档中补充第二阶段 runner 边界**

```markdown
当前 `runner` 已进入第二阶段：在保持 `CRA40 front2 2017-06-22T18 rh` 验证边界不扩张的前提下，开始正式支持 manifest override 对部分运行参数和分析链步骤开关的影响。

其中：

- `inventory / masks / geometry` 仍是必跑基础链
- `profiles / subareas / statistics` 是可选分析链
- 顶层摘要 key 固定不变
- 可选步骤通过 `completed / partial / skipped` 显式表达执行状态
```

- [ ] **Step 4: 复查文档中的旧摘要表述并改成新语义**

Run: `rg -n "front_mean|subarea_mean|包含|statistics|skipped|partial|completed" docs\pipeline_quickstart_zh.md docs\pipeline_architecture_mapping_zh.md`

Expected: 能定位到旧描述；更新后，文档同时保留默认基线值与新状态语义，不再暗示“statistics 永远完整返回子区域统计”。

- [ ] **Step 5: 跑一次最小编译与测试回归**

Run: `python -m py_compile pipeline\runner.py tests\test_runner_step.py`

Expected: PASS

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_runner_step.py -v`

Expected: PASS

- [ ] **Step 6: 完成检查点记录**

在 `.superpowers/sdd/progress.md` 追加一行：

```text
Task 7: runner gating docs aligned in quickstart and architecture mapping; final regression green
```

## Self-Review

### 1. Spec coverage

- override 生效验证：由 Task 1 和 Task 2 覆盖
- `profiles / subareas / statistics` step gating：由 Task 1 和 Task 2 覆盖
- `statistics` partial 语义：由 Task 1 的断言、Task 2 的实现与 Task 3 的文档同步覆盖
- 顶层摘要结构稳定：由 Task 2 返回结构和 Task 1 默认基线断言覆盖
- 文档同步：由 Task 3 覆盖

未发现 spec 中无任务承接的要求。

### 2. Placeholder scan

- 未使用 `TODO`、`TBD`、`implement later` 等占位词
- 每个测试步骤都给出具体命令与预期结果
- 每个代码修改步骤都给出具体函数或摘要结构示例

### 3. Type consistency

- `run_case_from_manifest(path, overrides=None) -> dict[str, object]` 与现有代码一致
- 新摘要对象统一使用 `enabled: bool` 与 `status: str`
- `statistics.subarea_mean` 在 partial 状态下统一为 `None`
- `subareas` 和 `profiles` 的 skipped 结构统一为 `{"enabled": False, "status": "skipped"}`

Plan complete and saved to `docs/superpowers/plans/2026-07-09-runner-override-step-gating.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
