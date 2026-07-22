# 旧脚本功能总表

这份文档的目的不是替代旧脚本注释，而是从“整个项目怎么理解”的角度，把根目录旧脚本、新流水线模块和研究流程之间的关系放到一张总表里。

适用场景：

- 新接手这个仓库时，先快速理解每个脚本大概负责什么
- 判断某个需求应该继续走旧脚本，还是已经可以走 `pipeline/`
- 给后续“进一步流水线化”提供一份过渡地图

## 1. 总体分层

当前仓库里的代码可以先分成三层：

1. 旧研究脚本层  
   根目录下的 `frontal*.py`、`merge_csv*.py`、`front_grid_lon_lat_unification.py` 等，保留原研究过程中的直接分析与出图逻辑。

2. 功能工具层  
   例如 `plot_picture_function.py`、`PIL_GIF.py`、`nc_compat.py`、`project_paths.py`，承担绘图、动图、路径和兼容支持。

3. 新流水线层  
   `pipeline/`、`manifests/`、`tests/`，把已稳定的步骤抽象成模块，并提供统一入口与测试。

## 2. 根目录脚本总表

| 脚本 | 主要作用 | 典型输入 | 典型输出 | 在当前项目中的位置 |
|---|---|---|---|---|
| `plot_picture_function.py` | 通用绘图函数 | 各类诊断场、剖面场 | PNG/JPG 等图件 | 工具层，供旧脚本复用 |
| `PIL_GIF.py` | 把已有组图生成为 GIF | 一组顺序图片 | GIF 动图 | 工具层，后处理辅助 |
| `front_grid_lon_lat_unification.py` | 统一原始再分析资料与目标范围；裁剪并生成新范围锋面掩膜 | 原始网格资料、人工打点结果 | 新范围 `nc` 掩膜文件 | 旧流程前段，掩膜资产准备 |
| `frontal_info_graphic_identification.py` | 生成 ERA5 个例连续帧图，服务人工识别打点 | ERA5 诊断量场 | 连续帧图件 | 旧流程中的识别辅助与诊断图 |
| `frontal_processing_CRA40.py` | 基于 CRA40 生成熵位温、降水等时序图；并输出沿拟合法线方向上下偏移锋面掩膜 | CRA40 资料、个例时间 | 时序图、offset 掩膜数据 | 旧流程中的 CRA40 诊断与 offset 产物来源 |
| `frontal1_process_rh.py` | 第一锋面湿度剖面处理 | 某时刻锋面掩膜、RH 三维场 | 湿度剖面图 | 旧流程中的 front1 剖面分析 |
| `frontal1_process_w.py` | 第一锋面垂直速度剖面处理 | 某时刻锋面掩膜、W 三维场 | 垂直速度剖面图 | 旧流程中的 front1 剖面分析 |
| `frontal1_process_SelectSubArea.py` | 在切线之间进一步筛选锋面子区域并输出掩膜 | 拟合曲线、切线、掩膜 | 子区域掩膜数据 | 旧流程中的子区域研究入口 |
| `frontal2_process.py` | 第二锋面的拟合、切线和多物理量剖面处理 | 某时刻锋面掩膜、多变量三维场 | front2 剖面与组合图 | 旧流程中的 front2 剖面分析 |
| `merge_csv.py` | 基于锋面掩膜做物理量网格平均并输出统计序列 | 掩膜、变量场 | CSV/统计结果 | 旧流程后段，完整锋面统计 |
| `merge_csv fengmian2.py` | 锋面 2 的应用统计与图片支持，也可用于锋面 1 类似绘制 | 掩膜、变量场、统计表 | CSV/图片相关结果 | 旧流程后段，front2 统计扩展 |
| `read-meiyuji-cwr copy plot.ipynb` | 相对独立的梅雨季/梅雨期及暴雨年份研究 notebook | 研究数据与统计结果 | Notebook 图表与分析记录 | 相对独立，不建议随意改动 |

## 3. 研究流程中的位置

把这些脚本按研究顺序排，大致可以理解为：

1. `front_grid_lon_lat_unification.py`  
   负责把原始资料与研究范围统一起来，并形成可后续使用的锋面掩膜资产。

2. `frontal_info_graphic_identification.py` / `frontal_processing_CRA40.py`  
   提供 ERA5 与 CRA40 的诊断依据，支撑人工识别和交叉验证锋面位置。

3. `frontal1_process_rh.py` / `frontal1_process_w.py` / `frontal2_process.py`  
   对已识别锋面做拟合、切线切割和多物理量剖面分析。

4. `frontal1_process_SelectSubArea.py`  
   在切线框架上进一步截取研究子区域，并输出可复用掩膜。

5. `merge_csv.py` / `merge_csv fengmian2.py`  
   利用完整锋面或子区域掩膜，对物理量做网格平均和统计输出。

## 4. 与新流水线的对应关系

当前已经迁入 `pipeline/` 的，不是旧脚本的全部，而是其中相对稳定、可复用的“计算内核”。

| 新流水线模块 | 对应旧脚本能力来源 | 当前状态 |
|---|---|---|
| `pipeline.steps.inventory` | 旧工程运行基线检查 | 已迁移 |
| `pipeline.steps.masks` | `front_grid_lon_lat_unification.py`、`frontal_processing_CRA40.py` 的掩膜组织思路 | 已迁移入口层 |
| `pipeline.steps.geometry` | `frontal1_process_*`、`frontal2_process.py` 中拟合/切线公共几何逻辑 | 已迁移 |
| `pipeline.steps.profiles` | `frontal1_process_rh.py`、`frontal1_process_w.py`、`frontal2_process.py` 中剖面抽样逻辑 | 已迁移 |
| `pipeline.steps.subareas` | `frontal1_process_SelectSubArea.py` 中子区域筛选逻辑 | 已迁移 |
| `pipeline.steps.statistics` | `merge_csv.py`、`merge_csv fengmian2.py` 的掩膜平均统计内核 | 已迁移 |
| `pipeline.runner` | 以上模块的 manifest 驱动统一入口 | 已支持已验证案例串联、diagnostics、CSV 导出与多 manifest 批量运行 |

尚未整体迁入 `pipeline/` 的，主要包括：

- legacy 中更完整的出图命名和结果组织约定
- 连续帧、组合剖面、人工识别辅助图等更复杂 diagnostics
- 多时次统计分析深化，如时序均值和跨锋面对比
- 更大范围 ERA5 时次覆盖

## 5. 现在应该怎么用

如果你的目标是：

- 看清旧工程每个脚本做什么  
  先看这份文档，再结合原脚本顶部注释。

- 快速跑一个已验证的新链路  
  先看 [快速使用指南](pipeline_quickstart_zh.md)。

- 理解新旧代码怎么对应  
  再看 [技术架构与旧工程映射](pipeline_architecture_mapping_zh.md)。

- 继续把更多旧流程迁入新流水线  
  建议优先迁移“稳定的计算内核”，不要先迁移整套图件批处理。

## 6. 一句话理解

根目录旧脚本仍然保存着完整研究过程的上下文；`pipeline/` 则是在这些脚本基础上，已经抽出来的一条“可测试、可复用、可继续扩展”的新主线。
