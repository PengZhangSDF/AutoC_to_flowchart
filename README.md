# AutoC_to_flowchart V1.0.2

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Platform](https://img.shields.io/badge/-Windows-blue?style=flat-square&logo=windows)

**一款简易的 C++ 代码自动转换流程图工具**

将 C++ 代码自动解析并生成美观、可编辑的流程图

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用指南](#-使用指南) • [贡献](#-贡献)

</div>

---

## 📖 项目简介
### AI真是太好用辣~本项目约90%由AI编写，而剩下10%是作者修BUG修的~
### ~~这个MD大部分也是AI写的~~
AutoC_to_flowchart 是一个基于 Python 和 PyQt6 开发的桌面应用程序，旨在帮助开发者和学生快速将 C++ 代码转换为标准的流程图。该工具特别适用于：

- 🎓 **学习辅助**：节约你在大学的时间！

##  功能特性

###  核心功能

- **✅ 自动代码解析**
  - 智能识别 C++ 语法结构（if-else、for、while 等，不支持 switch）
  - 自动提取控制流和判断条件
  - 支持嵌套结构和复杂逻辑
  - 支持多函数解析，可按需启用/关闭

- **✅ 流程图生成**
  - 符合国标的流程图图形（矩形、菱形、平行四边形、跑道形）
  - 自动布局，智能连线避免重叠
  - 支持 `break` 和 `continue` 语句的正确跳转
  - 多函数流程图自动横向排布，仅在存在 `return` 时保留“结束”节点

- **✅ 可视化编辑**
  - 拖拽移动元素
  - 手动添加/删除流程图模块
  - 自定义连接线和标签
  - 实时编辑元素文本
  - 主界面提供多函数识别快速切换按钮

- **✅ 智能画布**
  - 动态调整画布大小
  - Ctrl + 滚轮缩放视图
  - 鼠标拖动平移画布
  - 自动适应所有元素

- **✅ 导入导出**
  - 导出为高质量 PNG 图片
  - 保存/加载流程图项目（JSON 格式）
  - 从 C++ 代码一键导入

### 🎨 界面特色

- 简洁现代的 UI 设计
- 背景网格辅助对齐
- 右侧工具栏快捷操作，包含多函数快捷开关
- 实时文本编辑预览
- 设置窗口新增“关于我们”页集中展示提示与开源信息

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- Windows 10/11、macOS、或 Linux

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/PengZhangSDF/AutoC_to_flowchart.git
cd AutoC_to_flowchart
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

如果没有 `requirements.txt`，请手动安装：

```bash
pip install PyQt6
```

3. **运行程序**

```bash
python main.py
```

## 📝 使用指南

### 方法一：从 C++ 代码导入

1. 将你的 C++ 代码保存好为一个.c或者.cpp文件
2. 点击右侧工具栏的 **"从代码导入"** 按钮
3. 程序会自动解析代码并生成流程图
4. 可以手动调整布局和连接线

**示例代码：**

```cpp
#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    if (n > 0) {
        cout << "正数";
    } else if (n < 0) {
        cout << "负数";
    } else {
        cout << "零";
    }
    
    return 0;
}
```

### 方法二：手动创建流程图

1. 使用顶部工具栏添加模块：
   - **开始/结束模块**：跑道形（开始、结束）
   - **处理/语句模块**：矩形（赋值、计算）
   - **判断/循环模块**：菱形（条件判断）
   - **输入/输出模块**：平行四边形（I/O 操作）

2. 连接元素：
   - 点击起始元素的**红色连接点**
   - 再点击目标元素的**红色连接点**
   - 系统会自动创建连接线

3. 编辑文本：
   - 选中元素
   - 在右侧文本框中输入内容
   - 文本会实时更新

### 基本操作

| 操作         | 快捷方式          |
|------------|---------------|
| 缩放画布       | `Ctrl` + 鼠标滚轮 |
| 平移画布       | 鼠标左键拖动        |
| 移动元素       | 鼠标左键拖动        |
| 删除元素       | 右键点击 → 删除     |
| 删除连接线      | 右键点击连接线 → 删除  |
| 添加/删除连接线文字 | 右键点击连接线 → 菜单  |

### 导出流程图

1. 点击顶部工具栏的 **"导出为图片"** 按钮
2. 选择保存位置和文件名
3. 图片将以 PNG 格式导出（白色背景，高分辨率）

### 保存与加载

- **保存项目**：点击 "保存为文件"，保存为 JSON 格式
- **加载项目**：点击 "从保存的文件打开"，加载之前的项目

## 🏗️ 项目结构

```
AutoC_to_flowchart/
├── main.py                          # 主程序入口（简洁版）
├── config.yaml                      # 配置文件（可自定义参数）
├── config_manager.py                # 配置管理器
├── GUI/                             # GUI 图形界面包（模块化）
│   ├── __init__.py                  # GUI 包初始化
│   ├── items/                       # 图形元素模块
│   │   ├── __init__.py
│   │   ├── constants.py             # 常量定义（元素类型、连接点）
│   │   ├── connection_point.py      # 连接点类
│   │   ├── flowchart_item.py        # 流程图元素类
│   │   └── connection_line.py       # 连接线和标签类
│   ├── scene/                       # 场景模块
│   │   ├── __init__.py
│   │   └── flowchart_scene.py       # 流程图场景类
│   ├── view/                        # 视图模块
│   │   ├── __init__.py
│   │   └── flowchart_view.py        # 流程图视图类
│   └── window/                      # 主窗口模块
│       ├── __init__.py
│       └── main_window.py           # 主窗口类
├── code_to_flowchart_refactored.py  # 代码转流程图主流程
├── C_FIXED.py                       # C++ 代码预处理
├── JSON_transfer.py                 # C++ 代码解析为 JSON
├── FlowchartCreateTool/             # 流程图生成核心模块
│   ├── converter.py                 # JSON 转流程图转换器
│   ├── node_manager.py              # 节点管理
│   ├── connection_manager.py        # 连接管理
│   ├── control_flow/                # 控制流处理
│   │   ├── if_else_processor.py     # if-else 逻辑
│   │   └── loop_processor.py        # 循环逻辑
│   └── utils/                       # 工具函数
│       └── position_calculator.py   # 位置计算
├── io_operations.py                 # 文件 I/O 操作
├── logger.py                        # 日志系统
├── requirements.txt                 # 项目依赖
├── Cfile.cpp                        # 输入的 C++ 代码文件
├── output.json                      # 中间解析结果
├── output_flowchart.json            # 生成的流程图数据
└── README.md                        # 本文件
```

### 📦 GUI 模块说明

| 模块 | 功能 |
|------|------|
| **items** | 所有图形元素的创建、显示和交互 |
| **scene** | 场景管理、连接处理、画布控制 |
| **view** | 视图显示、缩放、平移 |
| **window** | 主窗口、工具栏、菜单管理 |

### ⚙️ 配置系统

项目支持通过 `config.yaml` 文件自定义各种参数：

```yaml
# 主要配置项
window:        # 窗口大小和位置
scene:         # 画布参数（起点、尺寸、边距、网格）
parser:        # 多函数识别开关
item:          # 元素默认尺寸、连接点参数
connection:    # 箭头、线条、路径偏移量
layout:        # 多个函数流程的布局间距
view:          # 缩放因子、拖动模式
export:        # 导出边距、默认文件名
text:          # 字体、大小、边距
tips:          # 提示信息、开源地址
```

**详细配置说明**：查看 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)

