# 梅雨锋区域掩码网页工具

在项目根目录运行：

```powershell
python web_mask_picker/app.py
```

也可双击 `web_mask_picker/start_web_mask_picker.bat`，它会以当前已验证具备
网页依赖的 `D:\anaconda\python.exe` 启动服务并打开页面。

然后打开 <http://127.0.0.1:5000>。导入**二次处理后得到的诊断变量**
NetCDF（不是原始 CRA40 文件），其应含一维 `lat/lon`（或
`latitude/longitude`）坐标；选择变量后即可选点。

- 单点模式：点击格点切换选择状态；支持撤回。
- 框选添加：左键拖拽添加矩形内格点；右键拖动平移，滚轮缩放。
- 下载的 `meiyu_front_mask.nc` 包含布尔变量 `meiyu_front_mask`，其形状与
  当前所选诊断量的纬度/经度格点严格一致，并沿用原始格点坐标。

默认使用 `YlOrRd`，与本项目熵位温梯度结果图一致；其他物理诊断量可手动
切换色标和显示范围。

## 导入问题日志

服务启动后会写入 `web_mask_picker/logs/app.log`。日志记录文件名、文件大小、
维度、可用变量、切片、选取格点数，以及失败时完整异常堆栈；不记录诊断场的
具体数值。日志还会记录浏览器是否选中文件、是否请求二维场、是否完成 Canvas
绘制及 JavaScript 异常。日志单文件最大 2 MB，保留 3 个历史副本。
