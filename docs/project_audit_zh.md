# 梅雨锋项目代码与数据审计（第一阶段）

## 1. 当前研究主线

结合现有代码与您的说明，项目主线可整理为：

1. 再分析资料准备
2. 关键诊断量时序/空间分布绘制
3. 人工识别与打点
4. 生成锋面掩膜数据
5. 对锋面区域进行曲线拟合与切线切割
6. 沿切线提取湿度/温度/垂直速度等剖面
7. 进一步筛选锋面子区域并输出子区域掩膜
8. 用掩膜结合云水资源量及相关特征量做区域平均
9. 输出完整锋面区与子区域的时序变化结果

这条主线已经比较清楚，后续重构可以按“资料准备 -> 掩膜 -> 剖面 -> 统计 -> 出图/动图”的流水线组织。

## 2. 现有脚本职责梳理

### 2.1 基础功能脚本

- `plot_picture_function.py`
  - 地图刻度、行政区边界、面域转掩膜等基础绘图工具。
  - 其中省界底图依赖 `china.shp`。
- `PIL_GIF.py`
  - 将已有静态图批量合成为 GIF 动图。
  - 属于通用后处理脚本。

### 2.2 相对独立的 notebook

- `read-meiyuji-cwr copy plot.ipynb`
  - 用于梅雨季、梅雨期以及个别暴雨年份研究。
  - 依赖额外的 `H:\NCEP_fixed\{年份}\p2_as_matlab\ResultGrid_D_*.nc` 数据。
  - 按您的要求，本阶段不改 notebook。

### 2.3 ERA5 / CRA40 主流程脚本

- `frontal_info_graphic_identification.py`
  - 基于 ERA5 绘制连续帧图。
  - 主要用于人工识别锋面和人工打点前的诊断参考。
  - 会叠加已有锋面掩膜散点，说明它既是“前期识别图”，也在验证人工打点结果。

- `front_grid_lon_lat_unification.py`
  - 将已有小范围锋面掩膜插值并统一到 CRA40 目标经纬度网格。
  - 本质是“掩膜网格统一与范围扩展”。

- `frontal_processing_CRA40.py`
  - 基于 CRA40 输出熵位温梯度、降水等时序或图形结果。
  - 同时会基于拟合线法线方向生成“上下偏移锋面”掩膜。
  - 是后续子区域研究的重要中间环节。

- `frontal1_process_rh.py`
  - 针对某一时次的锋面，拟合中心线并做等分切线。
  - 提取相对湿度剖面，并叠加温度/熵位温等值线。

- `frontal1_process_w.py`
  - 与 `frontal1_process_rh.py` 类似，但重点变量为垂直速度 `w`。

- `frontal2_process.py`
  - 逻辑与 `frontal1_process_*` 类似。
  - 兼有两部分功能：
    - 基于 ERA5 掩膜区域计算时序统计量（如 `|grad(theta_e)|`、CAPE）
    - 对某一时次做拟合线、切线和剖面分析

- `frontal1_process_SelectSubArea.py`
  - 在切线基础上继续划分锋面子区域。
  - 输出子区域掩膜，是后续“子区域平均统计”的关键来源。

- `merge_csv.py`
  - 汇总掩膜区域对应的云水资源相关 CSV 结果。
  - 输出区域平均时序图，属于掩膜应用的末端统计环节。

## 3. 代码中识别出的输入路径、输出路径与建议新路径

下面分为“现状硬编码路径”和“建议项目内路径”两列。

### 3.1 原始输入资料

