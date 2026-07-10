# Runner Manifest 化设计文档

## 1. 目标

本设计文档定义新流水线下一轮重构的第一个明确落点：把当前 `runner` 从“硬编码的已验证案例串联器”升级为“消费 manifest 的受限串联入口”。

这轮设计要解决的不是全部科学流程自动化，而是下面三个更基础的问题：

1. 如何把“一个研究案例默认怎么跑”从 `runner.py` 中抽离出来。
2. 如何在不破坏复现性的前提下，允许少量运行时参数覆盖，支持科研试验。
3. 如何在不推翻现有 `pipeline/steps/` 的情况下，为后续 `front1 / ERA5 / 更多变量` 扩展铺好配置层边界。

本轮的核心思想是：

- `manifest` 负责描述案例默认定义。
- `loader` 负责把 manifest 解析为真实运行配置。
- `runner` 只负责消费配置并执行步骤。
- 现有 `steps` 继续作为科学处理的核心可复用模块。

## 2. 当前状态

当前项目已经具备以下基础：

- 旧工程主要脚本已完成项目内路径修复与多轮冒烟验证。
- 新流水线已经形成 `inventory -> masks -> geometry -> profiles -> subareas -> statistics` 的模块边界。
- `pipeline/runner.py` 已经能够串联当前唯一完成真实验证的链路：
  - `dataset = cra40`
  - `front_id = front2`
  - `target_time = 2017-06-22T18`
  - `variable = rh`
- 当前 runner 已返回结构化摘要，并已有测试覆盖。

但当前仍存在一个明显结构性问题：

- 运行案例的定义仍然埋在代码里，而不是显式写在一个可复用、可审阅、可复制的案例声明文件中。

这会带来三个后果：

1. 用户无法一眼看出“这个案例为什么这样运行”。
2. 后续接入新案例时，容易继续在 `runner.py` 中堆叠条件分支。
3. 复现与试验的边界不清晰，容易把临时改动混入长期案例定义。

## 3. 本轮范围

本轮只做 manifest 化的最小可用版本，严格限制在下面内容内：

- 支持一个已验证案例 manifest。
- manifest 中包含案例元信息、step 开关、step 参数默认值、输入数据定位。
- 允许少量运行时 overrides。
- runner 改为从 manifest 解析后的运行配置启动。
- 保持当前已验证的 `CRA40 front2 2017-06-22T18` 链路继续可运行、可测试、可说明。

## 4. 不在本轮范围内的内容

以下内容明确不纳入本轮：

- `front1` 正式接入新 runner。
- `ERA5` 正式接入新 runner。
- `diagnostics` 模块接入统一入口。
- 完整输出命名规范与全量落盘体系。
- 多案例批处理调度器。
- 通用 CLI 产品化。
- 一次性支持全部变量，如 `temp / w / thetae`。

原因很明确：本轮目标是把“已验证链路的案例声明层”建立起来，而不是提前把未验证链路一并抽象。

## 5. 备选方案比较

### 5.1 方案 A：继续扩展 `pipeline/config.py`

做法：

- 仍由 `pipeline/config.py` 同时承担数据模型、manifest 解析、路径解析、运行时覆盖逻辑。

优点：

- 改动最少。
- 短期推进最快。

缺点：

- `config.py` 责任会继续膨胀。
- manifest 语义与运行时语义会缠在一起。
- 后续扩展 `front1 / ERA5` 时，结构仍容易回到“单文件堆逻辑”。

### 5.2 方案 B：新增独立 manifest 层

做法：

- 新增案例 manifest 文件目录。
- 新增 manifest 数据模型层。
- 新增 manifest 读取与解析层。
- runner 只消费解析后的运行配置。

优点：

- 配置声明、解析逻辑、执行逻辑边界清晰。
- 最符合研究流水线的复用需求。
- 便于未来扩展更多案例而不污染 runner。

缺点：

- 本轮文件数会增加。
- 需要补一层测试。

### 5.3 方案 C：一步做到 manifest + 输出规范 + 批处理入口

做法：

- 在本轮同时完成案例声明、输出命名规范、批量调度器。

优点：

- 形式上更完整。

缺点：

- 范围过大。
- 会把尚未稳定的输出规范与已验证链路强行绑在一起。
- 不利于当前阶段的稳健推进。

### 5.4 采用方案

本轮采用方案 B。

原因：

- 它同时满足“研究可复用”和“当前范围可控”。
- 它能为后续扩展留出清晰接口，但不提前承诺不成熟能力。

## 6. 设计总览

本轮采用“轻量双层配置，但先落一层文件”的结构：

- manifest 文件保存案例默认定义。
- 运行时允许用少量 overrides 临时覆盖。
- 解析层把二者合成为最终运行配置。
- runner 只消费最终运行配置。

