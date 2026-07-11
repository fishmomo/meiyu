# 梅雨锋新流水线技术架构与旧工程映射

## 1. 文档目的与读者

本文档面向三类读者：

- 维护 `pipeline/` 与相关基础设施的开发者
- 需要把新流水线继续扩展到更多数据源、锋面类型或变量的后续接手者
- 需要在新模块和旧科研脚本之间做问题追溯的人

本文档的目标不是快速教人“怎么跑”，而是回答四个维护问题：

1. 当前新流水线按什么结构组织。
2. `pipeline/steps/` 中各模块分别承接了旧工程的哪些逻辑。
3. 哪些能力已经迁移并经过验证，哪些仍主要依赖 legacy，哪些还没有进入新流水线总入口。
4. 后续如果要扩展 front1、ERA5、多变量或诊断图，应从哪里接入，而不是直接继续堆叠旧脚本。

本文档的判断依据来自：

- `docs/superpowers/specs/2026-07-09-architecture-mapping-and-runner-design.md`
- `docs/2026-07-05-layered-pipeline-design.md`
- `docs/legacy_project_smoke_status_2026-07-05.md`
- `docs/pipeline_quickstart_zh.md`
- `pipeline/steps/` 当前实现
- `tests/` 中与 step 和 runner 对应的验证用例

## 2. 当前新流水线总体结构

当前新流水线已经形成“manifest 案例层 + 配置入口/兼容层 + 路径与兼容层 + step 模块 + 受限 runner 入口”的结构。

```text
manifests/
  cases/
    cra40_front2_20170622T18.yml
pipeline/
  config.py
  manifest_loader.py
  manifest_models.py
  runner.py
  core/
    paths.py
    front_ops.py
    mask_ops.py
    section_ops.py
    stat_ops.py
    subarea_ops.py
  steps/
    inventory.py
    masks.py
    geometry.py
    profiles.py
    subareas.py
    statistics.py
```

配套基础设施位于：

- `project_paths.py`：统一项目内输入输出路径
- `nc_compat.py`：解决 Windows 中文路径下 `xarray/netCDF4/cfgrib/pygrib` 读写兼容问题

从执行关系看，当前新流水线分成两层：

1. 可复用计算模块层：`inventory -> masks -> geometry -> profiles -> subareas -> statistics`
2. manifest/配置解析层：`pipeline.manifest_loader.build_runtime_config(path, overrides=None)`
3. 统一入口层：`pipeline.runner.run_case(cfg)` 与 `pipeline.runner.run_case_from_manifest(path, overrides=None)`

其中统一入口层目前不是“通用总控器”，而是“受支持边界明确的串联器”。按照当前实现与测试，它正式支持以下已验证案例链路：

- `CRA40 + front2 + 2017-06-22T18 + rh`
- `CRA40 + front1 + 2017-06-22T18 + rh / temp / w`
- 支持更多时次（基于掩膜资产存在性验证）
- `ERA5 + front2 + 2017-06-22T18 + rh / temp / w`

这意味着当前新流水线已完成 front1/front2 多时次扩展、ERA5 接入和 diagnostics 图件扩展，但还没有泛化到批量调度。

第二阶段的边界需要按“基础链 / 可选分析链”来理解：

- `inventory / masks / geometry` 仍然是必跑基础链
- `profiles / subareas / statistics` 属于可选分析链，可由 `overrides` 和 step gating 单独开关
- 顶层摘要 key 保持固定，不会因为可选步骤关闭而增删字段
- 可选步骤的状态要显式表达为 `completed / partial / skipped`

## 3. 模块边界与职责

### 3.1 `inventory`

职责：

- 快照式检查 `raw / interim / processed` 三类目录是否存在
- 汇总环境依赖可用性，例如 `xarray`、`cfgrib`、`cartopy`、`matplotlib`

边界：

- 它不负责科学计算
- 它更接近“项目运行基线检查”而不是旧科研脚本的直接翻版

### 3.2 `masks`

职责：

- 解析当前案例可直接复用的掩膜资产位置
- 对外暴露主掩膜、extend 掩膜、子区域掩膜三类入口