**修改配置的方法**：
1. **使用设置窗口（推荐）**：点击右侧工具栏的 "⚙️ 设置" 按钮，在GUI中修改配置
2. **手动编辑**：直接编辑 `config.yaml` 文件

**快速修改示例**：
- 窗口太小？在设置中修改画布尺寸
- 连接线重叠？调整连接线路径偏移量
- 字体太小？增大文本字体大小
- 想换配色？在设置窗口的颜色下拉框中选择新的预设
- 想一次生成所有函数的流程图？在解析设置中开启或使用主界面快捷开关


## 🛠️ 技术栈

- **语言**：Python 3.8+（python 3.11开发）
- **GUI 框架**：PyQt6
- **图形绘制**：QPainter, QGraphicsScene
- **代码解析**：正则表达式 + 自定义解析器
- **数据格式**：JSON
- **配置管理**：PyYAML


## 🤝 贡献

欢迎贡献代码！

1. Fork 本项目
2. 创建新分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 贡献方向

- 🌐 支持更多编程语言（Python、Java、JavaScript）
- 🎨 更多流程图主题和样式
- 📊 支持导出为 SVG、PDF 格式
- 🌍 更多的流程图格式的导入
- 🐛 修复 Bug 和优化性能

## 📄 许可证

本项目采用 GPL-3.0 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

**PengZhangSDF**

- GitHub: [@PengZhangSDF](https://github.com/PengZhangSDF)
- 项目地址: [AutoC_to_flowchart](https://github.com/PengZhangSDF/AutoC_to_flowchart)

## 🙏 致谢

感谢所有为本项目做出贡献的开发者！

## 📮 反馈与支持

如果你在使用过程中遇到问题或有改进建议：

- 📝 提交 [Issue](https://github.com/PengZhangSDF/AutoC_to_flowchart/issues)
- 💡 发起 [Discussion](https://github.com/PengZhangSDF/AutoC_to_flowchart/discussions)
- ⭐ 如果觉得项目有用，请给个 Star！

---
## 本项目87-92%的代码由AI编写
### 使用到的AI：
- 豆包及其Trae CN
- deepseek
- Cursor
<div align="center">

**Design with ❤️ by PengZhangSDF**

如果这个项目对你有帮助，请考虑给它一个 ⭐ Star

</div>