| 类型 | 现状路径 | 当前状态 | 建议项目内路径 |
|---|---|---|---|
| ERA5 综合场 | `H:\Yu_jie\meiyu\data\201706.nc` | 已找到并已复制 | `data/raw/era5/201706.nc` |
| ERA5 CAPE | `H:\Yu_jie\meiyu\data\ERA5-CAPE.nc` | 已找到并已复制 | `data/raw/era5/ERA5-CAPE.nc` |
| ERA5 RH | `H:\Yu_jie\meiyu\data\ERA5_RH_201706.nc` | 已找到并已复制 | `data/raw/era5/ERA5_RH_201706.nc` |
| ERA5 SP | `H:\Yu_jie\meiyu\data\ERA5_SP_201706.nc` | 已找到并已复制 | `data/raw/era5/ERA5_SP_201706.nc` |
| ERA5 tmp | `H:\Yu_jie\meiyu\data\ERA5_tmp_201706.nc` | 已找到并已复制 | `data/raw/era5/ERA5_tmp_201706.nc` |
| ERA5 w | `H:\Yu_jie\meiyu\data\ERA5_wdata_201706.nc` | 已找到并已复制 | `data/raw/era5/ERA5_wdata_201706.nc` |
| CRA40 nc/grib/grib2 | `H:\Yu_jie\meiyu\CRA40\*` | 已找到并已复制 | `data/raw/cra40/` |
| 中国省界 shp | `H:\邢台观测站\python_qixianglianxi\shp\China\*` | 已找到并已复制 | `data/static/shapefiles/china/` |

### 3.2 掩膜与中间数据

| 类型 | 现状路径 | 当前状态 | 建议项目内路径 |
|---|---|---|---|
| ERA5 锋面1掩膜 | `D:\Yu_jie\pysider6\meiyu\fengmian1\{DT}.nc` | 缺失 | `data/interim/manual_masks/era5/front1/{DT}.nc` |
| ERA5 锋面2掩膜 | `D:\Yu_jie\pysider6\meiyu\fengmian2\{DT}.nc` | 缺失 | `data/interim/manual_masks/era5/front2/{DT}.nc` |
| CRA40 锋面1掩膜 | `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian1\{DT}.nc` | 缺失 | `data/interim/manual_masks/cra40/front1/{DT}.nc` |
| CRA40 锋面2掩膜 | `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2\{DT}.nc` | 缺失 | `data/interim/manual_masks/cra40/front2/{DT}.nc` |
| CRA40 扩展网格掩膜 | `...\CRA40_fengmian2\extend\{DT}.nc` / `extend_new\{DT}.nc` | 缺失 | `data/interim/manual_masks/cra40/front2_extend/{DT}.nc` |
| CRA40 子区域掩膜 | `...\CRA40_fengmian2\F_subdivision\*.nc` | 缺失 | `data/interim/manual_masks/cra40/front2_subareas/` |
| CRA40 偏移锋面掩膜 | `...\CRA40_fengmian2\diff\offset1.nc` | 缺失 | `data/interim/manual_masks/cra40/front2_offset/offset1.nc` |

### 3.3 统计结果与图形输出

| 类型 | 现状路径 | 当前状态 | 建议项目内路径 |
|---|---|---|---|
| mask 区域 CSV | `D:\Yu_jie\python project\cwr-compute-client\CSV\CRA40_mask\fengmian2*.csv` | 缺失 | `data/processed/mask_statistics/fengmian2_*.csv` |
| 各类 PNG 输出 | `H:\我的业务\MeiYu\锋生函数图\...` | 外部目录存在，但未迁入 | `outputs/figures/...` |
| GIF 输出 | 各脚本临时目录 | 未统一 | `outputs/animations/...` |

### 3.4 notebook 独立资料

| 类型 | 现状路径 | 当前状态 | 建议项目内路径 |
|---|---|---|---|
| NCEP ResultGrid | `H:\NCEP_fixed\{year}\p2_as_matlab\ResultGrid_D_*.nc` | 盘上存在，但尚未迁入项目 | `data/raw/notebook_ncep/{year}/` |

## 4. 本次已完成的数据整理

本阶段已在项目内建立统一目录，并完成以下复制：

- `data/raw/era5/`
  - 已复制 6 个 ERA5 文件，总大小约 499 MB。
- `data/raw/cra40/`
  - 已复制 202 个 CRA40 相关文件，总大小约 3.71 GB。
- `data/static/shapefiles/china/`
  - 已复制 `china.shp/.shx/.dbf/.prj/.cpg/.json` 及 `dem.png`。

此外，已提前建立以下空目录，供后续重构与补数据使用：

