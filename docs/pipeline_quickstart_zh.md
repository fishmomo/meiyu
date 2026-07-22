# 梅雨锋新流水线快速使用指南

## 1. 这份指南适合谁

这份文档面向三类使用者：

- 当前项目的主要研究者
- 后续需要复现实验或接手维护的人
- 不想先通读全部旧脚本，但希望先把新流水线跑起来的人

这份指南的目标很直接：告诉你当前版本的新流水线怎么用、从哪里开始、每一步会得到什么。

需要特别说明两点：

1. 当前新流水线已经把 `mask -> geometry -> profiles -> subareas -> statistics -> diagnostics` 这条主链路拆成了可复用模块。
2. 当前的 [`pipeline/runner.py`](/H:/邢台观测站/CWR_project/meiyu_new/pipeline/runner.py) 已经可以串联已验证案例，支持 CRA40/ERA5、front1/front2、多变量（`rh / temp / w`）、diagnostics 图件、CSV 导出和多 manifest 批量运行。它仍然不是任意数据、任意变量、任意产物的通用科研总调度器；使用时应以 manifest 与项目内已有数据资产为边界。

## 2. 运行前准备

### 2.1 运行环境

- 虚拟环境：`cwr_py312`
- 项目根目录：`H:\邢台观测站\CWR_project\meiyu_new`

推荐在项目根目录下执行命令。

```powershell
conda run -n cwr_py312 python -c "print('env ok')"
```

### 2.2 当前推荐的数据目录约定

项目内已经统一了主要路径，建议只使用项目内目录，不再依赖外部硬路径。

- 原始数据：`data/raw/`
- 中间掩膜数据：`data/interim/manual_masks/`
- 统计结果：`data/processed/mask_statistics/`
- 新流水线输出：`outputs/figures/`
- legacy 图片输出：`outputs/legacy_figures/`

这些路径的集中定义见 [`project_paths.py`](/H:/邢台观测站/CWR_project/meiyu_new/project_paths.py)。

### 2.3 当前最小案例需要的关键数据

本指南默认先用一个最小 smoke 案例起步：

- 数据集：`CRA40`
- 锋面：`front2`
- 时次：`2017-06-22T18`

这一条链路最关键的输入包括：

- manifest 案例文件：`manifests/cases/cra40_front2_20170622T18.yml`
- 主掩膜：`data/interim/manual_masks/cra40/front2/2017-06-22T18.nc`
- extend 掩膜：`data/interim/manual_masks/cra40/front2_extend/2017-06-22T18.nc`
- 子区域掩膜：`data/interim/manual_masks/cra40/front2_subareas/area2_lonlat_0622T18.nc`
- CRA40 相对湿度场：`data/raw/cra40/CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`

### 2.4 中文路径兼容提醒

这个项目位于中文目录下。对 Windows 来说，PowerShell 能看到文件，不代表 `xarray/netCDF4/cfgrib/pygrib` 一定能直接正常读写这些文件。

当前项目已经提供了兼容层 [`nc_compat.py`](/H:/邢台观测站/CWR_project/meiyu_new/nc_compat.py)。实际使用中，优先采用：

```python
from pathlib import Path
from nc_compat import open_dataset_compat

ds = open_dataset_compat(Path("data/interim/manual_masks/cra40/front2/2017-06-22T18.nc"))
```

不建议把下面这种写法当成默认入口：

```python
import xarray as xr

ds = xr.open_dataset("data/interim/manual_masks/cra40/front2/2017-06-22T18.nc")
```

因为在当前中文项目路径下，这种直接打开方式已经真实出现过 `FileNotFoundError`。

## 3. 当前流水线能做什么

当前已经落地并验证过的主链路是：

`mask -> geometry -> profiles -> subareas -> statistics -> diagnostics`

对应模块如下：

- `inventory`：检查 `raw / interim / processed` 三类目录及环境依赖
- `masks`：解析当前案例所需的主掩膜、extend 掩膜、子区域掩膜
- `geometry`：从主掩膜提取边界，拟合中心线，生成切线/法线采样框架
- `profiles`：基于 3D 场沿切线抽取剖面 bundle
- `subareas`：根据 sections 之间的关系，在主掩膜内部筛出子区域
- `statistics`：基于主掩膜或子区域掩膜，对网格场做掩膜平均
- `diagnostics`：基于剖面 bundle 产出最小研究辅助图件

当前 `runner` 现在已经能做三层事情：

