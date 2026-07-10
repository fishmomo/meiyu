# Runner Override 与 Step Gating 设计

## 1. 背景

当前新流水线已经完成了以下基础能力：

- 以 `manifests/cases/cra40_front2_20170622T18.yml` 作为已验证案例入口
- 通过 `pipeline.manifest_loader.build_runtime_config(...)` 将 manifest 解析为运行时配置
- 通过 `pipeline.runner.run_case_from_manifest(...)` 串联当前最小真实链路
- 在 `CRA40 front2 2017-06-22T18 rh` 个例上验证 `inventory -> masks -> geometry -> profiles -> subareas -> statistics`

上一阶段解决的是“案例入口”和“配置承载”的问题。本阶段解决的是“入口参数真正如何影响执行行为”的问题，重点不是新增科研算法，而是把 runner 的行为边界定义清楚、验证清楚。

本设计只讨论当前已验证个例上的 runner 强化，不扩展 front1、ERA5、多变量读取和 legacy 图件总控。

## 2. 目标

本阶段目标有三项：

1. 让 runner 真正消费 manifest override，而不是只有 manifest 解析层支持 override。
2. 为 runner 增加分析链的 step gating 语义，明确哪些步骤可关闭，关闭后摘要如何返回。
3. 在不破坏当前摘要顶层结构的前提下，让“跳过”“部分完成”“完成”三种状态都能被稳定表达。

## 3. 非目标

本阶段不做以下内容：

- 不把 `inventory / masks / geometry` 也做成可随意关闭的步骤
- 不新增 front1、ERA5 或更多时次的正式 runner 支持
- 不把 `rh` 以外变量正式纳入 runner 的真实支持边界
- 不在本阶段引入完整图件输出调度
- 不把当前受限 runner 直接改造成全项目总入口

## 4. 设计原则

### 4.1 基础链与分析链分层

runner 分成两段链路：

- 基础链：`inventory -> masks -> geometry`
- 分析链：`profiles -> subareas -> statistics`

基础链用于保证每次运行至少能产出一个可靠的锋面几何基础结果。分析链是在基础结果之上进行的剖面、子区域和统计分析。

### 4.2 顶层摘要结构稳定

无论后续步骤是否执行，runner 顶层摘要 key 固定保持如下结构：

- `case_name`
- `inventory`
- `masks`
- `outputs`
- `geometry`
- `profiles`
- `subareas`
- `statistics`

调用方不应通过“某个 key 是否存在”来判断步骤是否执行，而应通过每个模块自己的状态字段判断。

### 4.3 显式状态优于静默缺失

对于未执行的步骤，不使用“省略 key”表达，而使用显式状态对象表达：

- `skipped`：该步骤被配置关闭，未执行
- `completed`：该步骤完整执行完成
- `partial`：该步骤被请求执行，但由于上游可选依赖缺失，只完成了可独立完成的部分

## 5. Override 范围与预期行为

### 5.1 本阶段正式验证的 override 字段

本阶段正式验证以下 override 字段：

- `params.geometry.n_sections`
- `params.geometry.delta_x`
- `params.subareas.start_section`
- `params.subareas.end_section`
- `steps.profiles`
- `steps.subareas`
- `steps.statistics`

这几个字段已经具备较清晰的输入含义，并且能够通过摘要变化稳定验证。

### 5.2 结构型 override

结构型 override 指直接影响几何或区域边界的字段。

#### `params.geometry.n_sections`

预期影响：

- `geometry.section_shape[0]` 应随之变化
- 如果 `profiles` 开启，`profiles.bundle_shape[0]` 应同步变化
- 如果 `subareas` 开启，子区域构造所依据的 section 编号空间也应同步变化

#### `params.geometry.delta_x`

预期影响：

- 改变切线或几何采样参数
- 当前阶段不强行要求统计值呈现固定数值变化趋势
- 当前阶段重点验证“runner 能稳定使用 override 后继续跑通，并保持稳定摘要结构”

#### `params.subareas.start_section` 与 `params.subareas.end_section`

预期影响：

- `subareas.start_section` 与 `subareas.end_section` 应反映 override 后的值
- `subareas.selected_points` 通常会变化
- 若 `statistics` 开启且依赖子区域统计，则 `statistics.subarea_mean` 也可能随之变化

### 5.3 开关型 override

开关型 override 指直接控制分析链步骤是否执行。

#### `steps.profiles = false`

预期行为：

- 基础链仍正常执行
- `profiles` 不执行
- `profiles` 返回显式跳过对象
- `subareas` 与 `statistics` 的行为不直接依赖 `profiles`，因此仍可根据各自开关决定是否执行

#### `steps.subareas = false`

预期行为：

