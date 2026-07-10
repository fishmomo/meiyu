# Front1 V1 Design

## 1. 目标

本轮要做的不是把新流水线一次性泛化成完整的 front1 / front2 / 多时次 / 多数据源统一研究平台，而是做出一个能够真正开始研究的 `front1 V1`。

`front1 V1` 的明确目标是：

- 以 `CRA40` 为唯一数据源
- 以 `2017-06-22T18` 作为唯一基线时次
- 以 `front1` 为唯一锋面对象
- 以 `rh + temp + w` 作为第一批正式 runner 化变量
- 打通一条可研究主线：
  `mask -> geometry -> profiles -> subareas -> statistics -> diagnostics`

本轮完成后，研究者应能围绕这个单个 front1 个例，在新流水线内稳定获得：

- front1 掩膜与几何结果
- 三变量沿切线的剖面结果
- front1 完整区域与子区域统计结果
- 至少一套可稳定落盘的研究辅助图件
- 通过统一 manifest / runner 入口复现整个个例

## 2. 非目标

本轮明确不做以下事情：

- 不接入 `ERA5`
- 不扩展到多个时次
- 不做 front1 的批量 case 调度
- 不把 diagnostics 一次做成通用总调度器
- 不追求 front1 / front2 / 多变量的全面统一泛化
- 不替换全部 legacy 图件流程

这些能力都属于后续阶段。本轮只围绕“让 front1 真正进入可研究状态”来设计。

## 3. 基线个例与资产认定

### 3.1 基线个例

`front1 V1` 的唯一基线个例定为：

- dataset: `cra40`
- front_id: `front1`
- target_time: `2017-06-22T18`

这样做的原因是：

- 该时次在现有 front1 旧脚本中最稳定、最一致地被用作默认处理时次
- 它足够接近当前 front2 基线，便于复用已有结构和测试思路
- 它能把精力集中在 front1 资产与多变量链路，而不是再被更多时次分散

### 3.2 front1 掩膜资产边界

本轮首先必须把“front1 该用哪套掩膜”从 legacy 混用状态中剥离出来。

当前旧脚本里存在一个风险：front1 名义下的脚本，掩膜读取位置仍可能沿用 `front2` 相关接口或路径。对研究而言，这种历史混用不能继续进入新流水线。

因此 `front1 V1` 的第一原则是：

- 新流水线中凡是进入 `front1 V1` 的掩膜资产，必须显式以 `front1 + 2017-06-22T18` 身份被认定
- 若当前项目内不存在这套可确认的 front1 掩膜资产，则该任务先卡在资产整理层，而不是继续假设复用 `front2`

本轮允许的 front1 资产包括：

- 主掩膜
- 必要时的 extend 掩膜
- 若需要子区域研究，则包括 front1 对应的子区域掩膜或可从几何结果动态生成的子区域掩膜

本轮不允许的做法：

- 因为 legacy 脚本能跑，就默认 front1 可以沿用 front2 掩膜
- 在 runner 中静默把 front1 映射成 front2
- 文档上写成 front1，实际数据资产仍是 front2

## 4. 总体架构

本轮采用“保守桥接式”方案。

这意味着：

- 尽量复用当前已经稳定的 `pipeline.steps.*`
- 在必要位置补 front1 个例支持
- 在必要位置补 `temp / w` 变量支持
- 通过一个新的 front1 manifest 和一个受控 runner 边界，把这条 front1 个例主线串起来

本轮不追求先把 runner 做成大而全入口，而是先确保：

- 这个 front1 个例确实能研究
- 输出结果对研究者足够可用
- 代码路径足够清楚，便于后续扩展到更多时次

## 5. 模块设计

### 5.1 masks

`masks` 这一层要新增或补齐 `front1` 资产解析能力，但范围只限于：

- `front1`
- `2017-06-22T18`
- `CRA40`

职责：

- 显式解析 front1 主掩膜
- 如有需要，显式解析 front1 extend 掩膜
- 若 front1 子区域掩膜已有现成资产，则显式解析它
- 若没有现成 front1 子区域掩膜，则先允许后续 `subareas` 从主掩膜 + geometry 动态生成

本层不负责：

- 重新生产人工打点掩膜
- 推断 front1/front2 映射关系
- 处理 ERA5 掩膜

### 5.2 geometry

`geometry` 继续复用现有中心线拟合与 section 采样框架。

本轮要解决的问题不是重写 geometry，而是验证：

- front1 掩膜在当前 section 参数下是否稳定
- `n_sections / n_points / delta_x` 这一组几何参数对 front1 是否仍然适用

输出仍保持 `GeometryResult` 风格，不引入新的 front1 专用几何对象。

若 front1 在现有几何参数下不稳定，本轮允许针对 front1 V1 单独定义一组默认参数，但这些参数应放在 manifest 或 front1 个例配置中，而不是散落在 runner 条件分支里。

### 5.3 profiles

`profiles` 是本轮真正扩展的核心之一。

当前新流水线已经验证了：

- 单变量 `rh`
- 沿 geometry 抽取剖面 bundle

`front1 V1` 需要把这一层扩展到：

- `rh`
- `temp`
- `w`

扩展原则：

- 仍使用统一的 `build_profile_bundle_from_field(...)` 这类公共接口
- 变量差异应主要体现在“字段读取与命名映射”层，而不是每个变量各写一套剖面算法
- 每个变量都必须能在 front1 个例上形成稳定的 bundle 结果

本轮 runner 层的多变量支持不要求一次性输出复杂嵌套结构，但至少应能：

- 逐变量产出 profile 摘要
- 在 diagnostics 层消费这些 profile 结果

### 5.4 subareas

`subareas` 继续使用现有按 section 区间筛选的思路。

本轮目标不是泛化新的子区域理论，而是确保：