1. 基础层：
   读取配置、建立输出目录、生成 `inventory` 与 `masks` 摘要
2. 串联层：
   对当前已验证案例继续执行 `geometry -> profiles -> subareas -> statistics -> diagnostics`
3. 调度层：
   支持单 manifest、多个 manifest 批量运行，以及有限的 `--override key=value` 临时参数覆盖

已验证的完整案例包括：

- `CRA40 + front2 + 2017-06-22T18 + rh`
- `CRA40 + front1 + 2017-06-22T18 + rh / temp / w`
- `CRA40 + front1 + 2017-06-22T12 + rh / temp / w`
- `CRA40 + front2 + 2017-06-23T00 + rh`
- `ERA5 + front2 + 2017-06-22T18 + rh / temp / w`
- `ERA5 + front1 + 2017-06-22T18 + rh / temp / w`

也就是说：

- 如果你想快速检查整个最小链路是否还能跑通，可以直接先跑 `runner`
- 如果你想改参数、换变量、观察每一步中间对象，仍然建议按步骤调用模块函数

## 4. 最小可运行示例

### 命令行运行

如果你已经有可用的 `cwr_py312` 环境，也可以直接从终端跑当前这条已验证链路。CLI 的真实入口是 `python -m pipeline.runner --manifest <path> [<path> ...] [--override key=value]`，下面给几个最小例子：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml
```

关闭 `subareas`，但保留 `statistics`：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml --override steps.subareas=false --override steps.statistics=true
```

改几何切分数：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml --override params.geometry.n_sections=6
```

运行 `front1 V1` 多变量个例（含 `rh / temp / w` 三变量剖面、子区域统计与最小 diagnostics 图件）：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml
```

