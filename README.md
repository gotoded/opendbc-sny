<div align="center" style="text-align: center;">

<h1>Opendbc</h1>
<p>
  <b>opendbc 是一个用于控制汽车的 Python API。</b>
  <br>
  控制油门、刹车、转向等。读取速度、转向角度等信息。
</p>

<h3>
  <a href="https://docs.comma.ai">文档</a>
  <span> · </span>
  <a href="https://github.com/commaai/openpilot/blob/master/docs/CONTRIBUTING.md">贡献</a>
  <span> · </span>
  <a href="https://discord.comma.ai">Discord</a>
</h3>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![X Follow](https://img.shields.io/twitter/follow/comma_ai)](https://x.com/comma_ai)
[![Discord](https://img.shields.io/discord/469524606043160576)](https://discord.comma.ai)

<br>
<h3><i>如何移植一款车型 — Jason Young, COMMA_CON 2023</i></h3>
<a href="https://www.youtube.com/watch?v=XxPS5TpTUnI&t=142s">
  <img src="https://github.com/user-attachments/assets/ae89198e-561b-4210-a0d4-ccecd917577d" alt="▶ How to Port a Car - Jason Young, COMMA_CON 2023" width="800">
</a>
<br>

<h3><i>我们如何控制汽车？— Robbe Derks, COMMA_CON 2021</i></h3>
<a href="https://www.youtube.com/watch?v=nNU6ipme878">
  <img src="https://github.com/user-attachments/assets/28c40bc0-7884-47e9-b392-f47f03190497" alt="▶ How Do We Control The Car? - Robbe Derks, COMMA_CON 2021" width="800">
</a>
<br>

</div>

---

自 2016 年以来，大多数汽车都配备了电子控制的转向、油门和刹车，这得益于 [LKAS](https://en.wikipedia.org/wiki/Lane_departure_warning_system) 和 [ACC](https://en.wikipedia.org/wiki/Adaptive_cruise_control) 系统。本项目的目标是支持控制每一辆这类汽车的转向、油门和刹车。

虽然主要重点是支持 [openpilot](https://github.com/commaai/openpilot) 的 ADAS 接口，我们也致力于读取和写入尽可能多的信息（如电动车充电状态、车门锁定/解锁等），以便构建最好的车辆管理应用。

---

本 README 和[支持车型列表](docs/CARS.md)是 opendbc 项目的全部文档。使用、贡献和扩展 opendbc 所需的一切都在这些文档中。

## 快速开始

```bash
git clone https://github.com/commaai/opendbc.git
cd opendbc

# 你可能只需要运行这个命令。这是一个集依赖安装、编译、代码检查和测试于一体的脚本，也是在 CI 中运行的命令
./test.sh

# 以下是它运行的各个命令
pip3 install -e .[testing,docs]  # 安装依赖
scons -j8                        # 使用 8 核编译
unittest-parallel                # 运行测试
lefthook run lint                # 运行代码检查
```

[`examples/`](examples/) 目录包含了一些小程序示例，可以从汽车读取状态并控制转向、油门和刹车。
[`examples/joystick.py`](examples/joystick.py) 允许你使用操纵杆控制汽车。

### 项目结构
* [`opendbc/dbc/`](opendbc/dbc/) 是 [DBC](https://en.wikipedia.org/wiki/CAN_bus#DBC_(CAN_Database_Files)) 文件的仓库
* [`opendbc/can/`](opendbc/can/) 是用于解析和构建 DBC 文件中 CAN 消息的库
* [`opendbc/car/`](opendbc/car/) 是使用 Python 与汽车交互的高级库
* [`opendbc/safety/`](opendbc/safety/) 是 `opendbc/car/` 支持的所有汽车的功能安全模块

## 如何移植一款车型

本指南涵盖了从为新车型添加支持到改进现有车型（例如添加纵向控制或雷达解析）的所有内容。如果与你的车型相似的车型已经兼容，那么大部分工作可能已经为你完成了。

在最基本的情况下，一个车型移植将控制汽车的转向。一个"完整"的车型移植将包括：横向控制、纵向控制、良好的横向和纵向调优、雷达解析（如果配备）、模糊指纹识别等。新车支持文档将清楚地说明每辆车的支持级别。

### 连接到汽车

第一步是使用 comma four 和汽车线束连接到汽车。汽车线束让你连接到两个不同的 CAN 总线，并分离其中一个总线以发送我们自己的控制消息。

如果幸运的话，与你的汽车兼容的线束可能已经设计好并在 comma.ai/shop 上出售。如果不太幸运，请从 comma.ai/shop 购买"开发者线束"，并压接你需要的任何连接器。

### 移植结构

根据品牌不同，大部分基本结构可能已经存在。

车型移植的全部内容位于 `opendbc/car/<brand>/`：
* `carstate.py`：使用汽车的 DBC 文件从 CAN 流中解析相关信息
* `carcontroller.py`：输出 CAN 消息以控制汽车
* `<brand>can.py`：围绕 DBC 文件构建 CAN 消息的轻量级 Python 辅助函数
* `fingerprints.py`：用于识别车型的 ECU 固件版本数据库
* `interface.py`：与汽车交互的高级类
* `radar_interface.py`：解析雷达数据
* `values.py`：枚举该品牌支持的车型

### 逆向工程 CAN 消息

首先，录制一条包含许多有趣事件的路程：启用 LKAS 和 ACC，将方向盘转到两个极限位置等。然后，在 [cabana](https://github.com/commaai/openpilot/tree/master/tools/cabana) 中加载该路程。

### 调优

#### 纵向控制

使用[纵向机动测试](https://github.com/commaai/openpilot/tree/master/tools/longitudinal_maneuvers)报告来评估你的汽车的纵向控制并进行调优。

## 贡献

所有 opendbc 开发都在 GitHub 和 [Discord](https://discord.comma.ai) 上进行。请查看 `#dev-opendbc-cars` 频道和 `Vehicle Specific` 板块。

### 路线图

短期目标
- [ ] `pip install opendbc`
- [ ] 100% 类型覆盖
- [ ] 100% 行覆盖
- [ ] 使车型移植更容易：重构、工具、测试和文档
- [ ] 更好地展示所有支持汽车的状态：https://github.com/commaai/opendbc/issues/1144

长期目标
- [ ] 将支持扩展到每辆具有 LKAS + ACC 接口的汽车
- [ ] 自动横向和纵向控制/调优评估
- [ ] [横向](https://blog.comma.ai/090release/#torqued-an-auto-tuner-for-lateral-control)和纵向控制的自动调优
- [ ] [自动紧急制动](https://en.wikipedia.org/wiki/Automated_emergency_braking_system)

欢迎对以上任何内容做出贡献。

## 安全模型

当 [panda](https://comma.ai/shop/panda) 使用 [opendbc 安全固件](opendbc/safety)启动时，默认处于 `SAFETY_SILENT` 模式。在 `SAFETY_SILENT` 模式下，CAN 总线被强制静默。要发送消息，必须选择一个安全模式。某些安全模式（例如 `SAFETY_ALLOUTPUT`）在发布固件中被禁用。要使用它们，请编译并刷入你自己的版本。

安全模式可选支持 `controls_allowed`，它根据板上的可自定义状态允许或阻止一部分消息。

## 代码严谨性

opendbc 安全固件是为与 [openpilot](https://github.com/commaai/openpilot) 和 [panda](https://github.com/commaai/panda) 配合使用而编写的。安全固件通过其安全模型，提供并执行 [openpilot 安全](https://github.com/commaai/openpilot/blob/master/docs/SAFETY.md)。由于其关键功能，`safety` 文件夹中的应用代码严谨性必须保持高标准。

以下是我们实施的 [CI 回归测试](https://github.com/commaai/opendbc/actions)：
* 由 [cppcheck](https://github.com/danmar/cppcheck/) 执行通用静态代码分析。
* 此外，[cppcheck](https://github.com/danmar/cppcheck/) 有一个特定的插件用于检查 [MISRA C:2012](https://misra.org.uk/) 违规。参见[当前覆盖率](opendbc/safety/tests/misra/coverage_table)。
* 编译器选项相对严格：强制执行 `-Wall -Wextra -Wstrict-prototypes -Werror` 标志。
* [安全逻辑](opendbc/safety)通过每种支持车型变体的[单元测试](opendbc/safety/tests)进行测试和验证。

上述测试本身也经过测试：
* MISRA 覆盖率的[变异测试](opendbc/safety/tests/misra/test_mutation.py)
* 安全单元测试强制执行 100% 行覆盖率

此外，我们在汽车接口库上运行 [ruff linter](https://github.com/astral-sh/ruff) 和 [ty](https://github.com/astral-sh/ty)。

### 赏金

每个车型移植都有资格获得赏金：
* $2000 - [任意汽车品牌/平台移植](https://github.com/orgs/commaai/projects/26/views/1?pane=issue&itemId=47913774)
* $250 - [任意车型移植](https://github.com/orgs/commaai/projects/26/views/1?pane=issue&itemId=47913790)
* $300 - [逆向工程新的控制消息](https://github.com/orgs/commaai/projects/26/views/1?pane=issue&itemId=73445563)

除了标准赏金外，我们还为更受欢迎的汽车提供更高价值的赏金。请参阅 [comma.ai/bounties](comma.ai/bounties)。

## 常见问题

***我该如何使用？*** [comma four](https://comma.ai/shop/comma-four) 是专门设计用于运行和开发 opendbc 和 openpilot 的最佳方式。

***支持哪些汽车？*** 请参阅[支持车型列表](docs/CARS.md)。

***我可以为我的汽车添加支持吗？*** 可以，大多数汽车支持来自社区。请阅读[这里](https://github.com/commaai/opendbc/blob/docs/README.md#how-to-port-a-car)的指南。

***哪些汽车可以被支持？*** 任何具有 LKAS 和 ACC 的汽车。更多信息请参阅[这里](https://github.com/commaai/openpilot/blob/master/docs/CARS.md#dont-see-your-car-here)。

***这是如何工作的？*** 简而言之，我们设计了硬件来替代你汽车内置的车道保持和自适应巡航功能。请参阅[这个演讲](https://www.youtube.com/watch?v=FL8CxUSfipM)了解深入解释。

***是否有添加汽车支持的时间表或路线图？*** 没有，大多数汽车支持来自社区，comma 负责最终的安全和质量验证。社区车型移植越完整，汽车越受欢迎，我们就越有可能选择它作为下一个验证对象。

### 术语

* **port（移植）**：指特定汽车的集成和支持
* **lateral control（横向控制）**：即转向控制
* **longitudinal control（纵向控制）**：即油门/刹车控制
* **fingerprinting（指纹识别）**：识别汽车的自动过程
* **[LKAS](https://en.wikipedia.org/wiki/Lane_departure_warning_system)**：车道保持辅助系统
* **[ACC](https://en.wikipedia.org/wiki/Adaptive_cruise_control)**：自适应巡航控制
* **[harness（线束）](https://comma.ai/shop/car-harness)**：连接到汽车并拦截 ADAS 消息的汽车特定硬件
* **[panda](https://github.com/commaai/panda)**：用于连接汽车 CAN 总线的硬件
* **[ECU](https://en.wikipedia.org/wiki/Electronic_control_unit)**：汽车内部的计算机或控制模块
* **[CAN bus（CAN 总线）](https://en.wikipedia.org/wiki/CAN_bus)**：连接汽车中 ECU 的总线
* **[cabana](https://github.com/commaai/openpilot/tree/master/tools/cabana#readme)**：我们的 CAN 消息逆向工程工具
* **[DBC file（DBC 文件）](https://en.wikipedia.org/wiki/CAN_bus#DBC)**：包含 CAN 总线上消息定义的文件
* **[openpilot](https://github.com/commaai/openpilot)**：opendbc 支持的汽车的 ADAS 系统
* **[comma](https://github.com/commaai)**：opendbc 背后的公司
* **[comma four](https://comma.ai/shop/comma-four)**：用于运行 openpilot 的硬件

### 更多资源

* [*我们如何控制汽车？*](https://www.youtube.com/watch?v=nNU6ipme878&pp=ygUoY29tbWEgY29uIDIwMjEgaG93IGRvIHdlIGNvbnRyb2wgdGhlIGNhcg%3D%3D) 作者 [@robbederks](https://github.com/robbederks)，来自 COMMA_CON 2021
* [*如何移植一款车型*](https://www.youtube.com/watch?v=XxPS5TpTUnI&t=142s&pp=ygUPamFzb24gY29tbWEgY29u) 作者 [@jyoung8607](https://github.com/jyoung8607)，来自 COMMA_CON 2023
* [commaCarSegments](https://huggingface.co/datasets/commaai/commaCarSegments)：来自 300 种不同车型的大量 CAN 数据集
* [cabana](https://github.com/commaai/openpilot/tree/master/tools/cabana#readme)：我们的 CAN 消息逆向工程工具
* [can_print_changes.py](https://github.com/commaai/openpilot/blob/master/selfdrive/debug/can_print_changes.py)：比较两次驾驶中的整个 CAN 总线差异，例如一次没有 LKAS，一次有 LKAS
* [longitudinal maneuvers](https://github.com/commaai/openpilot/tree/master/tools/longitudinal_maneuvers)：用于评估和调优纵向控制的工具
* [opendbc data](https://commaai.github.io/opendbc-data/)：纵向机动评估的仓库

## 加入我们 — [comma.ai/jobs](https://comma.ai/jobs)

comma 正在招聘工程师来开发 opendbc 和 [openpilot](https://github.com/commaai/openpilot)。我们喜欢招聘贡献者。
