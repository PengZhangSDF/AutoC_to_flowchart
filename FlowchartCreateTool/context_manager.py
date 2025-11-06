"""
语句上下文跟踪与回溯模块
负责管理语句处理过程中的上下文信息
"""
from typing import Dict, Any, List


class ContextManager:
    """上下文管理器：负责跟踪和管理语句处理的上下文信息"""
    
    def __init__(self):
        """初始化上下文管理器"""
        # 用于跟踪语句上下文，支持回溯
        # 存储 (statement, parent_block, block_index, context_type, next_node) 的栈
        # context_type: 'loop', 'if_block', 'else_block', 'main' 或 None
        self.statement_context_stack = []
        
        # 待处理的 if-else 回连信息
        self.pending_if_else_reconnects = []
        
        # 语句索引 -> 第一个节点的映射
        self.statement_first_nodes = {}
        
        # 循环语句 -> 循环条件节点的映射（使用id(statement)作为key）
        self.loop_condition_nodes = {}
        
        # 输入JSON的引用，用于查找
        self.input_json = None
    
    def push_context(self, statement: Dict[str, Any], parent_block: List[Dict[str, Any]], 
                    block_index: int, context_type: str = None, next_node: Dict[str, Any] = None):
        """
        将上下文信息压入栈
        
        参数:
            statement: 当前语句
            parent_block: 父代码块
            block_index: 在父块中的索引
            context_type: 上下文类型
            next_node: 下一个节点
        """
        self.statement_context_stack.append(
            (statement, parent_block, block_index, context_type, next_node)
        )
    
    def pop_context(self):
        """从栈中弹出上下文信息"""
        if self.statement_context_stack:
            return self.statement_context_stack.pop()
        return None
    
    def get_current_context(self):
        """获取当前上下文（不弹出）"""
        if self.statement_context_stack:
            return self.statement_context_stack[-1]
        return None
    
    def add_pending_reconnect(self, reconnect_info: Dict[str, Any]):
        """
        添加待处理的if-else回连信息
        
        参数:
            reconnect_info: 包含回连所需信息的字典
        """
        self.pending_if_else_reconnects.append(reconnect_info)
    
    def register_statement_first_node(self, statement_index: int, node: Dict[str, Any]):
        """
        注册语句的第一个节点
        
        参数:
            statement_index: 语句索引
            node: 第一个节点
        """
        self.statement_first_nodes[statement_index] = node
    
    def get_statement_first_node(self, statement_index: int) -> Dict[str, Any]:
        """
        获取语句的第一个节点
        
        参数:
            statement_index: 语句索引
            
        返回:
            Dict: 第一个节点，如果未找到则返回None
        """
        return self.statement_first_nodes.get(statement_index)
    
    def register_loop_condition_node(self, loop_statement: Dict[str, Any], 
                                    condition_node: Dict[str, Any]):
        """
        注册循环语句的条件节点
        
        参数:
            loop_statement: 循环语句
            condition_node: 条件节点
        """
        self.loop_condition_nodes[id(loop_statement)] = condition_node
    
    def get_loop_condition_node(self, loop_statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取循环语句的条件节点
        
        参数:
            loop_statement: 循环语句
            
        返回:
            Dict: 条件节点，如果未找到则返回None
        """
        return self.loop_condition_nodes.get(id(loop_statement))
    
    def set_input_json(self, input_json: List[Dict[str, Any]]):
        """
        设置输入JSON的引用
        
        参数:
            input_json: 输入的JSON数据
        """
        self.input_json = input_json
    
    def reset(self):
        """重置上下文管理器状态"""
        self.statement_context_stack = []
        self.pending_if_else_reconnects = []
        self.statement_first_nodes = {}
        self.loop_condition_nodes = {}
        self.input_json = None
    
    def get_pending_reconnects(self) -> List[Dict[str, Any]]:
        """
        获取所有待处理的回连信息
        
        返回:
            List: 待处理的回连信息列表
        """
        return self.pending_if_else_reconnects
    
    def clear_pending_reconnects(self):
        """清空待处理的回连信息"""
        self.pending_if_else_reconnects = []