批量运行多个 manifest：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml manifests/cases/era5_front1_20170622T18.yml
```

这条命令会输出 JSON，里面包含 `case_name`、`geometry`、`profiles`、`subareas`、`statistics` 和 `diagnostics` 等摘要字段。IDE 里如果想逐步看中间对象，继续用下面的 Python 方式最方便。

下面给出一条当前项目内已经真实验证过的最小链路。建议先按这个案例跑通，再扩展到其他时次、其他变量、其他锋面。

### 4.1 第一步：读取配置并检查基础入口

```powershell
conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; import pprint; pprint.pp(run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml')))"
```

如果你要测试 runner 第二阶段的 step gating，可以在同一个已验证个例上显式传 `overrides`。下面这个例子关闭 `subareas`，但保留 `statistics`：

```powershell
conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; import pprint; pprint.pp(run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml'), overrides={'steps.subareas': False, 'steps.statistics': True}))"
```

这条命令直接从 `manifests/cases/cra40_front2_20170622T18.yml` 进入当前已验证个例，不再要求先手动读取 `pipeline/schemas/pipeline_config.yaml`。默认基线下，真实 smoke 的摘要应当包含：

- `geometry.centerline_points == 8`
- `geometry.section_shape == [8, 9]`
- `profiles.variable == 'rh'`
- `profiles.bundle_shape == [8, 9, 37]`
- `subareas.mask_shape == [81, 141]`
- `statistics.front_mean == 85.81288001650856`
- `statistics.subarea_mean == 87.94710636138916`

当前这套摘要语义里，步骤状态会显式区分为 `completed`、`skipped`、`partial`：

- `completed`：该步骤已经执行完成，摘要里对应结果可直接使用
- `skipped`：该步骤被 `overrides` 或 step gating 关掉，没有执行
- `partial`：主链路仍然跑通，但可选分析链只完成了部分步骤，摘要里会保留已完成的 key，并用状态说明未完成部分

当 `subareas` 关闭而 `statistics` 仍开启时，`statistics.front_mean` 会保留，`statistics.subarea_mean` 会是 `None`。也就是说，默认基线下会同时看到 `front_mean + subarea_mean`，但一旦把 `subareas` 关掉而保留 `statistics`，就只保留 `front_mean`，`subarea_mean` 显式变成 `None`，顶层摘要 key 仍然固定不变。

你正常会看到六类关键信息：

- `case_name`，当前应为 `cra40_front2_2017-06-22T18`
- `masks`，应包含 `front_mask / extend_mask / subarea_mask`
- `geometry`，当前应能看到 `centerline_points == 8`、`section_shape == [8, 9]`
- `profiles`，当前应能看到 `variable == 'rh'`、`bundle_shape == [8, 9, 37]`
- `subareas`，当前应能看到 `mask_shape == [81, 141]`
- `statistics`，在默认基线下应包含 `front_mean` 和 `subarea_mean`；如果关闭 `subareas`，则只保留 `front_mean`，`subarea_mean` 为 `None`

如果这一步失败，优先检查：

- 配置文件是否仍指向 `front2` 和 `2017-06-22T18`
- 三个掩膜文件是否都在项目内
- 当前配置是否仍处于已验证支持边界内

### 4.2 第二步：读取主掩膜并构建几何结果

```python
from pathlib import Path

from nc_compat import open_dataset_compat
from pipeline.steps.geometry import build_geometry_from_mask

mask_ds = open_dataset_compat(
    Path("data/interim/manual_masks/cra40/front2/2017-06-22T18.nc")
)
mask = mask_ds["ind_area_bool"].values.astype(bool)
lons = mask_ds["lon"].values
lats = mask_ds["lat"].values

geometry = build_geometry_from_mask(
    mask,
    lons,
    lats,
    degree=4,
    dense_points=1000,
    n_sections=8,
    distance=1.0,
    n_points=9,
    delta_x=0.1,
)

print(geometry.centerline_x.shape)
print(geometry.sampled_dx.shape)
```

这一阶段：

- 输入：主掩膜二维布尔场 + 对应经纬度坐标
- 调用：`build_geometry_from_mask(...)`
- 输出：`GeometryResult`

当前这个案例下，正常参考结果为：

- `geometry.centerline_x.shape == (8,)`
- `geometry.sampled_dx.shape == (8, 9)`

这说明：

- 中心线被等分成了 8 个 section 位置
- 每条法线方向采样了 9 个点

### 4.3 第三步：沿几何切线抽取 3D 剖面

```python
from pathlib import Path

from nc_compat import open_dataset_compat
from pipeline.steps.profiles import build_profile_bundle_from_field

rh_ds = open_dataset_compat(
    Path("data/raw/cra40/CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2")
)

field3d = rh_ds["r"].isel(isobaricInhPa=slice(0, 37)).sel(
    latitude=lats,
    longitude=lons,
    method="nearest",
).values
levels = rh_ds["isobaricInhPa"].isel(isobaricInhPa=slice(0, 37)).values

bundle = build_profile_bundle_from_field(
    "rh",
    field3d,
    levels,
    lats,
    lons,
    geometry,
)

print(bundle.variable)
print(bundle.values.shape)
```

这一阶段：

- 输入：3D 变量场、垂直层次、主掩膜网格坐标、几何结果
- 调用：`build_profile_bundle_from_field(...)`
- 输出：`ProfileBundle`

当前这个案例下，正常参考结果为：

- `bundle.variable == 'rh'`
- `bundle.values.shape == (8, 9, 37)`

可以把它理解成：

- 8 条 section
- 每条 section 上 9 个横向采样点
- 每个点有 37 个垂直层

### 4.4 第四步：根据 sections 在主掩膜内生成子区域

```python
import numpy as np

from pipeline.steps.subareas import build_subarea_mask

lon2d, lat2d = np.meshgrid(lons, lats)

submask = build_subarea_mask(
    lon2d,
    lat2d,
    mask,
    geometry,
    start_section=1,
    end_section=4,
)

print(submask.shape)
print(int(submask.sum()))
```

这一阶段：

- 输入：主掩膜所在网格、主掩膜布尔场、几何结果、起止切线编号
- 调用：`build_subarea_mask(...)`
- 输出：一个新的二维布尔掩膜

当前这个案例、当前参数下，正常参考结果为：

- `submask.shape == (81, 141)`
- `int(submask.sum()) == 48`

注意：`submask.sum()` 会随着 `n_sections / n_points / start_section / end_section` 的设置变化，不同参数下点数不同是正常现象。

### 4.5 第五步：对完整锋面区做掩膜平均

```python
from pipeline.steps.statistics import build_masked_mean

front_mean = build_masked_mean("rh", field3d[0], mask)
print(front_mean)
```

这一阶段：

- 输入：与主掩膜同网格的二维变量场 + 主掩膜
- 调用：`build_masked_mean(...)`
- 输出：一个浮点均值

当前这个案例下，使用 RH 第一个气压层时，正常参考结果约为：

- `85.81288`

### 4.6 第六步：对项目内静态子区域掩膜文件做掩膜平均

这一部分最容易出错，因为“主掩膜”和“子区域掩膜”不一定在同一网格上。
这里演示的是“项目里已经存在的静态子区域掩膜文件”这条单独流程，它可以用来复现旧工程里的子区域统计语义，但它和当前 `runner` 默认 `completed` 摘要中的 `statistics.subarea_mean` 不是同一件事。

当前项目中的这个真实案例就是这样：

- 主掩膜：`lat=81, lon=141`
- 子区域掩膜：`lat=164, lon=284`

所以不能把主掩膜对应的 `field3d[0]` 直接拿去和子区域掩膜相乘。必须先按子区域掩膜自己的坐标重新取场。

```python
from pathlib import Path

from nc_compat import open_dataset_compat
from pipeline.steps.statistics import build_masked_mean

sub_ds = open_dataset_compat(
    Path("data/interim/manual_masks/cra40/front2_subareas/area2_lonlat_0622T18.nc")
)
sub_bool = sub_ds["ind_area_bool"].values.astype(bool)
sub_lons = sub_ds["lon"].values
sub_lats = sub_ds["lat"].values

sub_field = rh_ds["r"].isel(isobaricInhPa=0).sel(
    latitude=sub_lats,
    longitude=sub_lons,
    method="nearest",
).values

sub_mean = build_masked_mean("rh", sub_field, sub_bool)
print(sub_mean)
```

当前这个案例下，静态子区域掩膜文件这条流程的参考结果约为：

- `79.697523`

而当前 `runner` 在默认 `completed` 情况下，使用的是“本次运行时根据 `geometry + start_section/end_section` 动态生成的 `submask`，并直接在主掩膜所在网格上计算子区域均值”这条语义；因此它的 `statistics.subarea_mean` 会是前面 4.1 小节列出的 `87.94710636138916`，不应与这里的 `79.697523` 混用。

## 5. 常见问题

### 5.1 找不到掩膜或原始数据

常见症状：

- `FileNotFoundError`
- `resolve_case_masks(...)` 报错
- `run_case(...)` 返回摘要里缺少预期路径

优先检查：

1. `manifests/cases/cra40_front2_20170622T18.yml` 是否仍然指向 `front2 + 2017-06-22T18`
2. 以下三个文件是否存在  
   `data/interim/manual_masks/cra40/front2/2017-06-22T18.nc`  
   `data/interim/manual_masks/cra40/front2_extend/2017-06-22T18.nc`  
   `data/interim/manual_masks/cra40/front2_subareas/area2_lonlat_0622T18.nc`
3. 原始 CRA40 文件是否在 `data/raw/cra40/`

### 5.2 中文路径下直接 `xr.open_dataset(...)` 失败

常见症状：

- 明明文件存在，但报 `FileNotFoundError`
- `netCDF4`、`cfgrib`、`pygrib` 在中文路径下行为异常

原因：

- 当前项目根路径含中文字符，部分后端在 Windows 下对中文绝对路径支持不稳定

处理方式：

- 统一优先使用 `open_dataset_compat(...)`
- 如果要写出新的 nc 文件，优先使用 `to_netcdf_compat(...)`

### 5.3 主掩膜和子区域掩膜不在同一网格

常见症状：

- 统计均值明显不合理
- 布尔掩膜与二维场形状对不上
- 结果虽然能算，但其实算错了

原因：

- 主掩膜和子区域掩膜可能来自不同范围、不同分辨率或不同 extend 处理

处理方式：

1. 先看掩膜自己的 `lat/lon` 或 `latitude/longitude`
2. 再让变量场按该掩膜坐标重新 `.sel(..., method='nearest')`
3. 然后再调用 `build_masked_mean(...)`

这一步不要偷懒直接复用“另一个网格上已经取好的场”。

### 5.4 `runner` 的支持边界

`runner` 已经是当前推荐的自动化入口，但它的边界仍然是“项目内已有资产 + manifest 明确描述 + 当前已迁移 step 能表达的分析链”。

`runner.py` 现在已经能串联当前已验证案例的：

- `inventory`
- `masks`
- `geometry`
- `profiles`
- `subareas`
- `statistics`
- `diagnostics`

第二阶段的语义是把基础链和分析链分开看：

- `inventory / masks / geometry` 仍然是必跑基础链
- `profiles / subareas / statistics / diagnostics` 属于可选分析链，是否执行由 manifest、`overrides` 和 step gating 控制
- 不管可选链是否关闭，顶层摘要 key 的结构保持不变，只是对应步骤的状态会落成 `completed / partial / skipped`

它已经覆盖当前的 front1/front2、CRA40/ERA5、`rh / temp / w` 和 diagnostics 主流程；如果你要继续做以下工作，仍然需要先扩展 manifest、数据资产或 step 实现：

- 新数据集或新的变量类型
- 尚未准备掩膜资产的新时次
- legacy 中未迁移的完整出图命名和产物组织
- 连续帧、组合剖面、人工识别辅助图等更复杂 diagnostics

这类扩展建议先在 `pipeline/core/*` 或 `pipeline/steps/*` 里补清楚科学语义，再把稳定入口接入 `runner`。

## 6. 输出与后续定位

### 6.1 新流水线输出目录

当前新流水线的 case 输出目录由 [`pipeline/core/paths.py`](/H:/邢台观测站/CWR_project/meiyu_new/pipeline/core/paths.py) 统一创建，典型结构为：

```text
outputs/
  figures/
    cra40_front2_2017-06-22T18/
      diagnostics/
      profiles/
      subareas/
      statistics/
  logs/
  manifests/
```

### 6.2 哪些结果目前还是“内存对象”

当前这条最小链路里，有些步骤已经有标准化 Python 对象，但不是每一步都自动写成文件：

- `GeometryResult`
- `ProfileBundle`
- `submask` 布尔数组
- `front_mean / sub_mean` 数值结果

`diagnostics` 步骤已经能够自动落盘 PNG 图件到 `outputs/figures/<case_name>/diagnostics/`。

### 6.3 标准化剖面与 ERA5 动力诊断

完整运行 `era5_front2_20170628T18`：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/era5_front2_20170628T18.yml
```

会在 `diagnostics/` 新增两组产品：

- 标准化横跨锋面剖面：`sections_rh_signed_km`、`sections_temp_signed_km`、`sections_w_signed_km`、`sections_rh_thetae_signed_km`、`sections_w_thetae_signed_km`。
- ERA5 850 hPa 动力图：`850_thetae_gradient_wind`、`850_divergence`、`850_moisture_flux_convergence`、`850_frontogenesis`。

标准化剖面以拟合锋心为 `0 km`，冷侧为负、暖湿侧为正。程序比较剖面外侧两个采样点的 θe 中位数；端点差小于 `0.5 K` 时不强行判断方向，并在对应面板标注 `orientation unresolved`。

动力图只使用 manifest 声明的 `data/raw/era5/201706.nc` 中同一时次、同一层次的 `u / v / q / t / r`，不会把 ERA5 风场与 CRA40 热力场混算。符号约定如下：

- 散度小于零表示辐合；
- 水汽通量辐合大于零表示水汽汇聚；
- 运动学锋生函数大于零表示锋生、小于零表示锋消。

`diagnostics.components` 会分别记录 `base / signed_sections / era5_dynamics`。显式请求的 ERA5 动力输入缺失或无效时，基础图仍保留，但总状态变为 `partial`，具体原因写入 `diagnostics.warnings`。

### 6.4 哪些结果目前仍主要参考 legacy 输出

如果你现在需要直接对照旧工程成果，仍建议参考：

- legacy 图片输出：`outputs/legacy_figures/`
- 旧工程跑通基线文档：[legacy_project_smoke_status_2026-07-05.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/legacy_project_smoke_status_2026-07-05.md)
- 分层设计文档：[2026-07-05-layered-pipeline-design.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/2026-07-05-layered-pipeline-design.md)

### 6.5 这份 guide 用完之后，下一步看什么

如果你的目标是：

- 先把当前最小链路跑通：继续按本指南执行即可
- 理解新模块之间的边界和设计关系：下一步看“技术架构与旧工程映射”文档
- 把其他时次、其他变量、其他锋面接进来：优先仿照已有 manifest 扩展；如果现有 step 语义不足，再补模块和测试

## 7. 一句话总结

当前这版新流水线已经适合做“项目内、真实数据、manifest 驱动”的自动化研究入口。最稳妥的使用方式，是先围绕 `CRA40 front2 2017-06-22T18` 跑通 `mask -> geometry -> profiles -> subareas -> statistics -> diagnostics`，确认输出和摘要结构，再使用已有 manifest 扩展到 front1、ERA5、多变量和批量案例。