- 基础链仍正常执行
- `subareas` 不执行，返回显式跳过对象
- 若 `statistics = true`，则 `statistics` 只计算可独立完成的完整锋面区域统计，不伪造子区域统计

#### `steps.statistics = false`

预期行为：

- 基础链仍正常执行
- `profiles` 和 `subareas` 是否执行，仅由它们自己的开关决定
- `statistics` 返回显式跳过对象

## 6. 模块摘要语义

### 6.1 `profiles`

当 `profiles` 开启并完成时，延续当前真实摘要主体，例如：

```python
{
    "enabled": True,
    "status": "completed",
    "variable": "rh",
    "bundle_shape": [8, 9, 37],
}
```

当 `profiles` 被关闭时：

```python
{
    "enabled": False,
    "status": "skipped",
}
```

### 6.2 `subareas`

当 `subareas` 开启并完成时，延续当前真实摘要主体，例如：

```python
{
    "enabled": True,
    "status": "completed",
    "mask_shape": [81, 141],
    "selected_points": 48,
    "start_section": 1,
    "end_section": 4,
}
```

当 `subareas` 被关闭时：

```python
{
    "enabled": False,
    "status": "skipped",
}
```

### 6.3 `statistics`

`statistics` 采用“部分可用、明确声明”的语义。

#### 完整完成

当 `statistics = true` 且 `subareas = true`，返回完整统计：

```python
{
    "enabled": True,
    "status": "completed",
    "front_mean": 85.81288001650856,
    "subarea_mean": 79.6975227355957,
    "subarea_status": "completed",
}
```

#### 部分完成

当 `statistics = true` 但 `subareas = false`，仍允许计算完整锋面区域统计，但不伪造子区域统计：

```python
{
    "enabled": True,
    "status": "partial",
    "front_mean": 85.81288001650856,
    "subarea_mean": None,
    "subarea_status": "skipped",
}
```

#### 跳过

当 `statistics = false`：

```python
{
    "enabled": False,
    "status": "skipped",
}
```

## 7. Runner 行为边界

本阶段 runner 的总行为边界定义如下：

1. `inventory / masks / geometry` 为必跑基础链，不受本阶段 `steps.*` 开关控制。
2. `profiles / subareas / statistics` 为可选分析链，受 `steps.*` 开关控制。
3. 顶层摘要 key 固定不变，不通过缺 key 表达步骤关闭。
4. 每个可选步骤必须显式返回 `completed / partial / skipped` 中的一种状态。
5. 本阶段仍然只正式支持 `CRA40 front2 2017-06-22T18 rh` 这条已验证链路。

## 8. 测试策略

本阶段测试分两层。

### 8.1 Manifest / 配置层回归

确保以下行为继续成立：

- manifest 仍能被解析为运行时配置
- 允许的 override 白名单不倒退
- 旧的 simple config 兼容路径不被误伤

### 8.2 Runner 行为验证

重点新增以下 runner 行为测试：

1. `run_case_from_manifest(...)` 在默认 manifest 下仍返回当前已验证摘要基线。
2. 当 override `params.geometry.n_sections` 时，`geometry.section_shape[0]` 与 `profiles.bundle_shape[0]` 发生预期变化。
3. 当 override `params.subareas.start_section/end_section` 时，`subareas.start_section/end_section` 与 `selected_points` 反映新配置。
4. 当 `steps.profiles = false` 时，`profiles.status == "skipped"`，基础链摘要仍存在。
5. 当 `steps.subareas = false` 且 `steps.statistics = true` 时，`statistics.status == "partial"`，`subarea_mean is None`。
6. 当 `steps.statistics = false` 时，`statistics.status == "skipped"`。

## 9. 与既有文档关系

本设计是对以下文档的续篇和补充：

- `docs/superpowers/specs/2026-07-09-runner-manifest-design.md`
- `docs/pipeline_quickstart_zh.md`
- `docs/pipeline_architecture_mapping_zh.md`

其中：

- manifest 设计文档解决“怎么描述案例与输入”
- 本文解决“runner 如何消费 override 与 step 开关，并如何稳定返回摘要”

## 10. 实施顺序

建议实施顺序如下：

1. 先补 runner 层行为测试，覆盖 override 与 step gating
2. 再调整 runner 摘要结构和 gating 逻辑
3. 最后更新 quickstart 与架构映射文档中的 runner 行为说明

## 11. 风险与边界提醒

- 当前 runner 仍然是“受限统一入口”，不是全流程科研总调度器
- `delta_x` 的数值影响在当前阶段只做可运行性与结构稳定性验证，不做科研含义背书
- 若后续引入更多统计量，应优先沿用 `enabled/status/...` 的显式摘要模式，而不是继续堆条件分支或省略字段
- 若后续要把 `inventory / masks / geometry` 也做成可配置步骤，应另起一轮设计，不应在本阶段顺手扩张