- `data/interim/manual_masks/era5/front1/`
- `data/interim/manual_masks/era5/front2/`
- `data/interim/manual_masks/cra40/front1/`
- `data/interim/manual_masks/cra40/front2/`
- `data/interim/manual_masks/cra40/front2_extend/`
- `data/interim/manual_masks/cra40/front2_subareas/`
- `data/interim/manual_masks/cra40/front2_offset/`
- `data/processed/mask_statistics/`
- `outputs/figures/`
- `outputs/animations/`

## 5. 当前明确缺失的数据

以下缺失项会阻断主流程后半段运行：

### 5.1 锋面掩膜库缺失

代码中反复依赖但当前未找到的目录：

- `D:\Yu_jie\pysider6\meiyu\fengmian1`
- `D:\Yu_jie\pysider6\meiyu\fengmian2`
- `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian1`
- `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2`
- `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2\extend`
- `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2\extend_new`
- `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2\F_subdivision`
- `D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2\diff`

建议您如果手头还保留这些数据，统一放到：

- `data/interim/manual_masks/era5/front1/`
- `data/interim/manual_masks/era5/front2/`
- `data/interim/manual_masks/cra40/front1/`
- `data/interim/manual_masks/cra40/front2/`
- `data/interim/manual_masks/cra40/front2_extend/`
- `data/interim/manual_masks/cra40/front2_subareas/`
- `data/interim/manual_masks/cra40/front2_offset/`

建议文件命名继续沿用现有时间格式：

- `{YYYY-MM-DDTHH}.nc`
- 例如：`2017-06-22T18.nc`

### 5.2 `merge_csv.py` 依赖的 CSV 缺失

当前未找到：

- `D:\Yu_jie\python project\cwr-compute-client\CSV\CRA40_mask\fengmian2*.csv`

建议统一放到：

- `data/processed/mask_statistics/`

如果后续需要分区域，建议命名规范改为：

- `front2_full_{DT}.csv`
- `front2_subarea_a_{DT}.csv`
- `front2_subarea_b_{DT}.csv`

## 6. 代码层面的关键观察

### 6.1 当前代码偏“研究草稿串联”，尚未形成可复用流水线

主要表现为：

- 大量硬编码路径
- 时间索引直接写死
- 同类逻辑在多个脚本中重复
- “读数据 -> 找掩膜 -> 拟合 -> 切线 -> 插值 -> 出图”没有拆成稳定函数

### 6.2 掩膜是整个流程的中枢数据资产

从实际依赖关系看，后续绝大多数分析都建立在掩膜上：

- ERA5/CRA40 对照验证要用掩膜
- 曲线拟合与切线要用掩膜边界
- 子区域细分要从掩膜出发
- `merge_csv` 的区域平均也要靠掩膜结果

所以后续重构时，最值得先标准化的是：

1. 掩膜文件格式
2. 掩膜目录结构
3. 掩膜时间命名规则
4. ERA5/CRA40 网格统一逻辑

## 7. 建议的后续重构顺序

在缺失掩膜补齐后，建议按下面顺序进入第二阶段：

1. 先做统一配置文件
   - 统一管理数据根目录、输出目录、shp 路径、研究时段、区域范围。
2. 再拆基础库
   - `io.py`：读 ERA5 / CRA40 / mask
   - `mask_ops.py`：掩膜裁剪、扩展、网格统一
   - `front_curve.py`：边界提取、拟合、等弧长采样、法线切线
   - `profile_ops.py`：剖面插值与组合绘图
   - `stats_ops.py`：掩膜区域统计
   - `plotters.py`：统一出图
3. 最后再做流水线脚本
   - `step01_prepare_data.py`
   - `step02_identify_front_reference.py`
   - `step03_unify_masks.py`
   - `step04_fit_front_and_profiles.py`
   - `step05_select_subareas.py`
   - `step06_mask_statistics.py`
   - `step07_make_gif.py`

## 8. 第一阶段结论

第一阶段已经可以确认：

- 主原始资料已基本齐备，并已迁入项目内。
- notebook 独立资料路径已定位。
- 主流程最关键的缺口不是 ERA5/CRA40，而是“人工打点后的锋面掩膜库”和“后续统计 CSV”。
- 项目已经具备进入“统一目录 + 新代码重塑 + skill 化流程”的前提，但前提是您补齐上述掩膜/CSV，或者允许我后续先按空目录和接口把新流水线架起来。
