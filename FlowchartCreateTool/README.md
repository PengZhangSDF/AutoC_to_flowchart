# FlowchartCreateTool

代码到流程图转换工具包 - 模块化重构版本

## 目录结构

```
FlowchartCreateTool/
├── __init__.py               # 包初始化，暴露核心类
├── converter.py              # 主转换器类（协调各模块）
├── node_manager.py           # 节点创建与管理
├── connection_manager.py     # 连接线创建与管理
├── context_manager.py        # 语句上下文跟踪与回溯
├── control_flow/             # 控制流（if-else/循环）处理
│   ├── __init__.py
│   ├── if_else_processor.py  # if-else及嵌套结构处理
│   └── loop_processor.py     # 循环结构处理
├── utils.py                  # 通用工具函数
└── README.md                 # 本文件
```

## 模块说明

### 1. converter.py - 主转换器
负责协调所有模块，执行代码到流程图的转换。

**主要类：**
- `FlowchartConverter`: 主转换器类

**主要方法：**
- `convert(input_json)`: 执行转换的主入口

### 2. node_manager.py - 节点管理器
负责流程图节点的创建、ID生成和管理。

**主要类：**
- `NodeManager`: 节点管理器

**主要方法：**
- `create_node(node_type, text, x, y)`: 创建节点
- `get_node_by_id(node_id)`: 根据ID查找节点
- `get_all_nodes()`: 获取所有节点

### 3. connection_manager.py - 连接管理器
负责节点间连接线的创建和管理。

**主要类：**
- `ConnectionManager`: 连接管理器

**主要方法：**
- `add_connection(start_id, start_point, end_id, end_point, label)`: 添加连接
- `connection_exists(start_id, end_id)`: 检查连接是否存在
- `get_all_connections()`: 获取所有连接

### 4. context_manager.py - 上下文管理器
负责跟踪和管理语句处理的上下文信息。

**主要类：**
- `ContextManager`: 上下文管理器

**主要方法：**
- `register_statement_first_node(index, node)`: 注册语句的第一个节点
- `register_loop_condition_node(statement, node)`: 注册循环条件节点
- `add_pending_reconnect(info)`: 添加待处理的回连信息

### 5. control_flow/if_else_processor.py - if-else处理器
处理if-else条件分支及其嵌套结构的回连逻辑。

**主要类：**
- `IfElseProcessor`: if-else结构处理器

**主要方法：**
- `handle_if_else_reconnect(...)`: 处理if-else的回连
- `handle_nested_if_else_reconnect(...)`: 处理嵌套if-else的回连

### 6. control_flow/loop_processor.py - 循环处理器
处理for和while循环结构。

**主要类：**
- `LoopProcessor`: 循环结构处理器

**主要方法：**
- `calculate_loop_offset(loop_item, base_offset, is_while)`: 计算循环偏移
- `add_loop_body_reconnection(...)`: 添加循环体的回连

### 7. utils.py - 工具函数
提供通用的辅助函数。

**主要函数：**
- `is_statement_in_loop(statement, loop_item)`: 检查语句是否在循环中
- `is_statement_in_block(statement, block)`: 检查语句是否在块中
- `find_all_nested_if_else(statement, result)`: 查找所有嵌套if-else
- `count_statement_chain(node)`: 计算语句链长度

## 使用方法

### 基本使用

```python
from FlowchartCreateTool import FlowchartConverter
import json

# 读取输入JSON
with open('output.json', 'r', encoding='utf-8') as f:
    input_json = json.load(f)

# 创建转换器并执行转换
converter = FlowchartConverter()
output_json = converter.convert(input_json)

# 保存结果
with open('output_flowchart.json', 'w', encoding='utf-8') as f:
    json.dump(output_json, f, indent=2, ensure_ascii=False)
```

### 高级使用

如果需要自定义行为，可以直接使用各个管理器：

```python
from FlowchartCreateTool import (
    NodeManager,
    ConnectionManager,
    ContextManager,
    IfElseProcessor,
    LoopProcessor
)

# 创建管理器
node_manager = NodeManager()
connection_manager = ConnectionManager(node_manager)
context_manager = ContextManager()

# 创建处理器
if_else_processor = IfElseProcessor(
    node_manager,
    connection_manager,
    context_manager
)

# ... 自定义处理逻辑
```

## 重构优势

1. **模块化设计**：每个模块职责单一，易于理解和维护
2. **可扩展性**：新功能可以通过添加新模块实现，不影响现有代码
3. **可测试性**：各模块可以独立测试
4. **可重用性**：各管理器和处理器可以在其他项目中重用
5. **代码清晰**：避免了单文件2000+行的庞大代码

## 与原版本的兼容性

重构后的代码完全保持了与原`code_to_flowchart.py`的功能一致性。所有的：
- 节点创建规则
- 连接逻辑
- if-else处理
- 循环处理
- 嵌套结构处理

都与原版本完全相同，只是代码组织更加清晰。

## 维护建议

1. 添加新功能时，优先考虑在哪个模块中实现
2. 如果功能不属于现有模块，考虑创建新模块
3. 保持各模块的职责单一
4. 添加单元测试以确保功能正确性

## 版本信息

- **版本**: 1.0.0
- **重构日期**: 2025-11-04
- **原始版本**: code_to_flowchart.py

