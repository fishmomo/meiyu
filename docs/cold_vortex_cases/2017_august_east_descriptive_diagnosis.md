# 2017 年 8 月东北冷涡个例：描述性诊断文字素材

## 个例、资料与口径

- 时段：2017-08-12 00 UTC 至 2017-08-14 06 UTC，共 10 个 6 小时时次。
- 资料：CRA40 0.25°×0.25°再分析资料，经 90°E–170°E、20°N–70°N 裁剪后用于诊断。
- 主体区：沿用已确定的唯一冷涡事件轨迹及其 `core_body` 掩膜，不以固定外围窗口替代主体。
- 物理量和统计口径与 2021 年 9 月个例一致：850 hPa 水汽通量辐合、700 hPa 气压垂直速度、主体内覆盖率、强度加权质心、两质心间距，以及条件平均强度。

## 直接结果

事件轨迹包含生成 1 时次、发展 6 时次、成熟 1 时次和消散 2 时次。标记的成熟时刻为 2017-08-13 18 UTC；当时主体面积约 0.76×10^6 km²，主体区平均 500 hPa 相对涡度约 4.19×10^-5 s^-1。全过程主体面积约在 0.76–0.85×10^6 km²之间变化，未出现 2021 年 9 月个例那样的显著面积收缩。

生成、发展、成熟、消散阶段中，辐合—上升共现区覆盖率分别为 25.43%、27.33%、26.39% 和 32.98%。共现覆盖率在消散阶段增加，但这不代表耦合强度增强：正 MFC 区条件平均强度由生成期 1.53×10^-7 s^-1 降至成熟期 0.69×10^-7 s^-1、消散期 0.62×10^-7 s^-1；上升区条件平均强度则由 0.103 Pa s^-1 降至 0.048 和 0.070 Pa s^-1。

水汽辐合质心与上升质心的平均间距，在生成、发展、成熟、消散阶段分别约为 0.18、0.33、0.35、0.22 个主体等效半径。二者全程仍位于同一主体尺度内；成熟阶段相对错位较大，消散阶段间距有所回落。

## 可用表述

该个例中，辐合—上升共现区的面积并未在消散阶段同步缩小，但其局地条件平均强度相对生成和发展阶段已减弱。因此，覆盖范围和局地强度必须分开解释：后期较大的共现面积不能单独作为冷涡动力或水汽作用维持增强的证据。该过程的主要特征是辐合与上升仍在主体内共存，但局地强度总体减弱，且成熟阶段两者的空间配置存在较明显的相对错位。

## 结论边界与数据

本材料仅支持主体环流、水汽通量辐合和垂直运动之间的描述性讨论；不包含降水、蒸发、云水或整层水分收支。

- `data/processed/cold_vortex/event_diagnostics/2017_august_east/core_diagnostics_timeseries.csv`
- `data/processed/cold_vortex/event_diagnostics/2017_august_east/core_moisture_ascent_coupling.csv`
- `data/processed/cold_vortex/event_diagnostics/2017_august_east/core_evolution_timeseries.png`
- `data/processed/cold_vortex/event_diagnostics/2017_august_east/formation_maturity_terminal_structure.png`
- `data/processed/cold_vortex/event_diagnostics/2017_august_east/core_moisture_ascent_coupling_timeseries.png`
- `data/processed/cold_vortex/event_diagnostics/2017_august_east/core_moisture_ascent_intensity_timeseries.png`
