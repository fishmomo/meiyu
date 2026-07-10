"""根据掩膜统计结果绘制锋面区域的时序图。"""

import os
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from project_paths import legacy_figure_path, mask_stats_glob

np.set_printoptions(
    suppress=True,
    formatter={"float_kind": "{:.6f}".format},
)

# 旧脚本默认汇总 CRA40 锋面2主区域统计结果，这里仅将数据源路径切到项目内新目录。
csvFilePath_list = sorted(glob(mask_stats_glob("CRA40_mask", "fengmian2*.csv")))
for i, ifpath in enumerate(csvFilePath_list):
    if i == 0:
        df = pd.read_csv(ifpath)
    else:
        df_temp = pd.read_csv(ifpath)
        df = pd.concat([df, df_temp], ignore_index=True)

fig = plt.figure(figsize=(5, 3), dpi=200)
ax = fig.add_subplot(1, 1, 1)
ax.plot(df["CWR"].values / df["dxy"].values[0], label="CWR", marker="^")
ax.set_xticks(np.arange(0, df.shape[0], 3))
ax.set_xticklabels(
    [os.path.basename(x)[-11:-4] for x in csvFilePath_list][::3],
    rotation=45,
    fontsize=12,
)
ax.set_ylabel("mm", fontsize=12)
ax.legend()
plt.savefig(legacy_figure_path("PPT_pic", filename="fengmian2-CRA40-CWR.png"), bbox_inches="tight")
