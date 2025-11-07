"""
循环结构处理模块
负责处理for和while循环结构
"""
from typing import Dict, Any
from logger.logger import logger
from ..utils import count_statement_chain


class LoopProcessor:
    """循环结构处理器：负责处理for和while循环"""
    
    def __init__(self, node_manager, connection_manager, context_manager):
        """
        初始化循环处理器
        
        参数:
            node_manager: 节点管理器
            connection_manager: 连接管理器
            context_manager: 上下文管理器
        """
        self.node_manager = node_manager
        self.connection_manager = connection_manager
        self.context_manager = context_manager
    
    def calculate_loop_offset(self, loop_item: Dict[str, Any], 
                            base_offset: float, is_while: bool = False) -> float:
        """
        计算循环体的x偏移量
        
        参数:
            loop_item: 循环语句项
            base_offset: 基础偏移量
            is_while: 是否为while循环
            
        返回:
            float: 计算后的偏移量
        """
        # 计算循环体内最长的语句链数量
        max_statement_chain = 0
        
        if "children" in loop_item:
            for child in loop_item["children"]:
                if isinstance(child, dict):
                    # 查找循环体块
                    loop_body_type = "while_true_block" if is_while else "for_block"
                    if child.get("type") in [loop_body_type, "while_block", "for_true_block"]:
                        if "children" in child:
                            for grandchild in child["children"]:
                                if isinstance(grandchild, dict) and grandchild.get('tag') != 'block':
                                    chain_length = count_statement_chain(grandchild)
                                    if chain_length > max_statement_chain:
                                        max_statement_chain = chain_length
        
        logger.debug(f"{'while' if is_while else 'for'}循环体内最长语句链数量: {max_statement_chain}")
        
        # 检查循环体内是否有if或while语句
        has_inner_conditional = self._has_inner_conditional(loop_item)
        
        # 根据是否有内部条件语句决定x偏移量 - 翻2倍
        loop_offset = base_offset * 2 if has_inner_conditional else base_offset
        logger.debug(f"循环最终决定：是否需要二倍偏移={has_inner_conditional}, 使用x偏移量={loop_offset}")
        
        return loop_offset
    
    def _has_inner_conditional(self, loop_item: Dict[str, Any]) -> bool:
        """
        检查循环体内是否有条件语句或嵌套循环
        
        参数:
            loop_item: 循环语句项
            
        返回:
            bool: 如果有条件语句返回True，否则返回False
        """
        if "children" in loop_item:
            for child in loop_item["children"]:
                if isinstance(child, dict):
                    if "children" in child:
                        for grandchild in child["children"]:
                            if isinstance(grandchild, dict):
                                original_unit = grandchild.get("original_unit", "").lower()
                                tag = grandchild.get("tag")
                                type_ = grandchild.get("type")
                                # 检查是否包含if或while关键字或条件标签
                                if ("if" in original_unit or 
                                    "while" in original_unit or
                                    tag in ["condition", "branch", "loop"] or
                                    type_ in ["if_block", "while_block", "while_true_block"]):
                                    logger.debug(f"循环体发现条件语句: {original_unit}")
                                    return True
        return False
    
    def add_loop_body_reconnection(self, body_current: Dict[str, Any], 
                                   loop_condition_node: Dict[str, Any],
                                   body_return: bool, child: Dict[str, Any],
                                   if_block_last_node: Dict[str, Any] = None) -> None:
        """
        添加循环体的回连
        
        参数:
            body_current: 循环体最后一个节点
            loop_condition_node: 循环条件节点
            body_return: 循环体是否有return语句
            child: 循环体块
            if_block_last_node: if块的最后节点（如果循环体以if-else结尾）
        """
        # 只有当循环体中没有return语句时才添加回连
        logger.debug(f"循环体最后节点: {body_current}, has_return: {body_return}")
        if body_current and not body_return:
            # 首先添加正常的right连接
            self.connection_manager.add_connection(
                body_current["id"], "right", loop_condition_node["id"], "up"
            )
            
            # 检查是否有if块的最后节点（从process_block返回）
            if if_block_last_node and if_block_last_node != body_current:
                # 这意味着循环体以if-else结构结尾
                logger.debug(f"检测到循环体以if-else结尾，添加if块left连接到循环")
                # 从if块的最后节点的left点连回循环的up点
                self.connection_manager.add_connection(
                    if_block_last_node["id"], "left", loop_condition_node["id"], "up"
                )
            else:
                # 如果没有直接返回if块的最后节点，尝试另一种方法
                self._add_fallback_if_reconnection(child, body_current, body_return, loop_condition_node)
    
    def _add_fallback_if_reconnection(self, child: Dict[str, Any], 
                                     body_current: Dict[str, Any],
                                     body_return: bool,
                                     loop_condition_node: Dict[str, Any]) -> None:
        """
        添加备用的if-else回连（如果process_block没有返回if块最后节点）
        
        参数:
            child: 循环体块
            body_current: 循环体最后节点
            body_return: 循环体是否有return
            loop_condition_node: 循环条件节点
        """
        # 检查循环体的最后一个子节点是否是if-else结构
        if "children" in child:
            last_child = child["children"][-1] if child["children"] else None
            if isinstance(last_child, dict) and last_child.get("type") == "if_block":
                # 检查是否有else块
                has_else = False
                if_node = None
                for block_child in last_child.get("children", []):
                    if isinstance(block_child, dict):
                        if block_child.get("type") == "else_block":
                            has_else = True
                        # 这个逻辑在原代码中会导致重新处理block，
                        # 为了避免循环依赖，这里简化处理
                
                if has_else and if_node:
                    logger.debug(f"通过备用方法检测到循环体以if-else结尾，添加if块left连接到循环")
                    self.connection_manager.add_connection(
                        if_node["id"], "left", loop_condition_node["id"], "up"
                    )
    
    def check_next_statements_for_conditional(self, input_json: list, 
                                             loop_index: int,
                                             statement_count: int) -> bool:
        """
        检查循环后续n个语句中是否有条件语句
        
        参数:
            input_json: 输入JSON列表
            loop_index: 循环语句在input_json中的索引
            statement_count: 要检查的语句数量
            
        返回:
            bool: 如果有条件语句返回True，否则返回False
        """
        if statement_count <= 0:
            logger.debug("循环体内没有语句，跳过检查")
            return False
        
        logger.debug(f"开始检查后续{statement_count}个语句中是否有条件语句")
        # 检查后续的n个非block语句
        check_count = 0
        for next_idx in range(loop_index + 1, len(input_json)):
            next_item = input_json[next_idx]
            if next_item.get("tag") != "block":
                original_unit = next_item.get("original_unit", "").lower()
                tag = next_item.get("tag")
                logger.debug(f"检查后续语句: {original_unit}, tag: {tag}")
                # 检查是否包含if或while关键字或条件标签
                if ("if" in original_unit or 
                    "while" in original_unit or
                    tag in ["condition", "branch", "loop"]):
                    logger.debug(f"发现条件语句: {original_unit}")
                    return True
                check_count += 1
                if check_count >= statement_count:
                    logger.debug(f"已检查{check_count}个语句，达到限制")
                    break
        
        return False

