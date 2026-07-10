# Meiyu Front Research Pipeline

这个仓库包含旧工程 `legacy` 代码和围绕已验证个例拆出来的新流水线 `pipeline/`。

## 命令行入口

IDE 里仍然可以直接调用 `run_case_from_manifest(...)`；如果要从终端直接跑已验证个例，可以用 `pipeline.runner` 的 CLI 入口：

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170622T18.yml
```

更完整的命令行示例和 IDE 用法说明，见 [docs/pipeline_quickstart_zh.md](docs/pipeline_quickstart_zh.md)。
