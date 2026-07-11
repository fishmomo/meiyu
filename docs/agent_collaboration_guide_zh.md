# 梅雨锋项目 Agent 协作开发指南

## 1. 文档目的

这份文档面向后续参与本项目的其他 Agent 或协作者，目标不是解释全部科研背景，而是回答 4 个最实际的问题：

1. 这个项目当前的主线是什么
2. 哪些能力已经稳定，哪些能力还在演进
3. 接手时优先看哪些文件和文档
4. 多 Agent 并行时应该怎样分工，才能尽量减少冲突、缩短周期

## 2. 项目当前主线

当前项目已经从旧工程中拆出一条新的 `pipeline/` 主线，研究路径是：

`再分析资料 -> 掩膜 -> 几何拟合/切线 -> 剖面 -> 子区域 -> 统计 -> 诊断图件`

目前新的主线重点围绕 CRA40 与 front1/front2 个例做“可复用、可 runner 化、可逐步扩展”的研究流水线，而不是继续直接堆叠 legacy 大脚本。

## 3. 新旧结构速览

建议先把下面几份文档读完，再开始改代码：

- [docs/pipeline_quickstart_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_quickstart_zh.md)
- [docs/pipeline_architecture_mapping_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_architecture_mapping_zh.md)
- [docs/legacy_script_index_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/legacy_script_index_zh.md)
- [docs/superpowers/specs/2026-07-10-front1-v1-design.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/superpowers/specs/2026-07-10-front1-v1-design.md)
- [docs/superpowers/plans/2026-07-10-front1-v1-implementation.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/superpowers/plans/2026-07-10-front1-v1-implementation.md)
- [docs/agent_project_status_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/agent_project_status_zh.md)

代码层的主入口和关键目录如下：

- `pipeline/runner.py`
  当前统一 runner 入口
- `pipeline/manifest_loader.py`
  manifest 解析与 front1 V1 显式认证边界
- `pipeline/core/`
  可复用的底层操作与数据映射
- `pipeline/steps/`
  流水线分步模块
- `manifests/cases/`
  个例入口
- `tests/`
  每个 step 与 runner 的回归测试

## 4. 当前稳定约束

后续 Agent 必须默认遵守这些约束，除非有新的设计文档显式修改：

- 当前支持 CRA40 和 ERA5 双数据源
- `front1` / `front2` 已支持多时次（基于掩膜资产存在性验证，当前 front1 13 个时次、front2 23 个时次）
- `front1` 相关输入必须显式认证，不能静默复用 `front2`
- CRA40 `temp` 使用 `CRA40_TEM_*`，字段名 `t`；ERA5 `temp` 使用 `ERA5_tmp_201706.nc`，字段名 `t`
- CRA40 `w` 使用 `CRA40_VVP_*`，字段名 `w`；ERA5 `w` 使用 `ERA5_wdata_201706.nc`，字段名 `w`
- CRA40 `rh` 使用 `CRA40_RHU_*`，字段名 `r`；ERA5 `rh` 使用 `ERA5_RH_201706.nc`，字段名 `r`
- 剖面变量当前正式 runner 化范围是 `rh / temp / w`
- `read-meiyuji-cwr copy plot.ipynb` 不建议随便改
- `pipeline/runner.py` 当前是受约束的研究入口，不是通用“大总调度器”

## 5. 当前推荐工作方式

本项目现在默认采用 `Subagent-Driven` 协作模式。

如果多个 Agent 并行开发，推荐遵循下面的规则：

- 每个 Agent 只拿一个明确任务，不要同时跨多个任务修改
- 尽量按文件所有权切分，避免多个 Agent 同时改同一文件
- 优先复用已有 `pipeline/core/*` 和 `pipeline/steps/*`
- 新能力先补测试，再补实现
- 新设计先落文档，再进入实现
- 任务完成后要留下可读的 report 或状态文档，而不是只在会话里说明

## 6. 推荐并行分工方式

为了缩短周期，建议后续 Agent 以“互不重叠的写入面”为原则分工。

### 6.1 适合独立并行的工作包

- `diagnostics` 图件输出层
  主要文件：`pipeline/steps/diagnostics.py`、相关 tests、docs
- `runner` 顶层串联与摘要结构
  主要文件：`pipeline/runner.py`、`tests/test_runner_step.py`
- `docs` 与研究使用说明
  主要文件：`docs/*.md`、`README.md`
- `更多 manifest 个例`
  主要文件：`manifests/cases/*.yml`、个例 smoke tests

### 6.2 不建议随便并行重叠的区域

- `pipeline/manifest_loader.py`
  这里承载 front1 V1 的显式认证边界，多个 Agent 同时修改容易把输入约束搞乱
- `pipeline/runner.py`
  这是当前主线串联点，多个 Agent 同改时容易把摘要结构与步骤逻辑打散
- `tests/test_runner_step.py`
  这里是主入口行为契约，冲突概率很高

## 7. 接手前的环境提醒

- 运行环境：`cwr_py312`
- 项目根目录：`H:\邢台观测站\CWR_project\meiyu_new`
- Windows + 中文路径下，优先使用 [`nc_compat.py`](/H:/邢台观测站/CWR_project/meiyu_new/nc_compat.py) 里的兼容入口
- PowerShell 常见的 `profile.ps1` 执行策略报错通常是环境噪音，不等于命令失败

常用命令：

```powershell
conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml
```

## 8. 进入开发前先确认

其他 Agent 开始工作前，建议先确认下面 3 件事：

1. 我要修改的文件是否和其他 Agent 冲突
2. 我要承接的是“已稳定能力扩展”还是“仍在设计中的能力”
3. 我的输出需要留下什么文档或测试，方便下一位继续接手

如果做不到这三点，就先不要改代码，先补设计或状态说明。
