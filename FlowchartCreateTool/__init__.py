"""
FlowchartCreateTool - 代码到流程图转换工具包

这个包提供了将代码结构转换为流程图的功能。
主要功能：
- 代码结构分析
- 流程图节点创建
- 控制流处理（if-else、循环）
- 连接线管理

使用示例：
    from FlowchartCreateTool import FlowchartConverter
    
    converter = FlowchartConverter()
    output = converter.convert(input_json)
"""

from .converter import FlowchartConverter
from .node_manager import NodeManager
from .connection_manager import ConnectionManager
from .context_manager import ContextManager
from .control_flow import IfElseProcessor, LoopProcessor

__version__ = "1.0.0"
__author__ = "Auto Render C Team"

__all__ = [
    'FlowchartConverter',
    'NodeManager',
    'ConnectionManager',
    'ContextManager',
    'IfElseProcessor',
    'LoopProcessor'
]

