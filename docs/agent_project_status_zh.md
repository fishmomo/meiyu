# 梅雨锋项目 Agent 进度与待办状态

## 1. 文档目的

这份文档用于告诉后续 Agent 当前项目已完成的内容和稳定基线。

## 2. 当前已完成的稳定基线

### 2.1 新流水线架构

全部 7 个 step 已落地并验证：
`inventory -> masks -> geometry -> profiles -> subareas -> statistics -> diagnostics`

### 2.2 已验证案例（共 6 个）

| manifest | dataset | front | time | variables |
|----------|---------|-------|------|-----------|
| `cra40_front2_20170622T18.yml` | CRA40 | front2 | 2017-06-22T18 | rh |
| `cra40_front1_20170622T18.yml` | CRA40 | front1 | 2017-06-22T18 | rh, temp, w |
| `cra40_front1_20170622T12.yml` | CRA40 | front1 | 2017-06-22T12 | rh, temp, w |
| `cra40_front2_20170623T00.yml` | CRA40 | front2 | 2017-06-23T00 | rh |
| `era5_front2_20170622T18.yml` | ERA5 | front2 | 2017-06-22T18 | rh, temp, w |
| `era5_front1_20170622T18.yml` | ERA5 | front1 | 2017-06-22T18 | rh, temp, w |

### 2.3 完整能力清单

| 能力 | 状态 | 提交 |
|------|------|------|
| front1 掩膜认证 + 多变量映射 | ✓ | `73fada7` ~ `21f899e` |
| front1/front2 runner 主线 | ✓ | `ef9fc97` |
| 子区域逐变量统计 | ✓ | `e03287f` |
| 最小 diagnostics 图件 | ✓ | `aae8820` |
| 文档补齐 | ✓ | `1378233` |
| 多时次支持 | ✓ | `650c53f` |
| ERA5 双源接入 | ✓ | `85f274e` |
| diagnostics 完整图件（3 类） | ✓ | `040ff81` |
| 文档同步 + hPa 标签 + ERA5 测试 | ✓ | `4143f8c` |
| 批处理调度 + CSV 导出 + ERA5 front1 | ✓ | `b3c574a` |

## 3. 命令行入口

```powershell
# 单案例
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml

# 批量运行
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml manifests/cases/era5_front1_20170622T18.yml

# 带 override
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml --override steps.statistics=false
```

## 4. 当前未完成的后续主线

- **更多时次的 ERA5 case**（ERA5 掩膜 front1 14 时次、front2 28 时次，当前仅验证了 1 个时次/锋面）
- **更丰富的诊断图件**（连续帧、组合剖面、人工识别辅助图等）
- **统计分析深化**（多时次时序均值、跨锋面对比等）

## 5. 一句话状态总结

项目已具备 CRA40 + ERA5 双源、front1 + front2 双锋面、多时次、多变量（rh/temp/w）、全部 7 个 pipeline step 串联、批处理调度、CSV 导出和三类诊断图件自动落盘的完整能力。全量测试 70 passed。
