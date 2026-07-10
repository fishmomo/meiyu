# 旧工程冒烟现状汇总（2026-07-05）

## 目的

本文件用于记录：

1. 旧工程中已经在当前项目路径下跑通的脚本
2. 已确认生成或更新的关键产物
3. 下一阶段“新流水线重构”前，仍建议统一的输出路径与命名问题

当前运行环境：`cwr_py312`

## 本轮结论

旧工程主流程已经在“尽量少改原脚本逻辑”的前提下基本跑通。

本轮修通的核心不是算法改造，而是：

1. 将旧的硬路径迁移到项目内路径
2. 为 Windows 中文项目路径补上 `xarray/netCDF4/cfgrib/pygrib` 兼容层
3. 修复少量旧脚本中的环境依赖和末端绘图小错误

## 已跑通脚本清单

### 1. 统计与汇总类

- `merge_csv.py`
- `merge_csv fengmian2.py`

状态：

- 已实际运行通过
- 已在 `outputs/legacy_figures/PPT_pic/` 下生成图片

已验证产物：

- `outputs/legacy_figures/PPT_pic/fengmian2-CRA40-CWR.png`
- `outputs/legacy_figures/PPT_pic/fengmian2-CRA40-mask-new.png`
- `outputs/legacy_figures/PPT_pic/fengmian2-CRA40-CWR+SP.png`

### 2. 掩膜网格统一类

- `front_grid_lon_lat_unification.py`

状态：

- 已实际运行通过
- 已重新批量输出 CRA40 锋面 2 扩展掩膜

已验证产物：

- `data/interim/manual_masks/cra40/front2_extend/*.nc`

### 3. ERA5 个例与剖面类

- `frontal2_process.py`
- `frontal_info_graphic_identification.py`

状态：

- `frontal2_process.py` 已实际运行通过
- `frontal_info_graphic_identification.py` 已完成路径迁移和编译校验，本轮未重新逐图全量冒烟

已验证产物：

- `frontal2_process.py` 已完整执行结束
- `frontal_info_graphic_identification.py` 的输出路径已迁入 `outputs/legacy_figures/`

### 4. CRA40 诊断与偏移锋面类

- `frontal_processing_CRA40.py`

状态：

- 已实际运行通过
- 已输出时序图
- 已重新写出偏移锋面掩膜

已验证产物：

- `outputs/legacy_figures/PPT_pic/SP_CRA40/*.png`
- `outputs/legacy_figures/PPT_pic/fengmian_pianyi/time1/2017-06-26T06-2.png`
- `data/interim/manual_masks/cra40/front2_offset/offset1.nc`

### 5. CRA40 剖面与子区域类

- `frontal1_process_w.py`
- `frontal1_process_rh.py`
- `frontal1_process_SelectSubArea.py`

状态：

- 三个脚本均已实际运行通过
- `SelectSubArea` 已重新输出子区域掩膜

已验证产物：

- `data/interim/manual_masks/cra40/front2_subareas/area2_lonlat_0622T18.nc`

## 本轮关键兼容修复

### 1. 中文项目路径与科学计算后端冲突

已确认：

- PowerShell 能看到文件，不代表 `netCDF4/xarray/pygrib/cfgrib` 能直接在中文绝对路径下读写
- 典型症状包括：
  - 现有文件报 `FileNotFoundError`
  - 新文件写出报 `PermissionError`
  - `pygrib` 报 `UnicodeEncodeError`

当前处理方式：

- 新增 `nc_compat.py`
- `xarray` 读写统一走兼容入口
- `pygrib.open(...)` 输入路径统一先暂存到 ASCII 临时目录
- `GRIB2` 默认走 `cfgrib` 并关闭索引文件副作用

### 2. 环境补充

本轮已为 `cwr_py312` 补装：

- `cfgrib`

作用：

- 让 `xarray` 可以直接识别并读取 `*.grib2`
- 保持旧脚本主体逻辑不需要改成全量 `pygrib` 手工解析

### 3. 旧脚本自身小问题修复