边界：

- 当前实现仍限定在 `CRA40 + front2`
- 它解决的是“掩膜资产定位与组织”，不是重新生成全部人工识别成果

### 3.3 `geometry`

职责：

- 从主掩膜提取有效轮廓
- 拟合锋面中心线
- 估计法线方向
- 建立切线/法线采样框架

边界：

- 输出是几何抽样框架，不直接产出物理量剖面图
- 算法入口已经独立，但仍以“已有掩膜”为输入前提

### 3.4 `profiles`

职责：

- 基于 `geometry` 提供的采样框架，从三维场中抽取剖面 bundle
- 将“变量名 + 剖面数组”封装为稳定对象

边界：

- 当前公开接口可以承接不同变量
- 但真正进入已验证统一入口的只有 `rh`

### 3.5 `subareas`

职责：

- 根据 section 之间的空间关系，从主掩膜内部筛出子区域
- 生成子区域布尔掩膜

边界：

- 它只负责子区域选择逻辑
- 不负责读取 legacy 子区域图件，也不负责统计

### 3.6 `statistics`

职责：

- 对主掩膜或子区域掩膜内的格点做平均
- 提供单时次均值和时序均值接口

边界：

- 当前 step 只封装统计计算
- legacy 中完整的 CSV 汇总与制图流程并没有整体迁入新总入口

### 3.7 `runner`

职责：

- 校验当前配置是否位于已验证支持边界内
- 串联 `inventory -> masks -> geometry -> profiles -> subareas -> statistics`
- 返回结构化摘要，而不是承诺完整科研落盘产物
- 在第二阶段把基础链与可选分析链分开处理，确保 `inventory / masks / geometry` 必跑
- 对 `profiles / subareas / statistics` 提供显式 step gating，关闭时要在摘要里标出 `skipped`

边界：

- 当前不是通用入口
- 当前不是多案例批处理器
- 当前不是诊断图、ERA5、front1、多变量统一总控
- 当前返回的顶层摘要 key 结构固定不变，步骤是否执行通过 `completed / partial / skipped` 这类状态表达

## 4. 新模块与旧脚本映射表

| 新模块 | 当前承接职责 | 主要对应的旧脚本/旧逻辑 | 当前状态 | 说明 |
| --- | --- | --- | --- | --- |
| `pipeline.steps.inventory` | 目录与环境基线检查 | 本轮整理出的旧工程运行基线，而非单一 legacy 脚本 | 已迁移并已验证 | 已有对应 step 与测试；作用是把旧工程“能否运行”的前置条件结构化 |
| `pipeline.steps.masks` | 已有掩膜资产定位、主掩膜/extend/子区域掩膜入口 | `front_grid_lon_lat_unification.py`；`frontal_processing_CRA40.py` 中 offset 掩膜相关产物组织 | 已迁移并已验证 | 当前验证依赖项目内现成掩膜资产，不等于已迁入“重新生成全部掩膜”的完整能力 |
| `pipeline.steps.geometry` | 轮廓提取、中心线拟合、法线采样框架 | `frontal1_process_w.py`、`frontal1_process_rh.py`、`frontal2_process.py`、`frontal1_process_SelectSubArea.py` 中公共几何逻辑 | 已迁移并已验证 | 新模块抽离的是公共几何能力，不等于直接复刻旧脚本全部出图流程 |
| `pipeline.steps.profiles` | 沿 section 抽取三维场剖面 bundle | `frontal1_process_w.py`、`frontal1_process_rh.py`、`frontal2_process.py` 中剖面抽样逻辑 | 已迁移并已验证 | 模块接口具备扩展性，但当前统一入口只验证 `rh` |
| `pipeline.steps.subareas` | 按 section 之间关系筛选子区域 | `frontal1_process_SelectSubArea.py` | 已迁移并已验证 | 已形成独立函数接口和测试，但与 legacy 子区域命名、图件产物尚未完全统一 |
| `pipeline.steps.statistics` | 掩膜均值与时序均值计算 | `merge_csv.py`、`merge_csv fengmian2.py` 的统计内核 | 已迁移并已验证 | 当前已迁入的是统计计算能力，不是 legacy 全套 CSV/绘图流程 |
| `pipeline.steps.diagnostics` | 最小研究辅助图件落盘（剖面 overview） | `frontal_info_graphic_identification.py`；`frontal_processing_CRA40.py` 中诊断图部分 | 已迁移并已验证（最小能力） | 当前只实现最小图件集合，不等于完整替代 legacy 全部诊断图 |
| 通用化 `runner` 总入口 | 跨数据源、跨锋面、跨变量的统一串联 | 多个 legacy 脚本组合关系 | 已部分迁移 | 当前 `runner` 正式支持 `CRA40 front2 2017-06-22T18 rh` 和 `CRA40 front1 2017-06-22T18 rh/temp/w` |