这意味着：

- 复现时以 manifest 为准。
- 试验时通过 overrides 做小幅扰动。
- 二者不混在同一个长期文件里。

## 7. Manifest 结构设计

### 7.1 文件位置

建议新增目录：

- `manifests/cases/`

首个样例文件建议命名为：

- `manifests/cases/cra40_front2_20170622T18.yml`

命名目标不是追求绝对通用，而是让研究者看到文件名就知道它描述的是哪一个已验证案例。

### 7.2 Manifest 承载内容

一个案例 manifest 至少包含以下四类信息：

1. 案例元信息
2. step 开关
3. step 默认参数
4. 输入数据定位

### 7.3 推荐结构

推荐 manifest 具有类似下面的逻辑层次：

```yaml
case_name: cra40_front2_20170622T18
dataset: cra40
front_id: front2
target_time: 2017-06-22T18

steps:
  inventory: true
  masks: true
  geometry: true
  profiles: true
  subareas: true
  statistics: true

params:
  geometry:
    degree: 4
    dense_points: 1000
    n_sections: 8
    distance: 1.0
    n_points: 9
    delta_x: 0.1
  profiles:
    variables:
      - rh
  subareas:
    start_section: 1
    end_section: 4

inputs:
  rh:
    logical_name: CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2
  front_mask:
    relative_path: data/processed/front_masks/front2/20170622T18/area_lonlat_0622T18.nc
```

上面只是结构示意，不要求首轮就支持所有嵌套写法的自由扩张，但字段语义要固定。

### 7.4 字段语义原则

字段设计必须遵守以下原则：

- `case_name / dataset / front_id / target_time` 代表案例身份，不是运行扰动项。
- `steps.*` 代表是否执行某步骤。
- `params.*` 代表该步骤的默认参数。
- `inputs.*` 代表该案例显式依赖的输入资产定位。

## 8. 输入数据定位策略

### 8.1 采用双模式解析

本轮 manifest 的输入定位采用双模式：

1. 相对路径模式
2. 逻辑名模式

并允许二者共存。

### 8.2 相对路径模式

适用于：

- 已经迁移进项目目录的数据。
- 需要显式指向某个固定文件的案例资产。

优点：

- 可读性直接。
- 对迁移旧工程资产非常顺手。

### 8.3 逻辑名模式

适用于：

- 已经有项目级路径函数可解析的标准原始资料。
- 希望保留与 `project_paths.py` 一致的数据组织习惯。

优点：

- 不把底层绝对路径写死到 manifest 中。
- 便于与已有 `cra40_file(...)`、后续其他路径函数保持一致。

### 8.4 解析优先级

建议优先级为：

1. 如果显式提供 `relative_path`，优先解析项目内相对路径。
2. 否则如果提供 `logical_name`，交给路径解析函数解析。
3. 如果二者都缺失，则报错。

这样既兼容旧工程迁移，也保留新流水线的项目路径抽象能力。

## 9. 运行时覆盖设计

### 9.1 覆盖目标

运行时覆盖只为支持科研试验，不为替代 manifest。

因此本轮 overrides 的目标是：

- 小范围修改少量 step 参数或 step 开关。
- 不改变 manifest 的核心身份字段。

### 9.2 推荐支持范围

本轮建议仅支持以下类型字段覆盖：

- `steps.profiles`
- `steps.subareas`
- `params.geometry.n_sections`
- `params.geometry.delta_x`
- `params.subareas.start_section`
- `params.subareas.end_section`
- `params.profiles.variables`

也可以支持更多同类字段，但必须保持“已知字段、显式覆盖”的原则。

### 9.3 明确不支持的覆盖

本轮不建议支持：

- 自动新增未知字段。
- 任意深层结构变形。
- 动态改写案例身份字段后继续静默运行。
- 用 overrides 直接重写完整输出规范。

### 9.4 合并原则

覆盖策略采用“manifest 默认值 + 运行时浅覆盖到指定字段”。

这样做的好处是：

- 案例定义仍稳定可复现。
- 运行时试验改动足够轻。
- 维护者更容易判断某次运行到底改了什么。

## 10. 代码边界设计

本轮不推翻现有 `pipeline/`，只在其旁边补一层 manifest 解析能力。

### 10.1 新增目录与文件

建议新增：

- `manifests/cases/*.yml`
- `pipeline/manifest_models.py`
- `pipeline/manifest_loader.py`

### 10.2 现有文件职责调整

#### `pipeline/manifest_models.py`

职责：

- 定义 manifest 对应的数据结构。
- 定义解析后运行配置对应的数据结构。
- 明确 step 开关、step 参数、输入定位的字段边界。

它回答的问题是：

- 一个案例 manifest 在程序内部应该长什么样。

#### `pipeline/manifest_loader.py`

