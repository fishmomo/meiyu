"""绘制锋面2应用统计图，逻辑同样可用于锋面1。"""

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

# 保留旧脚本“取 fengmain2-new 并丢弃末尾 3 个文件”的处理方式，只改项目内路径。
csvFilePath_list = sorted(
    glob(mask_stats_glob("CRA40_mask", "fengmain2-new", "fengmian2*.csv"))
)[:-3]
for i, ifpath in enumerate(csvFilePath_list):
    if i == 0:
        df = pd.read_csv(ifpath)
    else:
        df_temp = pd.read_csv(ifpath)
        df = pd.concat([df, df_temp], ignore_index=True)

fig = plt.figure(figsize=(9, 12), dpi=200)
varname = ["PEh", "CEv", "aveMv", "aveMh", "GMv", "GMh", "RCv", "RCh", "MC", "SP", "Dv", "Dh"]
for i in range(len(varname)):
    ax = fig.add_subplot(6, 2, i + 1)
    if varname[i] not in ["PEh", "CEv", "RCv", "RCh"]:
        if varname[i] == "Dv":
            ax.plot((df["INv"] - df["OTv"]) / df["dxy"], label=varname[i], marker="^")
        elif varname[i] == "Dh":
            ax.plot((df["INh"] - df["OTh"]) / df["dxy"], label=varname[i], marker="^")
        elif varname[i] == "SP" or varname[i] == "MC":
            ax.plot(df[varname[i]] / df["dxy"], label=varname[i], marker="^")
            ax.set_ylim([0, 20])
        elif varname[i] == "GMv":
            temp = df[varname[i]].to_numpy(copy=True)
            temp[-1] = np.nan
            ax.plot(temp / df["dxy"], label=varname[i], marker="^")
        else:
            ax.plot(df[varname[i]] / df["dxy"], label=varname[i], marker="^")
        ax.set_ylabel("mm", fontsize=12)
    elif varname[i] == "RCv":
        temp = df[varname[i]].to_numpy(copy=True)
        temp[temp > 1000] = np.nan
        ax.plot(temp, label=varname[i], marker="^")
        ax.set_ylabel("day", fontsize=12)
    elif varname[i] == "RCh":
        temp = df[varname[i]].to_numpy(copy=True)
        temp[temp > 1000] = np.nan
        ax.plot(temp, label=varname[i], marker="^")
        ax.set_ylabel("hour", fontsize=12)
    else:
        ax.plot(df[varname[i]], label=varname[i], marker="^")
        ax.set_ylabel("%", fontsize=12)
    if i >= len(varname) - 2:
        ax.set_xticks(np.arange(0, df.shape[0], 3))
        ax.set_xticklabels(
            [os.path.basename(x)[-11:-4] for x in csvFilePath_list][::3],
            rotation=45,
            fontsize=12,
        )
    else:
        ax.set_xticks([])
    ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(legacy_figure_path("PPT_pic", filename="fengmian2-CRA40-mask-new.png"), bbox_inches="tight")

fig = plt.figure(figsize=(6, 6), dpi=200)
ax = fig.add_subplot(2, 1, 1)
ax.plot(df["CWR"].values / df["dxy"], label="CWR", marker="^")
ax.set_ylabel("mm", fontsize=12)
ax.set_xticks([])
ax.legend()

ax2 = fig.add_subplot(2, 1, 2)
ax2.plot(df["SP"].values / df["dxy"], label="SP", marker="^")
ax2.set_ylabel("mm", fontsize=12)
ax2.set_xticks(np.arange(0, df.shape[0], 3))
ax2.legend()
ax2.set_xticklabels(
    [os.path.basename(x)[-11:-4] for x in csvFilePath_list][::3],
    rotation=45,
    fontsize=12,
)
plt.savefig(legacy_figure_path("PPT_pic", filename="fengmian2-CRA40-CWR+SP.png"), bbox_inches="tight")