映射时需要注意两点：

1. 一个旧脚本往往同时包含几何、剖面、绘图、统计等多种职责，所以不能做“一脚本对一模块”的机械对应。
2. 新流水线迁移的重点是“公共能力与可复用边界”，不是逐文件照搬旧工程。

## 5. 已迁移能力与未迁移能力

本项目当前必须明确区分三类状态，避免把“有代码骨架”误写成“已完成能力”。

### 5.1 已迁移并已验证

这类能力同时满足两个条件：已经有新模块实现，并且已有测试或真实案例链路验证。

- `inventory` 的目录快照与环境检查
- `masks` 对 `CRA40 front1/front2` 既有掩膜资产的显式解析
- `geometry` 的中心线拟合与 section 采样框架生成
- `profiles` 的三维场剖面抽样接口，已验证 `rh / temp / w`
- `subareas` 的子区域筛选
- `statistics` 的掩膜均值计算，已支持 front1 多变量逐变量 `front_mean` 与 `subarea_mean`
- `diagnostics` 的最小图件落盘
- `runner` 对 `CRA40 front2 2017-06-22T18 rh` 与 `CRA40 front1 2017-06-22T18 rh/temp/w` 的结构化串联

当前这些已验证能力在第二阶段里可以被 gating 拆开看，但语义不会变成“能力消失”：

- `completed`：对应步骤完成并产出结果
- `partial`：主链路继续跑通，但可选分析链只完成了部分步骤
- `skipped`：对应步骤被关闭，没有执行，因此只保留固定摘要结构

已验证的现阶段边界应理解为：

- 可以把当前最小案例以新模块方式串起来
- 可以返回几何、剖面、子区域、统计摘要
- 不应外推为“所有锋面、所有数据源、所有变量都已验证”

### 5.2 已有模块边界但仍主要依赖 legacy

这类能力已经在架构文档中有明确位置，甚至已有部分相关资产，但当前主要结果仍来自旧脚本，或者新流水线尚未形成等价入口。

- 统计类 legacy 产物输出：新流水线已有均值计算接口，但 `merge_csv.py`、`merge_csv fengmian2.py` 产生的 legacy 图件仍是当前可直接对照的主要结果
- 掩膜命名与产物规范：新流水线已经能消费现有掩膜，但像 `offset1.nc`、`area2_lonlat_0622T18.nc` 这类 legacy 风格命名仍在沿用
- diagnostics 完整图件体系：最小 diagnostics 已能落盘，但连续帧动画、批量出图、完整替代 `frontal_info_graphic_identification.py` 仍主要依赖 legacy

这一类能力不能写成“已全部迁移完成”，因为当前仍明显依赖旧脚本产物、旧命名或旧绘图流程。

### 5.3 尚未迁移到新流水线总入口

这类能力要么尚未进入 `runner`，要么尚未被证明能在统一入口下稳定工作。

- ERA5 的统一串联入口
- 更多时次的批量支持（front1/front2 均只验证了 `2017-06-22T18`）
- diagnostics 的完整图件总调度与批量出图
- 多案例批处理与批量调度
- 完整中间文件体系和统一 manifest/落盘规范

这一类能力即使在旧工程里“能跑”，也不能在新流水线文档中写成“已完成迁移”，因为它们还没有进入当前受支持的新总入口边界。