职责：

- 读取 manifest 文件。
- 做基础字段校验。
- 解析输入定位。
- 应用运行时 overrides。
- 生成 runner 可直接消费的运行配置对象。

它回答的问题是：

- 文字配置怎样变成最终运行配置。

#### `pipeline/config.py`

职责调整建议：

- 从“唯一配置入口”收缩为“兼容层或共享配置类型层”。

这意味着它不再继续膨胀为 manifest 总控制器，而是保留最适合复用的共享内容。

#### `pipeline/runner.py`

职责：

- 不再自己写死案例常量。
- 消费 manifest loader 返回的最终运行配置。
- 按 step 开关串联执行。
- 返回结构化摘要。

它回答的问题是：

- 给定一个已解析配置，应该怎样按顺序执行。

#### `pipeline/steps/*`

职责不变：

- 继续只承担单个科学处理环节的职责。

它们不负责：

- 解析 manifest。
- 判断案例身份。
- 处理运行时 overrides。

## 11. Runner 行为设计

### 11.1 本轮 runner 定位

manifest 化之后的 runner 仍然不是通用总控器，而是“受支持边界明确的已验证链路执行器”。

这点必须保留，因为当前真正完成真实验证的只有：

- `cra40`
- `front2`
- `2017-06-22T18`
- `rh`

### 11.2 支持边界

即使改为 manifest 驱动，本轮 runner 仍应对超出边界的配置明确报错，而不是静默尝试泛化。

报错原则：

- 如果案例身份超出当前已验证集合，直接提示“本版本 runner 只支持已验证链路”。
- 如果某个输入缺失，直接指出缺的是哪个输入。
- 如果 manifest 开启了当前 runner 尚未支持的变量或步骤，也应明确失败，而不是半运行。

### 11.3 输出形态

本轮 runner 继续返回结构化摘要，而不是一步落盘全部结果文件。

摘要中继续至少保留：

- `case_name`
- `inventory`
- `masks`
- `outputs`
- `geometry`
- `profiles`
- `subareas`
- `statistics`

这样可以保证：

- 快速使用文档不需要重写使用方式。
- 当前测试基线可以平滑迁移。
- 后续若加入更完整落盘，也可以在摘要壳层外增量扩展。

## 12. 测试与验证设计

### 12.1 需要新增的测试

本轮至少补充三类测试：

1. manifest 读取测试
2. overrides 合并测试
3. runner 消费 manifest 测试

### 12.2 manifest 读取测试

验证点：

- 能正确读取案例元信息。
- 能正确读取 steps。
- 能正确读取 params。
- 能正确读取 inputs。

### 12.3 overrides 合并测试

验证点：

- 已知字段可覆盖。
- 未知字段会报错。
- 覆盖不会静默改写案例身份字段。

### 12.4 runner 消费 manifest 测试

验证点：

- 当前已验证案例仍可跑通。
- 返回摘要仍包含 `geometry / profiles / subareas / statistics`。
- 不支持的案例身份会明确报错。

### 12.5 真实案例基线

本轮仍沿用当前已验证基线作为真实 smoke 参考：

- `geometry.centerline_points == 8`
- `geometry.section_shape == [8, 9]`
- `profiles.bundle_shape == [8, 9, 37]`
- `subareas.mask_shape == [81, 141]`
- `subareas.selected_points == 48`
- `statistics.front_mean` 约为 `85.81288`
- `statistics.subarea_mean` 约为 `79.697523`

不要求每个数值都在单元测试中做高精度硬编码断言，但应作为真实运行回归参考。

## 13. 成功标准

如果本轮设计落实成功，应达到以下效果：

1. 一个研究案例的默认运行方式可以写在独立 manifest 文件中，而不再埋在 `runner.py` 里。
2. 用户能够在不改案例文件的情况下，对少量 step 参数做临时试验覆盖。
3. runner 的职责被压缩为“执行”，而不是继续兼做配置声明层。
4. 当前已验证的 `CRA40 front2 2017-06-22T18` 链路仍然能跑通并保持已有摘要基线。
5. 后续扩展 `front1 / ERA5 / 更多变量` 时，优先扩的是 manifest 与 step 支持边界，而不是继续堆硬编码分支。

## 14. 下一阶段接口

本轮完成后，下一阶段才适合继续推进：

- 为 `front1` 增加 manifest 样例与支持边界。
- 为 `ERA5` 增加输入定位与步层验证。
- 为 `diagnostics` 增加独立 step 模块。
- 把输出命名与落盘规范单独做成下一轮设计。
- 在 manifest 稳定后，再考虑多案例 runner 或批处理入口。

换句话说，本轮 manifest 化不是终局，而是把“案例声明层”从旧式硬编码中独立出来，作为后续研究流水线真正可复用的起点。
