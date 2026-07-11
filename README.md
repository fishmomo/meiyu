# Meiyu Front Research Pipeline

这个仓库包含旧工程 `legacy` 代码和围绕已验证个例拆出来的新流水线 `pipeline/`。

## 命令行入口

IDE 里仍然可以直接调用 `run_case_from_manifest(...)`；如果要从终端直接跑已验证个例，可以用 `pipeline.runner` 的 CLI 入口：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml
```

运行 `front1 V1` 多变量个例：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml
```

运行 ERA5 front2 个例：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/era5_front2_20170622T18.yml
```

## 当前已验证案例

| manifest | dataset | front | time | variables |
|----------|---------|-------|------|-----------|
| `cra40_front2_20170622T18.yml` | CRA40 | front2 | 2017-06-22T18 | rh |
| `cra40_front1_20170622T18.yml` | CRA40 | front1 | 2017-06-22T18 | rh, temp, w |
| `cra40_front1_20170622T12.yml` | CRA40 | front1 | 2017-06-22T12 | rh, temp, w |
| `cra40_front2_20170623T00.yml` | CRA40 | front2 | 2017-06-23T00 | rh |
| `era5_front2_20170622T18.yml` | ERA5 | front2 | 2017-06-22T18 | rh, temp, w |
| `era5_front1_20170622T18.yml` | ERA5 | front1 | 2017-06-22T18 | rh, temp, w |

更完整的命令行示例和 IDE 用法说明，见 [docs/pipeline_quickstart_zh.md](docs/pipeline_quickstart_zh.md)。

## 协作文档

如果后续要让其他 Agent 或协作者参与本项目，建议优先阅读：

- [docs/agent_collaboration_guide_zh.md](docs/agent_collaboration_guide_zh.md)
- [docs/agent_project_status_zh.md](docs/agent_project_status_zh.md)