已修复：

- `merge_csv fengmian2.py` 中 pandas 只读数组赋值报错
- `frontal1_process_w.py` / `frontal1_process_rh.py` / `frontal1_process_SelectSubArea.py` 中未使用的 `cfgrib` 残留导入
- `frontal1_process_SelectSubArea.py` 中 `glob` 名称覆盖导致的 `TypeError`
- `frontal1_process_SelectSubArea.py` 最后一张掩膜图经纬度维度不匹配

## 当前仍存在但不阻塞运行的警告

### 1. 非交互绘图警告

多个脚本存在：

- `FigureCanvasAgg is non-interactive, and thus cannot be shown`

原因：

- 当前冒烟采用 `MPLBACKEND=Agg`
- 脚本里仍保留 `plt.show()`

结论：

- 不影响批处理执行
- 后续重构时建议统一改为“保存优先，可选显示”

### 2. MetPy 热力计算警告

多个剖面脚本存在：

- `divide by zero encountered in log`
- `invalid value encountered in divide`

结论：

- 当前不阻塞脚本完成
- 更像是局部格点物理量导致的数值警告
- 后续重构时建议显式记录并处理无效值

## 仍建议规范化的输出路径与命名

以下问题不影响旧工程运行，但建议作为下一阶段重构优先项。

### 1. 输出目录语义混杂

当前已迁入项目内，但目录语义仍带旧工程习惯：

- `outputs/legacy_figures/PPT_pic/`
- `outputs/legacy_figures/201706/`
- `outputs/legacy_figures/PPT_pic/SP_CRA40/`
- `outputs/legacy_figures/PPT_pic/fengmian_pianyi/time1/`

建议后续统一为更清晰的层级，例如：

- `outputs/figures/era5/front_identification/...`
- `outputs/figures/cra40/series/...`
- `outputs/figures/front_profiles/front1/...`
- `outputs/figures/front_profiles/front2/...`

### 2. 文件命名规则不统一

当前命名混合了：

- 纯时间名：`2017-06-28T06.png`
- 时间加后缀：`2017-06-26T06-2.png`
- 主题型文件名：`fengmian2-CRA40-CWR.png`
- 旧语义缩写：`SP_CRA40`

建议后续统一命名元素：

- 数据源：`era5` / `cra40`
- 锋面编号：`front1` / `front2`
- 产品类型：`mask` / `profile` / `timeseries` / `subarea`
- 变量类型：`sp` / `thetae` / `rh` / `w`
- 时间：`YYYY-MM-DDTHH`

### 3. 掩膜输出命名仍偏“人工约定”

当前仍有：

- `offset1.nc`
- `area2_lonlat_0622T18.nc`

建议后续统一改为显式命名，例如：

- `front2_offset_positive_2017-06-26T06.nc`
- `front2_subarea_area2_2017-06-22T18.nc`

### 4. 个别脚本仍保留旧路径痕迹或示例路径

当前主要剩余：

- `PIL_GIF.py` 示例输入仍是旧外部路径
- 个别脚本内仍有注释形式的旧 `H:\` / `D:\` 路径
- 个别 `savepath = ...` 中间变量已经无实际必要

这些不影响运行，但建议在新流水线阶段清理。

## 推荐的下一阶段工作顺序

1. 先把“旧工程已跑通清单”作为基线冻结，不再大改旧脚本逻辑
2. 基于当前项目路径体系，整理统一的输入输出规范
3. 再按研究流程拆成新流水线模块：
   - 资料准备
   - 诊断量绘图
   - 人工识别成果整理
   - 锋面掩膜生成
   - 拟合与切线生成
   - 多物理量剖面分析
   - 子区域掩膜输出
   - 掩膜统计与序列汇总

## 备注

本文件记录的是“当前旧工程在项目内路径下可运行的状态”，不是最终重构结果。

后续若进入新流水线开发，应优先复用：

- `project_paths.py`
- `nc_compat.py`
- `data/` 与 `outputs/` 的当前项目内路径组织