- front1 主掩膜上能稳定选出子区域
- 子区域结果可以继续喂给 statistics 与 diagnostics

本轮允许两种形态并存：

- 动态生成的 front1 子区域掩膜
- 若已有历史 front1 子区域掩膜文件，也允许作为对照或兼容输入

但 runner 的主线应优先围绕动态生成子区域掩膜，因为这更符合新流水线“从几何结果衍生研究区域”的方向。

### 5.5 statistics

`statistics` 本轮要从“front2 + rh 已验证”扩展为“front1 + 三变量可用”。

至少应支持：

- front1 完整区域均值
- front1 子区域均值
- `rh / temp / w` 三变量的单时次统计结果

本轮不要求：

- 一步补齐完整 CSV 批量导出体系
- 把 legacy 统计图完整迁进来

但输出语义要足够稳定，使研究者可以据此判断：

- 完整锋区与子区域在三个变量上的差异
- 是否值得进一步扩展到更多时次

### 5.6 diagnostics

本轮 diagnostics 的定位很明确：

- 它是“研究辅助图稳定产出层”
- 不是“大总调度器”

因此本轮 diagnostics 只需要做到：

- 能消费 front1 几何结果
- 能消费 `rh / temp / w` 三变量 profile 结果
- 能消费必要的区域/子区域统计结果
- 输出至少一套研究必需图件

建议本轮最小图件集合为：

- front1 个例的基础几何/掩膜辅助图
- 三变量剖面图
- 至少一张多变量组合图

本轮 diagnostics 不要求：

- 连续帧动画总调度
- 批量出图
- 完整替代 `frontal_info_graphic_identification.py` 或全部 legacy 研究图

本轮的标准不是“图件全”，而是“研究者看这组图就能开始判断 front1 个例物理结构”。

### 5.7 runner

`runner` 本轮要从：

- `CRA40 front2 2017-06-22T18 rh`

扩展到：

- `CRA40 front1 2017-06-22T18`
- `rh / temp / w`

但 runner 的扩展方式必须克制：

- 不应变成一大串 if/else 的临时总控
- 支持边界必须显式写清楚
- front1 V1 是“新增一个已验证个例边界”，不是“front1 已全面支持”

本轮 runner 至少应支持：

- 一个新的 front1 manifest
- front1 个例的 masks / geometry / profiles / subareas / statistics 串联
- 必要时增加 diagnostics 的统一触发

runner 顶层摘要仍应保持结构化，不回退成 legacy 大脚本式自由打印。

## 6. 数据与配置设计

### 6.1 manifest

本轮应新增一个 front1 基线 manifest，表达：

- case_name
- dataset = `cra40`
- front_id = `front1`
- target_time = `2017-06-22T18`
- geometry 参数
- variables = `rh / temp / w`
- 相关输入数据与掩膜资产

manifest 的作用不是美化配置，而是把：

- “front1 基线个例是什么”
- “这轮研究到底用哪些变量”
- “默认几何参数是什么”

这些信息从代码里抽出来，固定成可复现研究入口。

### 6.2 变量映射

本轮必须明确 `rh / temp / w` 在 CRA40 中各自读取哪个变量、走哪套输入文件。

变量映射应尽量放在清楚的配置或解析层，而不是散在多个 step 里。

原则：

- runner 负责组织
- step 负责计算
- 数据字段映射负责解释变量从哪来

## 7. 研究可启动的验收标准

只有同时满足下面几条，`front1 V1` 才算完成，研究才能真正开始：

1. front1 的 `2017-06-22T18` 掩膜资产被明确认定，不再混用 front2 资产
2. `geometry` 能在 front1 掩膜上稳定运行
3. `rh / temp / w` 三变量都能沿 front1 切线成功抽取剖面
4. front1 子区域掩膜能生成或被稳定读取
5. front1 完整区域与子区域统计结果能稳定输出
6. 至少一套 front1 研究辅助图件能稳定落盘
7. front1 manifest 能通过统一 runner 入口复现该个例
8. quickstart 或后续使用文档中能明确告诉研究者怎样运行 front1 V1

## 8. 实施顺序

本轮推荐按下面顺序推进：

1. 先厘清 front1 掩膜资产
2. 再验证 front1 geometry
3. 再扩 `temp / w` 变量进入 profiles
4. 再补 front1 statistics
5. 再接 front1 runner manifest
6. 最后补 front1 diagnostics 与使用说明

这样排序的原因是：

- front1 掩膜资产不清，后面都是假工作
- geometry 不稳定，profiles/subareas/statistics 都会连锁失真
- 多变量先进入计算链，再进入图件层，风险更低
- diagnostics 应建立在计算链稳定之后，而不是反过来驱动底层

## 9. 风险与处理策略

### 9.1 front1 资产仍不清楚

风险：

- 旧脚本名义上是 front1，但实际仍读 front2 掩膜

处理：

- 本轮优先做资产核对
- 若 front1 资产缺失，则明确把任务停在资产整理，而不是继续假跑

### 9.2 三变量并入后 runner 结构失控

风险：

- 为了快速支持 `rh / temp / w`，把 runner 写成变量分支堆栈

处理：

- 变量读取与字段映射单独收口
- 剖面算法继续复用统一 step 接口

### 9.3 diagnostics 又回到 legacy 大脚本模式

风险：

- 为了尽快出图，直接把旧图件逻辑整体搬进一个新大脚本

处理：

- 这轮只定义最小图件集合
- 只让 diagnostics 消费 step 结果，不反向侵入底层逻辑

## 10. 一句话结论

`front1 V1` 的目标不是“把新流水线做完整”，而是“以 CRA40 front1 2017-06-22T18 + rh/temp/w 为基线，做出一条真实可研究、可复现、可继续扩展的单个个例主线”。