## 6. 后续扩展接入建议

后续扩展应遵循“先补模块边界，再补统一入口”的顺序，不建议直接在 `runner` 中堆分支。

### 6.1 扩展新的变量

建议入口：

- 先扩展 `profiles` 与 `statistics` 的变量读取和验证基线
- 待单变量在真实案例中稳定后，再进入 `runner`

不建议直接做的事：

- 在没有真实基线前，把 `temp / w / thetae` 一次性并入统一入口

### 6.2 扩展 front1

`front1 V1` 已经围绕 `CRA40 + 2017-06-22T18 + rh/temp/w` 完成最小可研究链路。后续扩展建议：

- 验证 `front1` 在更多时次上的稳定性
- 若需要更多变量，先在 `profiles` 层扩展字段映射，再进入 `runner`
- 若 front1 与 front2 的 section 参数不兼容，应在 manifest 参数层分别定义，而不是在 runner 里堆分支

### 6.3 扩展 ERA5

建议入口：

- 先在 step 层验证数据读取、坐标对齐、剖面抽样
- 只有当 ERA5 有独立真实案例基线后，才考虑进入统一入口

原因：

- 旧工程中 ERA5 相关脚本能跑，不等于当前新入口已经具备同等支持

### 6.4 补齐 diagnostics

最小 `diagnostics` 已作为独立 step 落地并纳入 `runner`。后续补齐建议：

- 在现有 `write_front_diagnostics(...)` 基础上逐步增加更多图件类型（连续帧、组合图、热力图等）
- 明确每种图件的输入、输出和与人工识别流程的关系
- 保持 diagnostics 只消费 step 结果、不反向侵入底层逻辑的原则

### 6.5 规范化产物命名与落盘

建议入口：

- 先在 `core/paths.py` 与写出层统一命名规范
- 再逐步替换 legacy 风格文件名

原因：

- 当前很多结果虽然能消费，但命名仍保留历史语义
- 如果先改入口、不改命名，后续排障会更难追溯

## 7. 与现有文档的使用顺序

建议把现有文档按“先理解架构，再理解旧基线，最后按需运行”的顺序使用。

### 7.1 第一步：看分层设计

先读 [`docs/2026-07-05-layered-pipeline-design.md`](/H:/邢台观测站/CWR_project/meiyu_new/docs/2026-07-05-layered-pipeline-design.md)。

用途：

- 理解为什么要按研究流程而不是按旧脚本文件名拆模块
- 理解 `inventory / diagnostics / masks / geometry / profiles / subareas / statistics` 这些边界从何而来

### 7.2 第二步：看本文档

再读本文档 [`docs/pipeline_architecture_mapping_zh.md`](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_architecture_mapping_zh.md)。

用途：

- 理解“新模块对应旧脚本哪里”
- 理解“三类迁移状态”边界
- 判断某项能力现在应去查新模块、旧脚本，还是仍需手工对照

### 7.3 第三步：看 legacy 冒烟基线

然后读 [`docs/legacy_project_smoke_status_2026-07-05.md`](/H:/邢台观测站/CWR_project/meiyu_new/docs/legacy_project_smoke_status_2026-07-05.md)。

用途：

- 查清哪些旧脚本已跑通
- 查清当前仍有效的 legacy 产物和兼容性前提
- 给新流水线结果做人工对照

### 7.4 第四步：最后看快速使用指南

只有在准备实际运行时，再读 [`docs/pipeline_quickstart_zh.md`](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_quickstart_zh.md)。

用途：

- 获取最小案例的运行方法
- 查看数据准备、命令示例与常见问题

注意：

- 快速使用指南是“如何运行”的文档，不是“迁移状态裁定”的权威来源
- 如果它与当前代码实现出现时效差异，应优先以当前 `pipeline/steps/`、`pipeline/runner.py` 和对应测试为准

## 8. 一句话结论

当前新流水线已完成 CRA40/ERA5 双源、front1/front2 双锋面、多时次、多变量、三类 diagnostics 图件的完整串联。尚未完成：ERA5 front1 覆盖、批量多案例调度、legacy 产物全面对齐。
