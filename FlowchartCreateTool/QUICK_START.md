# FlowchartCreateTool 快速入门指南

## 安装

无需安装，直接将 `FlowchartCreateTool` 文件夹放在您的项目目录中即可使用。

## 基本用法

### 1. 简单示例

```python
from FlowchartCreateTool import FlowchartConverter
import json

# 读取输入数据
with open('output.json', 'r', encoding='utf-8') as f:
    input_json = json.load(f)

# 创建转换器
converter = FlowchartConverter()

# 执行转换
output_json = converter.convert(input_json)

# 保存结果
with open('output_flowchart.json', 'w', encoding='utf-8') as f:
    json.dump(output_json, f, indent=2, ensure_ascii=False)

print("转换完成！")
```

### 2. 在现有代码中使用

如果您之前使用的是 `code_to_flowchart.py`：

```python
# 旧代码
from old_version.code_to_flowchart import FixedCodeToFlowchartConverter

converter = FixedCodeToFlowchartConverter()
output = converter.convert(input_json)

# 新代码（只需修改导入）
from FlowchartCreateTool import FlowchartConverter

converter = FlowchartConverter()
output = converter.convert(input_json)
```

### 3. 直接运行

使用提供的入口文件：

```bash
python code_to_flowchart_refactored.py
```

或者直接运行转换器模块：

```bash
python -m FlowchartCreateTool.converter
```

## 输入格式

输入应该是一个JSON列表，每个元素代表一个代码语句：

```json
[
    {
        "tag": "i/o",
        "translated": "输入 x",
        "original_unit": "input x"
    },
    {
        "tag": "process",
        "translated": "x = x + 1",
        "original_unit": "x = x + 1"
    }
]
```

### 支持的语句类型

- **i/o**: 输入输出语句
- **process**: 处理语句
- **condition**: 条件判断（if）
- **branch**: 分支（else）
- **loop**: 循环（for/while）

## 输出格式

输出是一个包含节点和连接的JSON对象：

```json
{
    "version": "1.0",
    "items": [
        {
            "id": "...",
            "type": "start",
            "x": -4600.0,
            "y": -4800.0,
            "width": 125,
            "height": 75,
            "text": "开始"
        }
        // ... 更多节点
    ],
    "connections": [
        {
            "start_item_id": "...",
            "start_point_type": "down",
            "end_item_id": "...",
            "end_point_type": "up",
            "label": null
        }
        // ... 更多连接
    ]
}
```

## 高级用法

### 自定义坐标和偏移

```python
from FlowchartCreateTool import FlowchartConverter

converter = FlowchartConverter()

# 修改起始坐标
converter.current_x = -5000.0
converter.current_y = -5000.0

# 修改偏移量
converter.level_height = 150  # 层级间距
converter.condition_offset_x = 300  # if块x偏移
converter.loop_offset_x = 150  # 循环体x偏移

# 执行转换
output = converter.convert(input_json)
```

### 使用独立的管理器

```python
from FlowchartCreateTool import NodeManager, ConnectionManager, ContextManager

# 创建管理器
node_mgr = NodeManager()
conn_mgr = ConnectionManager(node_mgr)
ctx_mgr = ContextManager()

# 创建节点
start_node = node_mgr.create_node("start", "开始", -4600, -4800)
end_node = node_mgr.create_node("end", "结束", -4600, -4600)

# 添加连接
conn_mgr.add_connection(start_node["id"], "down", end_node["id"], "up")

# 获取所有节点和连接
nodes = node_mgr.get_all_nodes()
connections = conn_mgr.get_all_connections()
```

## 常见问题

### Q: 如何处理中文编码问题？
A: 确保在读写JSON文件时使用 `encoding='utf-8'`：
```python
with open('file.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
```

### Q: 输出的坐标为负数是否正常？
A: 是的，默认起始坐标为 (-4600, -4800)，这是为了适配特定的流程图编辑器。

### Q: 如何调整节点间距？
A: 修改 `converter.level_height` 属性：
```python
converter.level_height = 200  # 增大间距
```

### Q: 支持哪些节点类型？
A: 支持以下类型：
- `start`: 开始节点
- `end`: 结束节点
- `input`: 输入输出节点
- `process`: 处理节点
- `decision`: 判断节点

## 测试

运行测试套件：

```bash
python test_refactored_flowchart.py
```

预期输出：
```
============================================================
FlowchartCreateTool 重构验证测试
============================================================
...
[SUCCESS] 所有测试通过！重构成功！
```

## 更多资源

- **完整文档**: 查看 `README.md`
- **API文档**: 查看各模块的docstring
- **示例代码**: 查看 `test_refactored_flowchart.py`
- **重构总结**: 查看 `../REFACTORING_SUMMARY.md`

## 获取帮助

如果遇到问题：

1. 检查输入JSON格式是否正确
2. 查看日志文件（如果启用了日志）
3. 运行测试套件确保安装正确
4. 查看源代码中的注释和文档字符串

## 贡献

如果您发现bug或有改进建议，欢迎：

1. 创建issue报告问题
2. 提交pull request改进代码
3. 完善文档和示例

---

**版本**: 1.0.0  
**更新日期**: 2025-11-04

