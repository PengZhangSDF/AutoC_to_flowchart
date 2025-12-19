"""
主转换器模块
协调各模块完成代码到流程图的转换
"""
import json
from typing import Dict, Any, List, Tuple
from logger.logger import logger

from .node_manager import NodeManager
from .connection_manager import ConnectionManager
from .context_manager import ContextManager
from .control_flow import IfElseProcessor, LoopProcessor
from .utils import is_statement_in_loop, count_statement_chain


class FlowchartConverter:
    """流程图转换器：协调各模块完成代码到流程图的转换"""
    
    def __init__(self):
        """初始化转换器及所有管理器"""
        # 初始化各个管理器
        self.node_manager = NodeManager()
        self.connection_manager = ConnectionManager(self.node_manager)
        self.context_manager = ContextManager()
        
        # 初始化控制流处理器
        self.if_else_processor = IfElseProcessor(
            self.node_manager, 
            self.connection_manager, 
            self.context_manager
        )
        self.loop_processor = LoopProcessor(
            self.node_manager,
            self.connection_manager,
            self.context_manager
        )
        
        # 坐标和偏移量设置
        self.current_x = -4600.0  # 以-4600,-4800为起点
        self.current_y = -4800.0
        self.base_x = -4600.0
        self.base_y = -4800.0
        self.level_height = 125  # 层级之间的垂直距离
        self.condition_offset_x = 200  # if块的x偏移
        self.condition_offset_y = 150  # if/else块的y偏移
        self.loop_offset_x = 120  # 循环体的x偏移
        self.loop_offset_y = 120  # 循环体的y偏移
        
        # 用于process_block跟踪当前块
        self.current_block = None
    
    def convert(self, input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        转换主函数
        
        参数:
            input_json: 输入的JSON数据
            
        返回:
            Dict: 输出的流程图JSON
        """
        # 重置所有管理器状态
        self._reset_all()
        
        # 设置输入JSON引用
        self.context_manager.set_input_json(input_json)
        
        # 创建开始节点
        self.node_manager.start_node = self.node_manager.create_node(
            "start", "开始", self.current_x, self.current_y
        )
        self.current_y += self.level_height
        
        # 处理所有项目
        current_node = self.node_manager.start_node
        current_y = self.current_y
        max_y = current_y
        
        for i, item in enumerate(input_json):
            if item.get("tag") == "block":
                continue
            
            # 处理循环结构
            if self._is_loop_structure(item):
                current_node, current_y = self._process_loop_structure(
                    item, i, current_node, current_y, input_json
                )
            else:
                # 处理普通语句（包括 if-else）
                current_node, current_y = self._process_normal_statement(
                    item, i, current_node, current_y, input_json
                )
            
            # 更新最大y坐标
            if current_y > max_y:
                max_y = current_y
        
        # 处理结束节点
        self._create_end_node(current_node, max_y)
        
        # 处理所有待处理的 if-else 回连
        self._process_pending_reconnects(input_json)
        
        # **通用处理**：处理所有孤立节点（没有出站连接的节点）
        self._connect_orphan_nodes_generic(input_json)
        
        # **最终验证**：修复明显错误的连接
        self._fix_obviously_wrong_connections()
        
        # **最后的修复**：检查并修正down到主流程外层语句的连接
        self._fix_down_to_outer_layer()
        
        # **处理break语句**：连接到循环外的第一个语句
        self._process_break_statements(input_json)
        
        # 构建输出JSON
        return self._build_output()
    
    def _reset_all(self):
        """重置所有管理器状态"""
        self.node_manager.reset()
        self.connection_manager.reset()
        self.context_manager.reset()
        self.current_block = None
    
    def _is_loop_structure(self, item: Dict[str, Any]) -> bool:
        """判断是否为循环结构"""
        return (("for" in item.get("original_unit", "") or 
                "while" in item.get("original_unit", "").lower()) and 
               item.get("tag") in ["condition", "loop"])
    
    def _process_loop_structure(self, item: Dict[str, Any], index: int,
                               current_node: Dict[str, Any], current_y: float,
                               input_json: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
        """
        处理循环结构
        
        返回: (current_node, current_y)
        """
        is_for = "for" in item.get("original_unit", "")
        is_while = "while" in item.get("original_unit", "").lower()
        
        if is_for:
            return self._process_for_loop(item, current_node, current_y)
        elif is_while:
            return self._process_while_loop(item, index, current_node, current_y, input_json)
        
        return current_node, current_y
    
    def _process_for_loop(self, item: Dict[str, Any], current_node: Dict[str, Any],
                         current_y: float) -> Tuple[Dict[str, Any], float]:
        """处理for循环"""
        # 创建循环条件节点
        loop_condition_node = self.node_manager.create_node(
            "decision", item["translated"], self.current_x, current_y
        )
        self.connection_manager.add_connection(
            current_node["id"], "down", loop_condition_node["id"], "up"
        )
        # 保存循环语句到循环条件节点的映射
        self.context_manager.register_loop_condition_node(item, loop_condition_node)
        
        # 处理循环体
        loop_body_processed = False
        if "children" in item:
            for child in item["children"]:
                if isinstance(child, dict) and child.get("type") == "for_block":
                    body_current, body_return, body_x, body_y, if_block_last_node = self.process_block(
                        child["children"],
                        self.current_x + self.loop_offset_x,
                        current_y + self.loop_offset_y,
                        loop_condition_node,
                        "right",
                        context_type='loop',
                        parent_statement=item
                    )
                    current_node = body_current
                    current_y = body_y
                    loop_body_processed = True
                    
                    # 添加循环体回连
                    self.loop_processor.add_loop_body_reconnection(
                        body_current, loop_condition_node, body_return, child, if_block_last_node
                    )
        
        # 将循环条件节点作为当前节点
        if loop_body_processed:
            current_node = loop_condition_node
        
        return current_node, current_y
    
    def _process_while_loop(self, item: Dict[str, Any], index: int,
                           current_node: Dict[str, Any], current_y: float,
                           input_json: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
        """处理while循环"""
        logger.debug(f"\n检测到while循环: {item.get('original_unit')}, tag: {item.get('tag')}")
        
        # 计算while循环内最长的语句链数量
        max_statement_chain = self._calculate_while_statement_chain(item)
        logger.debug(f"计算得到循环体内最长语句链数量: {max_statement_chain}")
        
        # 检查while循环块下面的n个语句中是否有if或while语句
        has_inner_conditional = self.loop_processor.check_next_statements_for_conditional(
            input_json, index, max_statement_chain
        )
        
        # 根据是否有内部条件语句决定x偏移量
        loop_x_offset = self.loop_offset_x * 2 if has_inner_conditional else self.loop_offset_x
        logger.debug(f"最终决定：是否需要二倍偏移={has_inner_conditional}, 使用x偏移量={loop_x_offset}")
        
        # 创建循环条件节点
        loop_condition_node = self.node_manager.create_node(
            "decision", item["translated"], self.current_x, current_y
        )
        self.connection_manager.add_connection(
            current_node["id"], "down", loop_condition_node["id"], "up"
        )
        self.context_manager.register_loop_condition_node(item, loop_condition_node)
        
        # 处理循环体
        loop_body_processed = False
        if "children" in item:
            for child in item["children"]:
                if isinstance(child, dict) and child.get("type") in ["while_true_block", "while_block"]:
                    body_current, body_return, body_x, body_y, if_block_last_node = self.process_block(
                        child["children"],
                        self.current_x + loop_x_offset,
                        current_y + self.loop_offset_y,
                        loop_condition_node,
                        "right",
                        context_type='loop',
                        parent_statement=item
                    )
                    current_node = body_current
                    current_y = body_y
                    loop_body_processed = True
                    
                    # 添加循环体回连
                    self.loop_processor.add_loop_body_reconnection(
                        body_current, loop_condition_node, body_return, child, if_block_last_node
                    )
        
        # 将循环条件节点作为当前节点
        if loop_body_processed:
            current_node = loop_condition_node
        
        return current_node, current_y
    
    def _calculate_while_statement_chain(self, item: Dict[str, Any]) -> int:
        """计算while循环内最长的语句链数量"""
        max_statement_chain = 0
        
        if "children" in item:
            logger.debug(f"while循环有子节点: {len(item['children'])}")
            for child in item["children"]:
                if isinstance(child, dict):
                    logger.debug(f"子节点类型: {child.get('type')}")
                    if child.get('type') in ["while_true_block", "while_block", "body"]:
                        logger.debug(f"找到循环体: {child.get('type')}")
                        if "children" in child:
                            logger.debug(f"循环体有子节点: {len(child['children'])}")
                            for grandchild in child["children"]:
                                if isinstance(grandchild, dict) and grandchild.get('tag') != 'block':
                                    logger.debug(f"循环体内语句: {grandchild.get('original_unit') or grandchild.get('translated')}")
                                    chain_length = count_statement_chain(grandchild)
                                    if chain_length > max_statement_chain:
                                        max_statement_chain = chain_length
        
        return max_statement_chain
    
    def _process_normal_statement(self, item: Dict[str, Any], index: int,
                                  current_node: Dict[str, Any], current_y: float,
                                  input_json: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
        """处理普通语句（包括 if-else）"""
        stmt_current, stmt_return, stmt_x, stmt_y = self.process_statement(
            item, self.current_x, current_y, current_node
        )
        
        # 记录该语句的第一个节点
        self.context_manager.register_statement_first_node(index, stmt_current)
        
        # 如果当前语句是 if-else 结构，保存回连信息
        if item.get("tag") in ["condition", "branch"]:
            self._save_if_else_reconnect_info(item, stmt_current, index, input_json)
        
        return stmt_current, stmt_y
    
    def _save_if_else_reconnect_info(self, item: Dict[str, Any], stmt_current: Dict[str, Any],
                                    index: int, input_json: List[Dict[str, Any]]):
        """保存if-else回连信息"""
        if_block_info = item.get("_if_block_info")
        else_block_info = item.get("_else_block_info")
        
        if if_block_info or else_block_info:
            # 确定上下文类型
            context_type = item.get("_context_type") or 'main'
            
            # 获取循环条件节点（如果在循环内）
            loop_condition_node = self._find_loop_condition_node(item, index, input_json, context_type)
            
            # 保存回连信息
            self.context_manager.add_pending_reconnect({
                'if_last_node': if_block_info["last_node"] if if_block_info else None,
                'else_last_node': else_block_info["last_node"] if else_block_info else None,
                'if_has_return': if_block_info["has_return"] if if_block_info else False,
                'else_has_return': else_block_info["has_return"] if else_block_info else False,
                'condition_node': stmt_current,
                'parent_block': input_json,
                'if_statement_index': index,
                'context_type': context_type,
                'loop_condition_node': loop_condition_node,
                'parent_statement': None
            })
    
    def _find_loop_condition_node(self, item: Dict[str, Any], index: int,
                                 input_json: List[Dict[str, Any]], 
                                 context_type: str) -> Dict[str, Any]:
        """查找循环条件节点"""
        loop_condition_node = None
        if context_type == 'loop':
            # 向前查找循环语句
            for prev_idx in range(index - 1, -1, -1):
                prev_item = input_json[prev_idx] if prev_idx < len(input_json) else None
                if prev_item and isinstance(prev_item, dict):
                    prev_tag = prev_item.get("tag", "")
                    prev_orig = prev_item.get("original_unit", "").lower()
                    if ("for" in prev_orig or "while" in prev_orig or prev_tag in ["loop", "condition"]):
                        loop_condition_node = self.context_manager.get_loop_condition_node(prev_item)
                        if not loop_condition_node:
                            loop_condition_node = self.context_manager.get_statement_first_node(prev_idx)
                        break
        return loop_condition_node
    
    def _create_end_node(self, current_node: Dict[str, Any], max_y: float):
        """创建结束节点"""
        if self.node_manager.end_node is None:
            # 将结束节点放在所有节点的下方
            self.node_manager.end_node = self.node_manager.create_node(
                "end", "结束", self.current_x, max_y + self.level_height + 100
            )
            
            # 连接最后一个节点到结束节点
            if current_node != self.node_manager.end_node:
                if not self.connection_manager.connection_exists(
                    current_node["id"], self.node_manager.end_node["id"]
                ):
                    self.connection_manager.add_connection(
                        current_node["id"], "down", self.node_manager.end_node["id"], "up"
                    )
        
        # 移除重复的结束节点
        removed_node_ids = self.node_manager.remove_duplicate_end_nodes()
        if removed_node_ids:
            self.connection_manager.remove_connections_with_nodes(removed_node_ids)
    
    def _process_pending_reconnects(self, input_json: List[Dict[str, Any]]):
        """处理所有待处理的 if-else 回连"""
        for reconnect_info in self.context_manager.get_pending_reconnects():
            # 查找后续语句的第一个节点
            next_statement_first_node = self._find_next_statement_node(reconnect_info, input_json)
            
            # 获取循环条件节点
            loop_condition_node = self._get_loop_condition_node_for_reconnect(
                reconnect_info, input_json
            )
            
            # 调用回连处理
            context_type = reconnect_info.get('context_type')
            self.if_else_processor.handle_if_else_reconnect(
                reconnect_info['if_last_node'],
                reconnect_info['else_last_node'],
                reconnect_info['if_has_return'],
                reconnect_info['else_has_return'],
                reconnect_info['condition_node'],
                reconnect_info['parent_block'],
                reconnect_info['if_statement_index'],
                next_statement_first_node,
                loop_condition_node,
                self.context_manager.statement_context_stack,
                current_context_type=context_type
            )
            
            # 处理嵌套的if-else回连
            # **关键修复**：应该从parent_block获取语句，而不是从input_json
            parent_block = reconnect_info['parent_block']
            if_statement_idx = reconnect_info['if_statement_index']
            
            if if_statement_idx < len(parent_block):
                original_statement = parent_block[if_statement_idx]
                if original_statement and original_statement.get("tag") in ["condition", "branch"]:
                    self.if_else_processor.handle_nested_if_else_reconnect(
                        original_statement,
                        parent_block,
                        if_statement_idx,
                        next_statement_first_node,
                        loop_condition_node,
                        self.context_manager.statement_context_stack,
                        reconnect_info['condition_node']
                    )
    
    def _find_next_statement_node(self, reconnect_info: Dict[str, Any],
                                 input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """查找if-else后续语句的第一个节点"""
        next_statement_first_node = None
        if_statement_idx = reconnect_info['if_statement_index']
        parent_block = reconnect_info['parent_block']
        
        # **关键修复**：从parent_block获取语句，而不是从input_json
        else_last_node = None
        if if_statement_idx < len(parent_block):
            original_statement = parent_block[if_statement_idx]
            if original_statement:
                else_block_info = original_statement.get("_else_block_info")
                if else_block_info:
                    else_last_node = else_block_info.get("last_node")
        
        # 跳过整个if-else结构
        skip_count = self._calculate_skip_count(parent_block, if_statement_idx)
        
        # 查找真正的后续语句
        for next_idx in range(if_statement_idx + skip_count, len(parent_block)):
            next_item = parent_block[next_idx] if next_idx < len(parent_block) else None
            if next_item and isinstance(next_item, dict) and next_item.get("tag") != "block":
                if parent_block == input_json:
                    candidate_node = self.context_manager.get_statement_first_node(next_idx)
                    if candidate_node:
                        # 验证不是else块的最后节点
                        if else_last_node and candidate_node.get("id") == else_last_node.get("id"):
                            logger.debug(f"跳过else块的最后一个节点作为后续语句: {candidate_node.get('id')}")
                            continue
                        
                        # 验证不是if-else结构的一部分
                        # **关键修复**：original_statement现在从parent_block获取，更准确
                        current_original_stmt = None
                        if if_statement_idx < len(parent_block):
                            current_original_stmt = parent_block[if_statement_idx]
                        
                        if not current_original_stmt or not self._is_part_of_if_else(next_item, current_original_stmt):
                            next_statement_first_node = candidate_node
                            logger.debug(f"找到后续语句节点: {next_statement_first_node.get('id')}")
                            break
                break
        
        return next_statement_first_node
    
    def _calculate_skip_count(self, parent_block: List[Dict[str, Any]], 
                             if_statement_idx: int) -> int:
        """计算需要跳过的语句数量（整个if-else结构）"""
        skip_count = 0
        if if_statement_idx < len(parent_block):
            current_idx = if_statement_idx
            if current_idx < len(parent_block):
                current_item = parent_block[current_idx]
                if current_item.get("tag") in ["condition", "branch"]:
                    skip_count = 1
                    current_idx += 1
                    while current_idx < len(parent_block):
                        next_item = parent_block[current_idx]
                        if isinstance(next_item, dict):
                            if next_item.get("tag") == "branch" and "否则" in next_item.get("translated", ""):
                                skip_count += 1
                                current_idx += 1
                            else:
                                break
                        else:
                            break
        return skip_count
    
    def _is_part_of_if_else(self, next_item: Dict[str, Any], 
                           original_statement: Dict[str, Any]) -> bool:
        """判断语句是否是if-else结构的一部分"""
        if not original_statement or "children" not in original_statement:
            return False
        
        # 检查next_item是否是当前if-else结构的子元素
        for child in original_statement["children"]:
            if child == next_item:
                logger.debug(f"跳过：next_item是当前if-else结构的子元素（else块语句）")
                return True
            
            # 检查next_item是否在else_block的children中
            if isinstance(child, dict):
                if child.get("tag") == "branch" and "否则" in child.get("translated", ""):
                    if "children" in child:
                        for block_child in child["children"]:
                            if isinstance(block_child, dict) and block_child.get("type") == "else_block":
                                if "children" in block_child:
                                    for gc in block_child["children"]:
                                        if gc == next_item:
                                            logger.debug(f"跳过：next_item是else_block的children")
                                            return True
        
        return False
    
    def _get_loop_condition_node_for_reconnect(self, reconnect_info: Dict[str, Any],
                                              input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取回连所需的循环条件节点"""
        loop_condition_node = reconnect_info.get('loop_condition_node')
        
        if not loop_condition_node:
            if_statement_idx = reconnect_info['if_statement_index']
            parent_block = reconnect_info['parent_block']
            parent_statement = reconnect_info.get('parent_statement')
            
            # 从parent_statement查找
            if parent_statement:
                loop_condition_node = self.context_manager.get_loop_condition_node(parent_statement)
            
            # 从parent_block查找
            if not loop_condition_node and parent_block != input_json:
                loop_condition_node = self._find_loop_in_parent_block(parent_block, input_json)
            
            # 在parent_block中向前查找
            if not loop_condition_node:
                loop_condition_node = self._find_loop_before_statement(
                    parent_block, if_statement_idx, input_json
                )
        
        return loop_condition_node
    
    def _find_loop_in_parent_block(self, parent_block: List[Dict[str, Any]],
                                  input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在父块中查找循环条件节点"""
        for loop_idx, loop_item in enumerate(input_json):
            if isinstance(loop_item, dict):
                loop_tag = loop_item.get("tag", "")
                loop_orig = loop_item.get("original_unit", "").lower()
                if ("for" in loop_orig or "while" in loop_orig or loop_tag in ["loop", "condition"]):
                    if "children" in loop_item:
                        for child in loop_item.get("children", []):
                            if isinstance(child, dict):
                                if child.get("type") in ["for_block", "while_block", "while_true_block"]:
                                    if "children" in child:
                                        if parent_block == child["children"]:
                                            loop_condition_node = self.context_manager.get_loop_condition_node(loop_item)
                                            if not loop_condition_node:
                                                loop_condition_node = self.context_manager.get_statement_first_node(loop_idx)
                                            return loop_condition_node
        return None
    
    def _find_loop_before_statement(self, parent_block: List[Dict[str, Any]],
                                   if_statement_idx: int,
                                   input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在语句之前查找循环"""
        for prev_idx in range(if_statement_idx - 1, -1, -1):
            prev_item = parent_block[prev_idx] if prev_idx < len(parent_block) else None
            if prev_item and isinstance(prev_item, dict):
                prev_tag = prev_item.get("tag", "")
                prev_orig = prev_item.get("original_unit", "").lower()
                if ("for" in prev_orig or "while" in prev_orig or prev_tag in ["loop"]):
                    loop_condition_node = self.context_manager.get_loop_condition_node(prev_item)
                    if not loop_condition_node:
                        if parent_block == input_json:
                            loop_condition_node = self.context_manager.get_statement_first_node(prev_idx)
                    return loop_condition_node
        return None
    
    def _process_break_statements(self, input_json: List[Dict[str, Any]]):
        """
        处理所有break语句的连接
        
        break语句需要连接到循环外的第一个语句
        """
        # 收集所有break语句
        break_statements = []
        self._collect_break_statements(input_json, break_statements)
        
        if not break_statements:
            logger.debug("[break处理] 没有发现break语句")
            return
        
        logger.debug(f"[break处理] 发现{len(break_statements)}个break语句")
        
        # 处理每个break语句
        for stmt_info in break_statements:
            statement = stmt_info['statement']
            parent_loop = stmt_info['parent_loop']
            
            break_node = statement.get('_break_node')
            if not break_node:
                continue
            
            # 查找循环外的第一个语句
            next_after_loop = self._find_statement_after_loop_with_backtrack(
                parent_loop, input_json
            )
            
            if next_after_loop:
                # 添加break -> 循环外语句的left连接
                self.connection_manager.add_connection(
                    break_node['id'], 'left', next_after_loop['id'], 'up'
                )
                break_suffix = break_node['id'].split('_')[-1]
                next_suffix = next_after_loop['id'].split('_')[-1]
                logger.debug(f"[break连接] _{break_suffix} (left) -> _{next_suffix}")
            else:
                logger.debug(f"[break] 未找到循环外的语句，连接到结束节点")
                # 如果没有循环外的语句，连接到结束节点
                if self.node_manager.end_node:
                    self.connection_manager.add_connection(
                        break_node['id'], 'left', self.node_manager.end_node['id'], 'up'
                    )
    
    def _collect_break_statements(self, statements: List[Dict[str, Any]], 
                                  result: List[Dict[str, Any]], 
                                  current_loop: Dict[str, Any] = None):
        """
        递归收集所有break语句及其所在的循环
        """
        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            
            # 如果是break语句
            if stmt.get('_is_break'):
                parent_loop = stmt.get('_parent_loop_statement') or current_loop
                result.append({
                    'statement': stmt,
                    'parent_loop': parent_loop
                })
            
            # 如果是循环，更新current_loop
            tag = stmt.get('tag', '')
            orig = stmt.get('original_unit', '')
            if tag in ['loop', 'condition'] or 'for' in orig or 'while' in orig:
                # 这是一个新的循环
                new_loop = stmt
                
                # 递归处理循环体内的语句
                if 'children' in stmt:
                    for child in stmt['children']:
                        if isinstance(child, dict) and child.get('type') in [
                            'for_block', 'for_true_block', 'while_block', 'while_true_block'
                        ]:
                            self._collect_break_statements(
                                child.get('children', []), result, new_loop
                            )
            
            # 递归处理其他children
            if 'children' in stmt:
                for child in stmt['children']:
                    if isinstance(child, dict):
                        if child.get('type') in ['if_block', 'else_block']:
                            # if/else块内继承当前的循环上下文
                            self._collect_break_statements(
                                child.get('children', []), result, current_loop
                            )
    
    def _find_statement_after_loop_with_backtrack(self, loop_statement: Dict[str, Any],
                                                  input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        查找循环后的第一个语句（支持回溯）
        
        如果循环后没有同级语句，会向上回溯到父结构查找
        """
        if not loop_statement:
            return None
        
        # 首先尝试直接查找
        result = self._find_statement_after_loop(loop_statement, input_json)
        if result:
            return result
        
        # 如果没找到，尝试回溯：查找包含这个循环的if/else块，然后找if/else后的语句
        parent_if_else = self._find_parent_if_else_of_loop(loop_statement, input_json)
        if parent_if_else:
            # 找到父if-else后的语句
            result = self._find_statement_after_loop(parent_if_else, input_json)
            if result:
                return result
        
        return None
    
    def _find_parent_if_else_of_loop(self, loop_statement: Dict[str, Any],
                                     statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        查找包含给定循环的父if-else结构
        """
        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            
            # 检查这个语句的children中是否包含循环
            if 'children' in stmt:
                for child in stmt['children']:
                    if not isinstance(child, dict):
                        continue
                    
                    # 如果child是if_block或else_block
                    if child.get('type') in ['if_block', 'else_block']:
                        child_children = child.get('children', [])
                        
                        # 检查循环是否直接在这个块中
                        if loop_statement in child_children:
                            # 找到了！返回父if-else语句
                            return stmt
                        
                        # 递归查找
                        result = self._find_parent_if_else_of_loop(loop_statement, child_children)
                        if result:
                            return result
        
        return None
    
    def _find_statement_after_loop(self, loop_statement: Dict[str, Any],
                                   input_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        查找循环语句之后的第一个语句的首节点
        
        参数:
            loop_statement: 循环语句
            input_json: 主语句列表
        
        返回:
            循环后第一个语句的节点，如果没有则返回None
        """
        if not loop_statement:
            return None
        
        # 首先在顶层查找
        result = self._find_next_in_block(loop_statement, input_json, is_top_level=True)
        if result:
            return result
        
        # 如果在顶层没找到，递归查找嵌套的循环
        return self._find_next_in_nested_blocks(loop_statement, input_json)
    
    def _find_next_in_block(self, target_statement: Dict[str, Any],
                           block: List[Dict[str, Any]],
                           is_top_level: bool = False) -> Dict[str, Any]:
        """在给定的block中查找target_statement之后的语句"""
        for idx, stmt in enumerate(block):
            if stmt == target_statement:
                # 找到了，查找后续语句
                for next_idx in range(idx + 1, len(block)):
                    next_stmt = block[next_idx]
                    if isinstance(next_stmt, dict) and next_stmt.get('tag') != 'block':
                        # 找到后续语句
                        if is_top_level:
                            # 顶层可以使用statement_first_nodes
                            return self.context_manager.get_statement_first_node(next_idx)
                        else:
                            # 嵌套层需要通过文本查找节点
                            return self._find_node_by_text(next_stmt.get('translated', ''))
                # 没有后续语句
                return None
        return None
    
    def _find_next_in_nested_blocks(self, target_statement: Dict[str, Any],
                                    statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在嵌套结构中递归查找target_statement之后的语句"""
        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            
            # 检查children中的各种块
            if 'children' in stmt:
                for child in stmt['children']:
                    if not isinstance(child, dict):
                        continue
                    
                    child_type = child.get('type', '')
                    if child_type in ['if_block', 'else_block', 'for_block', 'for_true_block',
                                     'while_block', 'while_true_block']:
                        child_children = child.get('children', [])
                        
                        # 在这个块中查找
                        result = self._find_next_in_block(target_statement, child_children)
                        if result:
                            return result
                        
                        # 递归查找
                        result = self._find_next_in_nested_blocks(target_statement, child_children)
                        if result:
                            return result
        
        return None
    
    def _find_node_by_text(self, text: str) -> Dict[str, Any]:
        """根据文本查找节点"""
        if not text:
            return None
        
        for node in self.node_manager.get_all_nodes():
            if node.get('text') == text:
                return node
        
        return None
    
    def _fix_down_to_outer_layer(self):
        """
        修复down到外层语句的错误连接
        
        特征：
        1. 节点从decision.right进入（if块）
        2. 有down连接到主流程上的process/input节点（y>100, x在主流程）
        3. 有可用的right到循环的候选（decision，y向上）
        
        这种情况下应该right到循环，而不是down到外层语句
        """
        nodes_to_fix = []
        base_x = -4600.0
        
        for node in self.node_manager.get_all_nodes():
            # 跳过特殊节点
            if node.get('text') in ['开始', '结束']:
                continue
            
            # **新增**：跳过break和continue节点
            node_text_lower = node.get('text', '').lower()
            if node_text_lower == 'break;' or node_text_lower == 'continue;':
                continue
            
            node_id = node.get('id')
            node_y = node.get('y', 0)
            
            # 检查是否从decision.right进入
            incoming = self.connection_manager.get_connections_to_node(node_id)
            from_decision_right = any(
                c['start_point_type'] == 'right' and
                self.node_manager.get_node_by_id(c['start_item_id']).get('type') == 'decision'
                for c in incoming
            )
            
            if not from_decision_right:
                continue
            
            # 检查出站连接
            outgoing = self.connection_manager.get_connections_from_node(node_id)
            if len(outgoing) != 1:
                continue
            
            conn = outgoing[0]
            if conn['start_point_type'] != 'down':
                continue  # 只检查down连接
            
            # 检查目标节点
            target_id = conn['end_item_id']
            target = self.node_manager.get_node_by_id(target_id)
            if not target or target.get('type') not in ['process', 'input']:
                continue
            
            target_y = target.get('y', 0)
            target_x = target.get('x', 0)
            y_diff = target_y - node_y
            
            # **关键判断**：是否应该检查right候选
            target_in_main = abs(target_x - base_x) < 100
            x_dist = abs(target_x - node.get('x', 0))
            
            # 检查目标节点是否从decision进入（可能是另一个分支的内部语句）
            # **改进**：追溯2层，检查直接或间接的decision连接
            target_incoming = self.connection_manager.get_connections_to_node(target_id)
            target_from_decision = False
            
            # 第1层：直接检查
            for c in target_incoming:
                parent = self.node_manager.get_node_by_id(c['start_item_id'])
                if parent and parent.get('type') == 'decision':
                    target_from_decision = True
                    break
                # 第2层：如果parent是process，检查parent的入站
                elif parent and parent.get('type') in ['process', 'input']:
                    parent_incoming = self.connection_manager.get_connections_to_node(parent.get('id'))
                    for pc in parent_incoming:
                        grandparent = self.node_manager.get_node_by_id(pc['start_item_id'])
                        if grandparent and grandparent.get('type') == 'decision':
                            target_from_decision = True
                            break
                if target_from_decision:
                    break
            
            # **额外检查**：如果目标是汇聚点（在target中会有多个入站），可能是正确的后续语句
            # 但在处理时可能还没有所有连接，所以不能完全依赖这个
            target_is_convergence = len(target_incoming) >= 2
            
            # **更严格的判断**：只在以下情况修复：
            # 条件1：目标在主流程且y>100（明确的外层语句）
            # 条件2已移除，因为太容易误判
            should_check_right = (y_diff > 100 and target_in_main)
            
            if should_check_right:
                # 查找更好的right候选（循环节点）
                # **改进**：选择距离最近的循环节点，而不是第一个
                better_right = None
                min_distance = float('inf')
                
                for candidate in self.node_manager.get_all_nodes():
                    if candidate.get('id') == node_id or candidate.get('type') != 'decision':
                        continue
                    
                    cand_y = candidate.get('y', 0)
                    cand_y_diff = cand_y - node_y
                    
                    # 向上的decision节点（可能是循环）
                    if cand_y_diff < 0 and 200 < abs(cand_y_diff) < 800:
                        cand_text = candidate.get('text', '')
                        is_loop = any(kw in cand_text for kw in ['判断：', '循环', 'for', 'while', '<', '<='])
                        
                        if is_loop:
                            distance = abs(cand_y_diff)
                            if distance < min_distance:
                                min_distance = distance
                                better_right = candidate
                
                if better_right:
                    nodes_to_fix.append((node, conn, better_right))
        
        # 执行修复
        for node, wrong_conn, correct_target in nodes_to_fix:
            node_suffix = node.get('id').split('_')[-1]
            correct_suffix = correct_target.get('id').split('_')[-1]
            
            logger.debug(f"[修复外层连接] _{node_suffix}: 删除down连接，添加right到循环_{correct_suffix}")
            
            # 删除错误的连接
            self.connection_manager.connections.remove(wrong_conn)
            
            # 添加正确的连接
            self.connection_manager.add_connection(
                node.get('id'), 'right', correct_target.get('id'), 'up'
            )
    
    def _fix_obviously_wrong_connections(self):
        """
        修复明显错误的连接
        
        检查：
        1. 从if块(decision.right进入的process)出发的right连接
        2. 如果附近有更合适的down目标（process/input，距离<300），应该改为down连接
        """
        nodes_to_fix = []
        
        for node in self.node_manager.get_all_nodes():
            # 跳过特殊节点
            if node.get('text') in ['开始', '结束']:
                continue
            
            # **新增**：跳过break和continue节点
            node_text = node.get('text', '').lower()
            if node_text == 'break;' or node_text == 'continue;':
                continue
            
            node_id = node.get('id')
            
            # 检查是否从decision.right进入
            incoming = self.connection_manager.get_connections_to_node(node_id)
            from_decision_right = any(
                c['start_point_type'] == 'right' and
                self.node_manager.get_node_by_id(c['start_item_id']).get('type') == 'decision'
                for c in incoming
            )
            
            if not from_decision_right:
                continue
            
            # 检查出站连接
            outgoing = self.connection_manager.get_connections_from_node(node_id)
            if len(outgoing) != 1:
                continue
            
            conn = outgoing[0]
            if conn['start_point_type'] != 'right':
                continue  # 只检查right连接
            
            # **关键判断**：只修复连到错误循环的连接
            # 检查当前target是否是错误的循环节点
            target_id = conn['end_item_id']
            target_node = self.node_manager.get_node_by_id(target_id)
            
            if not target_node:
                continue
            
            # **判断target是否是错误的循环节点**：
            # 只修复明显错误的情况：target距离特别远（>600）或者不是真正的循环节点
            node_y = node.get('y', 0)
            target_y = target_node.get('y', 0)
            y_diff_to_target = target_y - node_y
            abs_y_to_target = abs(y_diff_to_target)
            
            # 如果target在下方（y > node_y），不是错误的循环回连，跳过
            if y_diff_to_target >= 0:
                continue
            
            # **新增检查**：如果target是合理距离的循环节点（<600且有循环关键词），不修复
            target_text = target_node.get('text', '')
            target_is_loop = any(kw in target_text for kw in ['判断：', '循环', 'for', 'while', '<', '<='])
            
            if abs_y_to_target < 600 and target_is_loop:
                # 这是合理的循环回连，不修复
                continue
            
            # 查找附近的process/input节点作为更好的目标
            better_target = None
            best_score = float('inf')
            
            for candidate in self.node_manager.get_all_nodes():
                if candidate.get('id') == node_id or candidate.get('text') in ['开始', '结束']:
                    continue
                
                cand_type = candidate.get('type', '')
                if cand_type not in ['process', 'input']:
                    continue  # 只考虑process/input
                
                cand_y = candidate.get('y', 0)
                y_diff = cand_y - node_y
                
                # 只考虑向下、距离很合理的节点（y<250）
                if 0 < y_diff <= 250:
                    x_diff = abs(candidate.get('x', 0) - node.get('x', 0))
                    # 如果x距离太大（>700），可能不是真正的后续语句
                    if x_diff > 700:
                        continue
                    
                    score = y_diff + x_diff * 0.5
                    
                    if score < best_score:
                        best_score = score
                        better_target = candidate
            
            # **改进条件**：只有找到合理的down目标才修复
            # 分数阈值根据y距离调整：y越近，允许的x距离越大
            if better_target:
                better_y = better_target.get('y', 0) - node_y
                # 如果y距离很近（<150），即使x距离大也接受（阈值600）
                # 如果y距离适中（150-300），x距离不能太大（阈值500）
                max_allowed_score = 600 if better_y < 150 else 500
                
                if best_score <= max_allowed_score:
                    nodes_to_fix.append((node, conn, better_target))
        
        # 执行修复
        for node, wrong_conn, correct_target in nodes_to_fix:
            node_suffix = node.get('id').split('_')[-1]
            correct_suffix = correct_target.get('id').split('_')[-1]
            
            logger.debug(f"[修复错误连接] _{node_suffix}: 删除right连接，添加down到_{correct_suffix}")
            
            # 删除错误的连接
            self.connection_manager.connections.remove(wrong_conn)
            
            # 添加正确的连接
            self.connection_manager.add_connection(
                node.get('id'), 'down', correct_target.get('id'), 'up'
            )
    
    def _connect_orphan_nodes_generic(self, input_json: List[Dict[str, Any]]):
        """
        通用的孤立节点连接方法：基于结构特征而非硬编码规则
        
        算法：
        1. 找到所有孤立节点（没有出站连接）
        2. 分析每个节点的结构特征（入站连接、位置）
        3. 基于特征选择最合适的目标和连接类型
        """
        orphans = []
        for node in self.node_manager.get_all_nodes():
            # 跳过特殊节点
            if node.get('text') in ['开始', '结束']:
                continue
            
            # **新增**：跳过break和continue节点（它们已经被专门处理）
            node_text = node.get('text', '').lower()
            if node_text == 'break;' or node_text == 'continue;':
                continue
            
            outgoing = self.connection_manager.get_connections_from_node(node['id'])
            if not outgoing:
                orphans.append(node)
        
        if not orphans:
            return
        
        logger.debug(f"[通用处理] 发现{len(orphans)}个孤立节点")
        
        for orphan in orphans:
            orphan_suffix = orphan['id'].split('_')[-1]
            target, conn_type = self._find_target_generic(orphan)
            if target and conn_type:
                # 验证不是连接到自己
                if target.get('id') != orphan.get('id'):
                    self.connection_manager.add_connection(
                        orphan['id'], conn_type, target['id'], 'up'
                    )
                    target_suffix = target['id'].split('_')[-1]
                    logger.debug(f"[通用处理] 连接 _{orphan_suffix} ({conn_type}) -> _{target_suffix}")
            else:
                logger.warning(f"[通用处理] _{orphan_suffix} 未找到目标")
    
    def _find_target_generic(self, orphan: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        通用方法：为孤立节点找到目标
        
        基于结构特征：
        1. 检查入站连接类型（从decision.right或down进入）
        2. 查找候选目标节点
        3. 基于距离、类型、位置选择最佳目标
        """
        orphan_id = orphan.get('id', '')
        orphan_x = orphan.get('x', 0)
        orphan_y = orphan.get('y', 0)
        base_x = -4600.0
        
        # **调试**：记录孤立节点ID
        orphan_suffix = orphan_id.split('_')[-1] if '_' in orphan_id else '?'
        
        # 1. 分析入站连接
        incoming = self.connection_manager.get_connections_to_node(orphan_id)
        from_decision_right = False
        
        for conn in incoming:
            start_node = self.node_manager.get_node_by_id(conn['start_item_id'])
            if start_node and start_node.get('type') == 'decision':
                if conn['start_point_type'] == 'right':
                    from_decision_right = True
                    break
        
        # 2. 识别中转节点（汇聚点）
        # 中转节点：有多个入站连接且有出站连接
        intermediate_nodes = set()
        convergence_nodes_with_right = set()  # 有right出站的汇聚点
        
        for node in self.node_manager.get_all_nodes():
            node_incoming = self.connection_manager.get_connections_to_node(node.get('id'))
            if len(node_incoming) >= 2:
                node_outgoing = self.connection_manager.get_connections_from_node(node.get('id'))
                
                has_down_out = any(c['start_point_type'] == 'down' for c in node_outgoing)
                has_right_out = any(c['start_point_type'] == 'right' for c in node_outgoing)
                
                if has_down_out:
                    intermediate_nodes.add(node.get('id'))
                if has_right_out:
                    convergence_nodes_with_right.add(node.get('id'))
        
        # 3. 收集候选节点
        down_candidates = []  # (node, score, y_diff)
        right_candidates = []  # (node, score, y_diff)
        
        for node in self.node_manager.get_all_nodes():
            node_id = node.get('id', '')
            
            # **严格过滤**：跳过自己、开始、结束节点
            if not node_id or node_id == orphan_id or node.get('text') in ['开始', '结束']:
                # 调试：如果是自己，记录一下
                if node_id == orphan_id:
                    logger.debug(f"  [过滤] 跳过自己: {node_id}")
                continue
            
            node_y = node.get('y', 0)
            node_x = node.get('x', 0)
            node_type = node.get('type', '')
            
            y_diff = node_y - orphan_y
            x_diff = abs(node_x - orphan_x)
            
            # 向下候选：y>0且距离合理
            if 0 < y_diff <= 500:
                # **跳过明显的中转节点**：
                # 只跳过那些有向下出站且距离很近的节点（它们只是传递点）
                if node_id in intermediate_nodes and y_diff < 200:
                    continue
                
                # **跳过平行分支节点**：y距离很近（<150）的节点可能是平行分支
                # 扩展识别：不仅检查直接从decision进入，还检查它的"祖先"
                if y_diff < 150:
                    node_incoming = self.connection_manager.get_connections_to_node(node_id)
                    
                    # 方法1：直接从decision进入
                    is_parallel_branch = any(
                        c['start_point_type'] in ['right', 'down'] and
                        self.node_manager.get_node_by_id(c['start_item_id']).get('type') == 'decision'
                        for c in node_incoming
                    )
                    
                    # 方法2：从process进入，但这个process也从decision进入（间接平行分支）
                    if not is_parallel_branch:
                        for conn in node_incoming:
                            parent = self.node_manager.get_node_by_id(conn['start_item_id'])
                            if parent and parent.get('type') == 'process':
                                parent_incoming = self.connection_manager.get_connections_to_node(parent.get('id'))
                                parent_from_decision = any(
                                    c['start_point_type'] in ['right', 'down'] and
                                    self.node_manager.get_node_by_id(c['start_item_id']).get('type') == 'decision'
                                    for c in parent_incoming
                                )
                                if parent_from_decision:
                                    is_parallel_branch = True
                                    break
                    
                    if is_parallel_branch:
                        continue  # 跳过平行分支
                
                # **改进评分**：主要基于y距离，x距离作为辅助
                score = y_diff
                
                # **判断孤立节点是否在主流程**
                orphan_in_main = abs(orphan_x - base_x) < 100
                is_main = abs(node_x - base_x) < 50
                
                # **主流程节点优先**，但只对孤立节点也在主流程时才高度优先
                if is_main and orphan_in_main:
                    score *= 0.4  # 都在主流程，优先
                # 孤立节点不在主流程，候选在主流程，中等优先
                elif is_main:
                    score *= 0.7  # 适度优先
                # x距离很近的节点优先
                elif x_diff < 250:
                    score *= 0.5
                # x距离适中的节点
                elif x_diff < 500:
                    score *= 0.8
                # x距离远（可能是跨块连接）
                else:
                    score *= 1.0
                
                # **最后安全检查**：确保不添加自己
                if node_id != orphan_id:
                    down_candidates.append((node, score, y_diff))
                else:
                    logger.warning(f"  [BUG] 差点添加自己为down候选: {node_id}")
            
            # 向上候选：循环节点（decision类型，y<0）
            elif y_diff < 0 and node_type == 'decision':
                if 200 < abs(y_diff) < 1000:
                    # 检查是否像循环节点
                    text = node.get('text', '')
                    is_loop = any(keyword in text for keyword in ['判断：', '循环', 'for', 'while', '<', '<='])
                    
                    if is_loop:
                        score = abs(y_diff) * 0.5
                        right_candidates.append((node, score, y_diff))
        
        # 4. 选择最佳目标
        down_candidates.sort(key=lambda x: x[1])
        right_candidates.sort(key=lambda x: x[1])
        
        # **安全检查**：移除连接到自己的候选
        down_candidates = [(n, s, y) for n, s, y in down_candidates if n.get('id') != orphan_id]
        right_candidates = [(n, s, y) for n, s, y in right_candidates if n.get('id') != orphan_id]
        
        orphan_suffix = orphan['id'].split('_')[-1] if '_' in orphan['id'] else '?'
        logger.debug(f"[查找目标] _{orphan_suffix}: down候选={len(down_candidates)}, right候选={len(right_candidates)}, from_decision_right={from_decision_right}")
        if down_candidates:
            for i, (n, score, y_diff) in enumerate(down_candidates[:3]):
                n_suffix = n['id'].split('_')[-1]
                logger.debug(f"  down[{i}]: _{n_suffix}, y_diff={y_diff}, score={score:.1f}")
        if right_candidates:
            for i, (n, score, y_diff) in enumerate(right_candidates[:3]):
                n_suffix = n['id'].split('_')[-1]
                logger.debug(f"  right[{i}]: _{n_suffix}, y_diff={y_diff}, score={score:.1f}")
        
        # **改进的决策逻辑**：基于实际距离特征
        if from_decision_right:
            # 从if块出来，需要判断是回连到循环还是连接到后续语句
            if down_candidates and right_candidates:
                best_down = down_candidates[0]
                best_down_y = best_down[2]
                best_down_node = best_down[0]
                
                # **关键判断**：检查best_down是否是汇聚点（有right出站）
                # 如果是汇聚点，需要检查是否有其他非汇聚点的down候选
                best_down_is_convergence = best_down_node.get('id') in convergence_nodes_with_right
                
                # **更精确的规则**：
                # 如果best_down是汇聚点，检查是否有其他非汇聚点候选
                if best_down_is_convergence and best_down_y > 100:
                    # 查找其他非汇聚点的down候选
                    other_down = [c for c in down_candidates[1:] if c[0].get('id') not in convergence_nodes_with_right]
                    if other_down and other_down[0][2] < 300:
                        # 有其他合理的down候选，不应该连到汇聚点，应该right
                        return right_candidates[0][0], 'right'
                    # 没有其他合理候选，就down到汇聚点（它是唯一选择）
                    else:
                        return best_down[0], 'down'
                
                # 如果有距离很近的down候选（y<150），肯定是后续语句
                if best_down_y < 150:
                    return best_down[0], 'down'
                # 如果最近的down候选距离适中（150-300），需要进一步判断
                elif best_down_y < 300:
                    # **改进判断**：不仅看x距离，还要看down候选的类型
                    best_down_x_diff = abs(best_down[0].get('x', 0) - orphan_x)
                    best_down_type = best_down[0].get('type', '')
                    orphan_in_main = abs(orphan_x - base_x) < 100
                    down_in_main = abs(best_down[0].get('x', 0) - base_x) < 100
                    
                    # **关键改进**：如果down候选是process/input（不是decision），即使x距离远，也可能是正确的后续语句
                    # 因为if块可能在侧边，而后续语句回到主流程
                    if best_down_type in ['process', 'input']:
                        # 如果目标在主流程，优先选择down（即使x距离大）
                        if down_in_main and best_down_y < 250:
                            return best_down[0], 'down'
                        # 如果x距离不是特别大，选down
                        elif best_down_x_diff < 700:
                            return best_down[0], 'down'
                        # x距离太大，可能不对，选right
                        else:
                            return right_candidates[0][0], 'right'
                    # down候选是decision，可能是下一个if-else，判断更严格
                    else:
                        if best_down_x_diff < 300:
                            return best_down[0], 'down'
                        else:
                            return right_candidates[0][0], 'right'
                # 如果最近的down候选很远（>=300），应该right回连到循环
                else:
                    return right_candidates[0][0], 'right'
            elif right_candidates:
                return right_candidates[0][0], 'right'
            elif down_candidates:
                return down_candidates[0][0], 'down'
        else:
            # 从else块或其他结构出来，优先使用down到后续语句
            if down_candidates:
                return down_candidates[0][0], 'down'
            if right_candidates:
                return right_candidates[0][0], 'right'
        
        return None, None
    
    def _fix_orphan_nodes_OLD(self, input_json: List[Dict[str, Any]]):
        """
        通用修复：处理所有孤立节点和可能有错误连接的节点
        
        这是一个通用的后处理步骤，不依赖特定的节点ID或测试用例
        """
        # 第一步：查找所有孤立节点
        orphan_nodes = []
        for node in self.node_manager.get_all_nodes():
            if node.get('text') in ['开始', '结束'] or node.get('type') in ['start', 'end']:
                continue
            
            outgoing = self.connection_manager.get_connections_from_node(node['id'])
            if not outgoing:
                orphan_nodes.append(node)
        
        if orphan_nodes:
            orphan_suffixes = [n['id'].split('_')[-1] for n in orphan_nodes]
            logger.debug(f"[通用修复] 发现{len(orphan_nodes)}个孤立节点: {orphan_suffixes}")
            
            # 为每个孤立节点查找目标
            for node in orphan_nodes:
                target, conn_type = self._find_target_for_orphan_node(node)
                if target and conn_type:
                    self.connection_manager.add_connection(
                        node['id'], conn_type, target['id'], 'up'
                    )
        
        # 第二步：检查并修正可能错误的连接
        # 特征：从decision.right进入的process节点，如果连接到循环但附近有后续语句，可能是错误的
        self._fix_potentially_wrong_connections()
    
    def _fix_potentially_wrong_connections(self):
        """
        修复可能错误的连接
        
        检查所有从decision.right进入的process节点，
        如果它们的出站连接不合理，修正它们
        """
        print("[修正方法] 开始检查可能错误的连接...")
        nodes_to_fix = []
        
        from_decision_right_count = 0
        checked_count = 0
        
        for node in self.node_manager.get_all_nodes():
            if node.get('text') in ['开始', '结束'] or node.get('type') in ['start', 'end']:
                continue
            
            node_id = node.get('id')
            
            # 检查入站连接
            incoming = self.connection_manager.get_connections_to_node(node_id)
            from_decision_right = any(
                c['start_point_type'] == 'right' and 
                self.node_manager.get_node_by_id(c['start_item_id']).get('type') == 'decision'
                for c in incoming
            )
            
            if not from_decision_right:
                continue
            
            from_decision_right_count += 1
            
            # 检查出站连接
            outgoing = self.connection_manager.get_connections_from_node(node_id)
            if len(outgoing) != 1:
                continue  # 只处理有唯一出站连接的节点
            
            checked_count += 1
            
            current_conn = outgoing[0]
            current_target_id = current_conn['end_item_id']
            current_point_type = current_conn['start_point_type']
            
            # **检查1**：是否连到自己？
            if current_target_id == node_id:
                logger.debug(f"[修正] {node_id} 连到自己，需要修正")
                nodes_to_fix.append(node)
                continue
            
            # **检查2**：暂时不做额外检查，避免引入新问题
            # 只处理连到自己的明显错误
        
        print(f"[修正统计] 从decision.right进入的节点: {from_decision_right_count}个")
        print(f"[修正统计] 检查了: {checked_count}个")
        print(f"[修正统计] 需要修正: {len(nodes_to_fix)}个")
        
        # 修正这些节点
        for node in nodes_to_fix:
            node_id = node.get('id')
            # 删除现有的错误连接
            self.connection_manager.connections = [
                c for c in self.connection_manager.connections 
                if c['start_item_id'] != node_id
            ]
            
            # 重新查找正确的目标
            target, conn_type = self._find_target_for_orphan_node(node)
            if target and conn_type:
                node_suffix = node_id.split('_')[-1] if '_' in node_id else '?'
                target_suffix = target.get('id').split('_')[-1] if '_' in target.get('id') else '?'
                print(f"[修正] 重新连接 _{node_suffix} ({conn_type}) -> _{target_suffix}")
                self.connection_manager.add_connection(
                    node_id, conn_type, target['id'], 'up'
                )
    
    def _find_target_for_orphan_node(self, orphan: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        为孤立节点查找目标节点和连接类型
        
        通用算法：
        1. 检查节点的入站连接，判断它在什么结构中
        2. 查找所有候选目标节点
        3. 根据节点特征评分，选择最佳目标
        """
        orphan_id = orphan.get('id')
        orphan_x = orphan.get('x', 0)
        orphan_y = orphan.get('y', 0)
        base_x = -4600.0
        
        # 1. 分析入站连接
        incoming = self.connection_manager.get_connections_to_node(orphan_id)
        from_decision_right = False
        from_decision_down = False
        
        for conn in incoming:
            start = self.node_manager.get_node_by_id(conn['start_item_id'])
            if start and start.get('type') == 'decision':
                if conn['start_point_type'] == 'right':
                    from_decision_right = True
                elif conn['start_point_type'] == 'down':
                    from_decision_down = True
        
        # 2. 识别中转节点（汇聚点：多个入站+向下出站）
        intermediate_nodes = set()
        for node in self.node_manager.get_all_nodes():
            incoming = self.connection_manager.get_connections_to_node(node.get('id'))
            outgoing = self.connection_manager.get_connections_from_node(node.get('id'))
            
            # **改进的中转站识别**：有多个入站连接且有向下出站连接
            if len(incoming) >= 2:
                for conn in outgoing:
                    if conn['start_point_type'] == 'down':
                        target = self.node_manager.get_node_by_id(conn['end_item_id'])
                        if target and target.get('y', 0) >= node.get('y', 0):
                            # 这是一个汇聚点
                            intermediate_nodes.add(node.get('id'))
                            break
        
        # 3. 收集候选节点
        down_candidates = []
        right_candidates = []
        
        for node in self.node_manager.get_all_nodes():
            # **关键修复**：跳过自己、开始、结束节点
            if node.get('id') == orphan_id or node.get('text') in ['开始', '结束']:
                continue
            # **额外安全检查**：确保不会连接到自己
            if node.get('id') == orphan_id:
                continue
            
            node_y = node.get('y', 0)
            node_x = node.get('x', 0)
            y_diff = node_y - orphan_y
            x_diff = abs(node_x - orphan_x)
            is_main = abs(node_x - base_x) < 50
            is_decision = node.get('type') == 'decision'
            
            # 向下候选（注意：只考虑y_diff > 0的节点）
            if y_diff > 0 and y_diff <= 600:
                # **关键过滤1**：跳过汇聚点（中转节点）
                if node.get('id') in intermediate_nodes and y_diff < 200:
                    continue
                
                # **简化过滤**：只跳过同一y坐标的节点（可能是平行分支）
                # 如果候选节点的y坐标与orphan非常接近（<50），它们可能是平行分支
                if abs(y_diff) < 50:
                    continue  # 跳过同一行的节点
                
                # **关键过滤3**：如果候选节点从process进入（不是decision），
                # 它可能是另一个if块的内部语句，不应作为其他if块的后续语句
                if y_diff < 150:  # 只对近距离候选应用此过滤
                    node_incoming = self.connection_manager.get_connections_to_node(node.get('id'))
                    is_from_process = any(
                        self.node_manager.get_node_by_id(c['start_item_id']).get('type') == 'process'
                        for c in node_incoming
                    )
                    if is_from_process:
                        continue  # 跳过从process进入的节点（可能是内部语句）
                
                # 评分：距离越近越好，decision优先，主流程优先
                score = y_diff
                
                # **改进评分**：decision节点和非decision节点区别对待
                # **关键改进**：x距离是重要因素，x距离大说明不是同一个语句块
                if is_decision:
                    # decision节点（可能是后续的if-else条件）
                    if y_diff < 300:
                        score *= 0.2 if x_diff < 400 else 0.5
                    else:
                        score *= 0.4
                else:
                    # process/input节点（可能是后续语句或其他）
                    # x距离是关键因素：x距离大的节点很可能不是后续语句
                    if y_diff < 150:
                        if x_diff < 250:
                            score *= 0.1  # 非常接近
                        elif x_diff < 400:
                            score *= 0.4  # 较近
                        else:
                            score *= 1.5  # 较远，大幅惩罚
                    elif y_diff < 300:
                        if x_diff < 300:
                            score *= 0.3
                        elif x_diff < 500:
                            score *= 0.7
                        else:
                            score *= 2.0  # x距离远，大幅惩罚
                    else:
                        score *= 1.5
                
                down_candidates.append((node, score, y_diff, x_diff))
            
            # 向上候选（循环回连）
            elif y_diff < 0 and is_decision:
                # **改进**：只考虑合理距离的循环节点
                if 200 < abs(y_diff) < 1000:
                    # **通用的循环节点识别**：
                    # 1. 检查文本中是否包含循环关键词
                    # 2. 检查该decision是否有right出站连接（循环特征）
                    node_text = node.get('text', '')
                    
                    # 方法1：文本特征（最重要）
                    has_loop_keyword = ('判断：' in node_text or '循环' in node_text or 
                                       'for' in node_text.lower() or 'while' in node_text.lower())
                    
                    # 方法2：比较运算符（循环条件通常有<或<=）
                    has_comparison = '<' in node_text or '<=' in node_text or '>' in node_text or '>=' in node_text
                    
                    # 方法3：结构特征 - 检查是否有right出站连接
                    node_outgoing = self.connection_manager.get_connections_from_node(node.get('id'))
                    has_right_out = any(c['start_point_type'] == 'right' for c in node_outgoing)
                    
                    # 方法4：位置特征 - 在主流程上（x坐标接近base_x）
                    is_main_flow_decision = is_main and abs(y_diff) < 800
                    
                    # **更严格的综合判断**：必须满足文本特征或（比较运算符+结构特征+位置特征）
                    is_loop_node = has_loop_keyword or (has_comparison and has_right_out and is_main_flow_decision)
                    
                    # **额外验证**：如果只有结构和位置特征，检查是否有入站从right（循环特征）
                    if not has_loop_keyword and is_loop_node:
                        node_incoming = self.connection_manager.get_connections_to_node(node.get('id'))
                        has_right_in = any(c['end_point_type'] == 'up' and c['start_point_type'] == 'right' 
                                          for c in node_incoming)
                        if not has_right_in:
                            is_loop_node = False  # 没有循环的入站连接，不是循环节点
                    
                    if is_loop_node:
                        # 评分：距离越近越好，但也考虑特征匹配度
                        score = abs(y_diff)
                        
                        # 如果既有文本特征又有结构特征，优先级更高
                        if has_loop_keyword and has_right_out:
                            score *= 0.7  # 更优先
                        
                        right_candidates.append((node, score, y_diff, x_diff))
        
        # 4. 选择最佳候选
        if from_decision_right:
            # 从if块出来，可能需要回连到循环或连接到后续语句
            down_candidates.sort(key=lambda x: x[1])
            right_candidates.sort(key=lambda x: x[1])
            
            if down_candidates and right_candidates:
                best_down = down_candidates[0]
                best_right = right_candidates[0]
                
                # **通用决策算法**：综合比较down和right的得分
                best_down_y = best_down[2]
                best_down_x = best_down[3]
                best_down_score = best_down[1]
                best_right_score = best_right[1]
                best_down_node = best_down[0]
                best_right_node = best_right[0]
                best_down_type = best_down_node.get('type')
                best_right_y = abs(best_right[2])
                
                # **改进的通用规则**：基于节点类型和距离综合判断
                orphan_suffix = orphan['id'].split('_')[-1] if '_' in orphan['id'] else '?'
                
                # **通用规则1**：如果有process/input类型的down候选
                # 但需要判断它是否是真正的同级后续语句，还是外层语句
                process_or_input_down = [c for c in down_candidates 
                                         if c[0].get('type') in ['process', 'input']]
                
                if process_or_input_down:
                    # 选择y距离最近的process/input节点
                    best_process = process_or_input_down[0]
                    best_process_node = best_process[0]
                    best_process_y = best_process[2]
                    best_process_x = best_process[3]
                    best_process_x_coord = best_process_node.get('x', 0)
                    
                    # **关键判断**：如果process/input节点在主流程上（x接近-4600），
                    # 它更可能是外层语句，不是同一循环的后续语句
                    base_x = -4600.0
                    process_in_main_flow = abs(best_process_x_coord - base_x) < 100
                    
                    # **调试**：
                    logger.debug(f"[检查] _{orphan_suffix}: best_process x={best_process_x_coord}, 主流程?={process_in_main_flow}, has_right?={len(right_candidates)>0}")
                    
                    # **关键改进**：即使process/input候选存在，也要综合评估是否应该right
                    # 如果有right候选，比较两者的合理性
                    if right_candidates:
                        best_right = right_candidates[0]
                        best_right_node = best_right[0]
                        best_right_y = abs(best_right[2])
                        best_right_text = best_right_node.get('text', '')
                        
                        # 判断right候选是否是真正的循环节点（包含循环关键词）
                        is_true_loop = any(kw in best_right_text for kw in ['判断：', '循环', 'for', 'while', '<', '<=', '>', '>='])
                        
                        # **详细调试**
                        right_suffix = best_right_node.get('id').split('_')[-1]
                        logger.debug(f"[规则1详情] _{orphan_suffix}: process_y={best_process_y}, process_in_main={process_in_main_flow}, process_x={best_process_x}")
                        logger.debug(f"  right候选: _{right_suffix}, is_true_loop={is_true_loop}, text={best_right_text[:30]}")
                        
                        # **通用规则**：如果down候选y距离>100且（在主流程上 或 x距离>400），优先考虑right
                        if best_process_y > 100 and (process_in_main_flow or best_process_x > 400):
                            if is_true_loop:
                                logger.debug(f"[决策] _{orphan_suffix} 规则1a: right到循环_{right_suffix}（down候选y>100且在主流程或x>400）")
                                return best_right_node, 'right'
                            else:
                                logger.debug(f"[跳过1a] right候选不是真循环")
                        else:
                            logger.debug(f"[跳过1a] 条件不满足: y>100?={best_process_y>100}, 主流程或x>400?={process_in_main_flow or best_process_x>400}")
                    
                    # **额外判断**：如果y距离适中（>=100）且x距离也适中（150-300）
                    # 可能是平行分支而不是后续语句，应该考虑right
                    if best_process_y >= 100 and 150 <= best_process_x <= 300:
                        if right_candidates:
                            # 有right候选，且right距离合理，选right
                            best_right_y_abs = abs(right_candidates[0][2])
                            if best_right_y_abs < 600:  # 放宽阈值
                                right_suffix = right_candidates[0][0].get('id').split('_')[-1]
                                logger.debug(f"[决策] _{orphan_suffix} 规则1a2: right到循环_{right_suffix}（down可能是平行分支,y={best_process_y},x={best_process_x}）")
                                return right_candidates[0][0], 'right'
                    
                    # 如果距离很近（y<100），肯定选down
                    if best_process_y < 100:
                        logger.debug(f"[决策] _{orphan_suffix} 规则1b: down到process/input (y很近={best_process_y})")
                        return best_process[0], 'down'
                    
                    # 如果没有选择right，且距离合理（y<=300）且不在主流程上，选down
                    if best_process_y <= 300 and not process_in_main_flow:
                        logger.debug(f"[决策] _{orphan_suffix} 规则1c: down到process/input (y={best_process_y}, 不在主流程)")
                        return best_process[0], 'down'
                
                # 规则3：如果down是decision且距离较远（>=300），优先选right
                if best_down_type == 'decision' and best_down_y >= 300:
                    logger.debug(f"[决策] _{orphan_suffix} 规则3: right（down是远距离decision）")
                    return best_right_node, 'right'
                
                # 规则4：如果down的y距离适中（<300），检查节点类型和特征
                if best_down_y < 300:
                    # 如果x距离很远（>=700），可能不是后续语句，选right
                    if best_down_x >= 700:
                        logger.debug(f"[决策] _{orphan_suffix} 规则4a: right（x距离太远）")
                        return best_right_node, 'right'
                    # **改进**：如果best_down是decision，比较得分和特征
                    if best_down_type == 'decision':
                        # 检查down候选是否在主流程上（x接近base_x）
                        best_down_x_coord = best_down_node.get('x', 0)
                        down_is_main_flow = abs(best_down_x_coord - base_x) < 50
                        
                        # decision节点作为后续语句不太常见，需要更严格的判断
                        # 如果right也可用，比较它们的特征
                        if right_candidates:
                            # 检查right是否是真正的循环节点（有循环关键词）
                            best_right_text = best_right_node.get('text', '')
                            is_true_loop = '判断：' in best_right_text or '循环' in best_right_text or 'for' in best_right_text.lower() or 'while' in best_right_text.lower()
                            
                            # **更严格的条件**：当down的x距离一般（>=300）或y距离不是很近（>=150）时，考虑right
                            # 但如果down在主流程上且y距离很近（<150），优先选down
                            if is_true_loop:
                                if down_is_main_flow and best_down_y < 150:
                                    # down在主流程上且很近，选down
                                    pass
                                elif best_down_x >= 300 or best_down_y >= 150:
                                    # down的距离不是特别好，选right
                                    logger.debug(f"[决策] _{orphan_suffix} 规则4b-1: right到真循环")
                                    return best_right_node, 'right'
                        # 否则选down
                        logger.debug(f"[决策] _{orphan_suffix} 规则4b-2: down到decision")
                        return best_down_node, 'down'
                    # 如果best_down是process/input，选down
                    else:
                        logger.debug(f"[决策] _{orphan_suffix} 规则4c: down到process/input")
                        return best_down_node, 'down'
                
                # 规则5：默认选right（到循环）
                logger.debug(f"[决策] _{orphan_suffix} 规则5: 默认right")
                return best_right_node, 'right'
            elif down_candidates:
                return down_candidates[0][0], 'down'
            elif right_candidates:
                return right_candidates[0][0], 'right'
        else:
            # 从其他地方出来，优先选择down
            if down_candidates:
                down_candidates.sort(key=lambda x: x[1])
                return down_candidates[0][0], 'down'
            elif right_candidates:
                right_candidates.sort(key=lambda x: x[1])
                return right_candidates[0][0], 'right'
        
        return None, None
    
    def _build_output(self) -> Dict[str, Any]:
        """构建输出JSON"""
        return {
            "version": "1.0",
            "items": self.node_manager.get_all_nodes(),
            "connections": self.connection_manager.get_all_connections()
        }
    
    # ===== process_statement 和 process_block 方法 =====
    # 这两个方法保持与原代码类似的结构，但使用管理器来操作节点和连接
    
    def process_statement(self, statement: Dict[str, Any], x: float, y: float,
                         parent_node: Dict[str, Any] = None, connection_dir: str = "down",
                         context_type: str = None, parent_block: List[Dict[str, Any]] = None,
                         block_index: int = -1, parent_loop_statement: Dict[str, Any] = None) -> Tuple[Dict[str, Any], bool, float, float]:
        """处理单个语句
        
        参数:
            parent_loop_statement: 父循环语句（用于嵌套结构中传递循环信息）
        """
        if statement.get("tag") == "block":
            return parent_node, False, x, y
        
        node_text = statement.get("translated", "")
        node_type = "process"
        
        # 根据tag确定节点类型
        tag = statement.get("tag", "")
        if tag == "i/o":
            node_type = "input"
        elif tag in ["condition", "branch", "loop"]:
            if "while" in statement.get("original_unit", "") and tag == "loop":
                node_type = "decision"
            elif "else" in statement.get("original_unit", "") and node_text == "否则":
                return self._process_else_block(statement, x, y, parent_node)
            else:
                node_type = "decision"
        
        # 处理return语句
        if "return" in node_text or "返回" in node_text:
            return self._process_return_statement(x, y, parent_node, connection_dir)
        
        # 处理break语句
        if "break" in node_text and node_text.strip().endswith("break;"):
            return self._process_break_statement(
                statement, x, y, parent_node, connection_dir, 
                context_type, parent_loop_statement
            )
        
        # 处理continue语句
        if "continue" in node_text and node_text.strip().endswith("continue;"):
            return self._process_continue_statement(
                statement, x, y, parent_node, connection_dir,
                context_type, parent_loop_statement
            )
        
        # 创建节点
        current_node = self.node_manager.create_node(node_type, node_text, x, y)
        
        # 保存上下文类型
        if context_type:
            statement["_context_type"] = context_type
        
        # 添加连接
        if parent_node:
            self.connection_manager.add_connection(
                parent_node["id"], connection_dir, current_node["id"], "up"
            )
        
        # 处理子节点
        has_return, next_x, next_y = self._process_statement_children(
            statement, current_node, x, y, context_type, parent_block, parent_loop_statement
        )
        
        # 确保后续语句在所有分支之后
        if tag in ["condition", "branch"] and statement.get("children"):
            next_y = self._adjust_y_after_branches(statement, y, next_y)
        
        self.node_manager.last_node = current_node
        return current_node, has_return, next_x, next_y
    
    def _process_else_block(self, statement: Dict[str, Any], x: float, y: float,
                           parent_node: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, float, float]:
        """处理else块"""
        child_has_return = False
        if parent_node:
            condition_node_y = parent_node["y"]
            child_next_y = condition_node_y + self.condition_offset_y
        else:
            child_next_y = y
        
        last_child_node = None
        if "children" in statement and statement["children"]:
            for child in statement["children"]:
                if isinstance(child, dict):
                    if child.get("type") == "else_block":
                        block_x = child.get("x", x)
                        logger.debug(f"else_block的x坐标: {block_x}")
                        
                        if parent_node:
                            else_block_start_y = parent_node["y"] + self.condition_offset_y
                        else:
                            else_block_start_y = child_next_y
                        
                        for grandchild in child.get("children", []):
                            if isinstance(grandchild, dict):
                                use_dir = "down"
                                if parent_node and not last_child_node:
                                    grandchild_current, grandchild_return, grandchild_x, grandchild_y = self.process_statement(
                                        grandchild, block_x, else_block_start_y,
                                        parent_node, "down"
                                    )
                                else:
                                    grandchild_current, grandchild_return, grandchild_x, grandchild_y = self.process_statement(
                                        grandchild, block_x, child_next_y, last_child_node, use_dir
                                    )
                                logger.debug(f"处理else_block的子节点: x={block_x}, y={child_next_y}")
                                last_child_node = grandchild_current
                                child_has_return = child_has_return or grandchild_return
                                child_next_y = max(child_next_y, grandchild_y)
                                block_x = grandchild_x
                    else:
                        child_current, child_return, child_x, child_y = self.process_statement(
                            child, x, child_next_y, parent_node, "down"
                        )
                        last_child_node = child_current
                        child_has_return = child_has_return or child_return
                        child_next_y = max(child_next_y, child_y)
        
        if last_child_node:
            return last_child_node, child_has_return, x, child_next_y
        return parent_node, child_has_return, x, child_next_y
    
    def _process_return_statement(self, x: float, y: float, parent_node: Dict[str, Any],
                                  connection_dir: str) -> Tuple[Dict[str, Any], bool, float, float]:
        """处理return语句"""
        end_node = self.node_manager.create_node("end", "结束", x, y)
        
        if parent_node:
            self.connection_manager.add_connection(
                parent_node["id"], connection_dir, end_node["id"], "up"
            )
        
        self.node_manager.end_node = end_node
        self.node_manager.last_node = end_node
        return end_node, True, x, y + self.level_height
    
    def _process_break_statement(self, statement: Dict[str, Any], x: float, y: float,
                                parent_node: Dict[str, Any], connection_dir: str,
                                context_type: str, parent_loop_statement: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, float, float]:
        """
        处理break语句
        
        break语句的left连接到循环外的第一个语句的up
        """
        # 创建break节点
        break_node = self.node_manager.create_node("process", "break;", x, y)
        
        # 连接到父节点
        if parent_node:
            self.connection_manager.add_connection(
                parent_node["id"], connection_dir, break_node["id"], "up"
            )
        
        # 保存break节点和循环信息，稍后统一处理连接到循环外
        # 标记这个语句为break，并保存必要的上下文信息
        statement["_is_break"] = True
        statement["_break_node"] = break_node
        statement["_parent_loop_statement"] = parent_loop_statement
        
        self.node_manager.last_node = break_node
        # break类似return，后续语句不可达
        return break_node, True, x, y + self.level_height
    
    def _process_continue_statement(self, statement: Dict[str, Any], x: float, y: float,
                                   parent_node: Dict[str, Any], connection_dir: str,
                                   context_type: str, parent_loop_statement: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, float, float]:
        """
        处理continue语句
        
        continue语句的right连接到循环的up（循环条件节点）
        """
        # 创建continue节点
        continue_node = self.node_manager.create_node("process", "continue;", x, y)
        
        # 连接到父节点
        if parent_node:
            self.connection_manager.add_connection(
                parent_node["id"], connection_dir, continue_node["id"], "up"
            )
        
        # 获取循环条件节点
        loop_condition_node = None
        if parent_loop_statement:
            loop_condition_node = self.context_manager.get_loop_condition_node(parent_loop_statement)
        
        # 如果找到了循环条件节点，立即连接
        if loop_condition_node:
            self.connection_manager.add_connection(
                continue_node["id"], "right", loop_condition_node["id"], "up"
            )
            logger.debug(f"[continue] 连接到循环: {continue_node['id']} -> {loop_condition_node['id']}")
        else:
            # 如果没找到，保存信息稍后处理
            logger.warning(f"[continue] 未找到循环条件节点，稍后处理")
            statement["_is_continue"] = True
            statement["_continue_node"] = continue_node
            statement["_parent_loop_statement"] = parent_loop_statement
        
        self.node_manager.last_node = continue_node
        # continue类似return，后续语句不可达
        return continue_node, True, x, y + self.level_height
    
    def _process_statement_children(self, statement: Dict[str, Any], current_node: Dict[str, Any],
                                   x: float, y: float, context_type: str,
                                   parent_block: List[Dict[str, Any]],
                                   parent_loop_statement: Dict[str, Any] = None) -> Tuple[bool, float, float]:
        """处理语句的子节点
        
        参数:
            parent_loop_statement: 父循环语句（用于嵌套结构）
        """
        has_return = False
        next_x = x
        next_y = y + self.level_height
        
        if "children" not in statement or not statement["children"]:
            return has_return, next_x, next_y
        
        # 特殊处理：switch 的 case 分支（children 中包含 type == 'case_block'）
        try:
            children = statement.get("children", [])
            has_case_block = any(
                isinstance(child, dict) and child.get("type") == "case_block"
                for child in children
            )
        except Exception:
            has_case_block = False
        
        if has_case_block:
            return self._process_switch_cases_in_statement(
                statement, current_node, x, y, context_type, parent_block, parent_loop_statement
            )
        
        for child in statement["children"]:
            if isinstance(child, dict):
                logger.debug(f"处理子节点: tag={child.get('tag')}, translated={child.get('translated')}, type={child.get('type')}")
                
                if "type" in child:
                    # 处理特殊类型的块
                    if child["type"] == "if_block":
                        has_return, next_y = self._process_if_block(
                            child, statement, current_node, x, y, context_type, parent_block,
                            parent_loop_statement
                        )
                    elif child["type"] == "else_block":
                        has_return, next_y = self._process_else_block_in_statement(
                            child, statement, current_node, x, y, context_type, parent_block,
                            parent_loop_statement
                        )
                    elif child["type"] == "while_true_block":
                        # **关键修复**：传递statement（while语句）作为parent_loop_statement
                        next_y = self._process_while_block_in_statement(
                            child, current_node, x, y, parent_statement=statement
                        )
                    elif child["type"] == "for_true_block":
                        # **关键修复**：传递statement（for语句）作为parent_loop_statement
                        next_y = self._process_for_block_in_statement(
                            child, current_node, x, y, parent_statement=statement
                        )
                else:
                    # 递归处理普通子节点
                    # **关键修复**：传递parent_loop_statement
                    child_current, child_return, child_x, child_y = self.process_statement(
                        child, next_x, next_y, current_node, "down",
                        parent_loop_statement=parent_loop_statement
                    )
                    current_node = child_current
                    has_return = has_return or child_return
                    next_y = child_y
        
        return has_return, next_x, next_y

    def _process_switch_cases_in_statement(self, statement: Dict[str, Any], current_node: Dict[str, Any],
                                           x: float, y: float, context_type: str,
                                           parent_block: List[Dict[str, Any]],
                                           parent_loop_statement: Dict[str, Any] = None) -> Tuple[bool, float, float]:
        """
        处理 switch 的 case 分支：
        - 多选择块（当前 decision 节点）的 down 连接到每个 case 第一个块的 up
        - 每个 case 在同一高度，水平向右排列
        - 每个 case 内部语句正常解析
        - 每个 case 的最后一个模块的 down 将在 process_block 中统一连接到 switch 后的第一个块
        """
        has_return = False
        children = [c for c in statement.get("children", []) if isinstance(c, dict) and c.get("type") == "case_block"]
        if not children or not current_node:
            return has_return, x, y + self.level_height
        
        # 布局参数：所有 case 的起始 y 相同，x 依次向右偏移
        base_case_y = y + self.condition_offset_y
        base_case_x = x + self.condition_offset_x
        case_spacing = max(self.condition_offset_x * 2, 150)
        
        last_nodes = []
        max_case_y = base_case_y
        
        for idx, case_block in enumerate(children):
            case_x = base_case_x + idx * case_spacing
            
            # 处理单个 case 分支块
            case_current, case_return, case_end_x, case_end_y, _ = self.process_block(
                case_block.get("children", []),
                case_x,
                base_case_y,
                current_node,
                "down",  # 要求：switch 的 down 连接到各个 case 的 up
                context_type=context_type,
                parent_statement=statement,
                parent_loop_statement=parent_loop_statement
            )
            
            if case_current:
                last_nodes.append(case_current)
                max_case_y = max(max_case_y, case_end_y)
            
            has_return = has_return or case_return
        
        # 记录每个 case 的最后节点，供后续与 switch 后第一个块相连
        if last_nodes:
            statement["_switch_case_last_nodes"] = last_nodes
        
        # switch 之后的整体 y 位置取所有 case 中最大的 y
        next_x = x
        next_y = max_case_y
        return has_return, next_x, next_y
    
    def _process_if_block(self, child: Dict[str, Any], statement: Dict[str, Any],
                         current_node: Dict[str, Any], x: float, y: float,
                         context_type: str, parent_block: List[Dict[str, Any]],
                         parent_loop_statement: Dict[str, Any] = None) -> Tuple[bool, float]:
        """处理if块
        
        参数:
            parent_loop_statement: 父循环语句（用于嵌套结构）
        """
        # 计算if块内最长的语句链数量n
        max_statement_chain = self._calculate_max_statement_chain(child)
        logger.debug(f"if块内最长语句链数量: {max_statement_chain}")
        
        # 检查是否需要二倍偏移
        has_next_if_in_n_statements = self._check_next_if_in_n_statements(
            statement, max_statement_chain
        )
        
        # 决定x偏移量
        condition_x_offset = self.condition_offset_x * 2 if has_next_if_in_n_statements else self.condition_offset_x
        logger.debug(f"if块最终决定：是否需要二倍偏移={has_next_if_in_n_statements}, 使用x偏移量={condition_x_offset}")
        
        # 确定上下文类型
        if_block_context_type = context_type or self._infer_context_type(parent_block)
        final_if_context_type = if_block_context_type or 'if_block'
        
        # 处理if块
        # **关键修复**：传递parent_loop_statement，这样嵌套的if-else才能获取正确的循环节点
        if_current, if_return, if_x, if_y, _ = self.process_block(
            child["children"],
            x + condition_x_offset,
            y + self.condition_offset_y,
            current_node,
            "right",
            context_type=final_if_context_type,
            parent_statement=statement,
            parent_loop_statement=parent_loop_statement
        )
        
        # 保存信息
        child["x"] = x + condition_x_offset
        statement["_if_block_info"] = {
            "last_node": if_current,
            "has_return": if_return
        }
        statement["_if_block_max_y"] = if_y
        
        # **关键修复**：对于嵌套的if块（if_block_context_type不是main），
        # 确保回连信息被正确处理
        # 这在process_block的_save_if_else_reconnect_in_block中应该已经处理了
        # 但为了确保，如果是if_block类型，我们也在这里保存
        
        return if_return, if_y
    
    def _process_else_block_in_statement(self, child: Dict[str, Any], statement: Dict[str, Any],
                                        current_node: Dict[str, Any], x: float, y: float,
                                        context_type: str, parent_block: List[Dict[str, Any]],
                                        parent_loop_statement: Dict[str, Any] = None) -> Tuple[bool, float]:
        """处理else块（在语句中）
        
        参数:
            parent_loop_statement: 父循环语句（用于嵌套结构）
        """
        else_block_context_type = context_type or self._infer_context_type(parent_block)
        final_else_context_type = else_block_context_type or 'else_block'
        
        # **关键修复**：传递parent_loop_statement
        else_current, else_return, else_x, else_y, _ = self.process_block(
            child["children"],
            x + self.condition_offset_x * 2,
            y + self.condition_offset_y,
            current_node,
            "down",
            context_type=final_else_context_type,
            parent_statement=statement,
            parent_loop_statement=parent_loop_statement
        )
        
        child["x"] = x + self.condition_offset_x * 2
        statement["_else_block_info"] = {
            "last_node": else_current,
            "has_return": else_return
        }
        statement["_else_block_max_y"] = else_y
        
        return else_return, else_y
    
    def _process_while_block_in_statement(self, child: Dict[str, Any], 
                                         current_node: Dict[str, Any],
                                         x: float, y: float,
                                         parent_statement: Dict[str, Any] = None) -> float:
        """处理while块（在语句中）
        
        参数:
            parent_statement: while循环语句（用于注册循环条件节点）
        """
        logger.debug(f"\n检测到while_true_block，需要计算偏移量")
        
        # **关键修复**：注册while循环的条件节点
        if parent_statement and current_node:
            self.context_manager.register_loop_condition_node(parent_statement, current_node)
        
        loop_x_offset = self.loop_processor.calculate_loop_offset(child, self.loop_offset_x, is_while=True)
        
        # **关键修复**：传递parent_statement作为parent_loop_statement
        loop_current, loop_return, loop_x, loop_y, _ = self.process_block(
            child["children"],
            x + loop_x_offset,
            y + self.loop_offset_y,
            current_node,
            "down",
            context_type='loop',
            parent_statement=parent_statement,
            parent_loop_statement=parent_statement
        )
        
        # 循环体的最后一个节点的right连接到循环判断块的up
        self.connection_manager.add_connection(
            loop_current["id"], "right", current_node["id"], "up"
        )
        
        return loop_y
    
    def _process_for_block_in_statement(self, child: Dict[str, Any],
                                       current_node: Dict[str, Any],
                                       x: float, y: float,
                                       parent_statement: Dict[str, Any] = None) -> float:
        """处理for块（在语句中）
        
        参数:
            parent_statement: for循环语句（用于注册循环条件节点）
        """
        # **关键修复**：注册for循环的条件节点
        if parent_statement and current_node:
            self.context_manager.register_loop_condition_node(parent_statement, current_node)
        
        # **关键修复**：传递parent_statement作为parent_loop_statement
        loop_current, loop_return, loop_x, loop_y, _ = self.process_block(
            child["children"],
            x + self.loop_offset_x,
            y + self.loop_offset_y,
            current_node,
            "down",
            context_type='loop',
            parent_statement=parent_statement,
            parent_loop_statement=parent_statement
        )
        
        self.connection_manager.add_connection(
            loop_current["id"], "right", current_node["id"], "up"
        )
        
        return loop_y
    
    def _calculate_max_statement_chain(self, child: Dict[str, Any]) -> int:
        """计算最长语句链"""
        max_statement_chain = 0
        
        if "children" in child:
            for grandchild in child["children"]:
                if isinstance(grandchild, dict) and grandchild.get('type') != 'else_block':
                    if "children" in grandchild:
                        for great_grandchild in grandchild["children"]:
                            if isinstance(great_grandchild, dict) and great_grandchild.get('tag') != 'block':
                                chain_length = count_statement_chain(great_grandchild)
                                if chain_length > max_statement_chain:
                                    max_statement_chain = chain_length
        
        return max_statement_chain
    
    def _check_next_if_in_n_statements(self, statement: Dict[str, Any], 
                                      max_statement_chain: int) -> bool:
        """检查后续n条语句内是否有新的if-else模块"""
        if max_statement_chain <= 0:
            return False
        
        logger.debug(f"开始检查从if模块结束后{max_statement_chain}条语句内是否有新的if-else模块")
        
        has_next_if_in_n_statements = False
        counted_statements = 0
        
        def check_statements(stmts, max_count, is_else_block=False):
            nonlocal counted_statements, has_next_if_in_n_statements
            
            if counted_statements >= max_count or has_next_if_in_n_statements:
                return
            
            for stmt in stmts:
                if not isinstance(stmt, dict):
                    continue
                
                counted_statements += 1
                stmt_type = stmt.get('type', 'unknown')
                stmt_tag = stmt.get('tag', 'unknown')
                logger.debug(f"从if模块结束后计数: 第{counted_statements}条语句 - 类型: {stmt_type}, 标签: {stmt_tag}")
                
                if stmt != statement and stmt_type in ['if_block', 'while_block', 'while_true_block']:
                    has_next_if_in_n_statements = True
                    logger.debug(f"在第{counted_statements}条语句发现新的条件/循环模块: {stmt_type}，需要二倍偏移")
                    return
                
                if "children" in stmt:
                    check_statements(stmt["children"], max_count, is_else_block=stmt_type == 'else_block')
                    if counted_statements >= max_count or has_next_if_in_n_statements:
                        return
        
        # 检查当前if-else模块中的所有语句
        for child in statement.get("children", []):
            if isinstance(child, dict) and "children" in child:
                logger.debug(f"检查块内的语句，块类型: {child.get('type', 'unknown')}")
                check_statements(child["children"], max_statement_chain)
                if counted_statements >= max_statement_chain or has_next_if_in_n_statements:
                    break
        
        # 检查后续语句
        if not has_next_if_in_n_statements and counted_statements < max_statement_chain:
            if hasattr(self, 'current_block') and self.current_block:
                for i, stmt in enumerate(self.current_block):
                    if stmt == statement:
                        remaining = max_statement_chain - counted_statements
                        next_stmts = self.current_block[i+1:i+1+remaining]
                        logger.debug(f"检查if-else模块之后的{len(next_stmts)}条语句")
                        check_statements(next_stmts, max_statement_chain)
                        break
        
        logger.debug(f"检查完成，是否在{max_statement_chain}条语句内发现新的if-else模块: {has_next_if_in_n_statements}")
        return has_next_if_in_n_statements
    
    def _infer_context_type(self, parent_block: List[Dict[str, Any]]) -> str:
        """推断上下文类型"""
        if not parent_block:
            return 'main'
        
        # 检查是否在循环中
        if any("for" in stmt.get("original_unit", "").lower() or 
               "while" in stmt.get("original_unit", "").lower() or
               stmt.get("tag") == "loop"
               for stmt in parent_block if isinstance(stmt, dict)):
            return 'loop'
        
        # 检查是否在if_block中
        if any(stmt.get("type") == "if_block" for stmt in parent_block if isinstance(stmt, dict)):
            return 'if_block'
        
        # 检查是否在else_block中
        if any(stmt.get("type") == "else_block" for stmt in parent_block if isinstance(stmt, dict)):
            return 'else_block'
        
        return 'main'
    
    def _adjust_y_after_branches(self, statement: Dict[str, Any], y: float, next_y: float) -> float:
        """调整分支后的y坐标"""
        max_branch_y = y
        if_block_max_y = statement.get("_if_block_max_y")
        else_block_max_y = statement.get("_else_block_max_y")
        
        if if_block_max_y is not None:
            max_branch_y = max(max_branch_y, if_block_max_y)
        if else_block_max_y is not None:
            max_branch_y = max(max_branch_y, else_block_max_y)
        
        return max(next_y, max_branch_y + self.level_height)
    
    def process_block(self, block: List[Dict[str, Any]], x: float, y: float,
                     parent_node: Dict[str, Any] = None, connection_dir: str = "down",
                     context_type: str = None, parent_statement: Dict[str, Any] = None,
                     parent_loop_statement: Dict[str, Any] = None) -> Tuple[
        Dict[str, Any], bool, float, float, Dict[str, Any]]:
        """处理代码块
        
        参数:
            parent_loop_statement: 父循环语句（在嵌套结构中传递最近的循环）
        """
        current_node = parent_node
        has_return = False
        current_x = x
        current_y = y
        if_block_last_node = None
        # 待与后续第一个语句连接的 switch case 最后节点列表
        pending_switch_case_last_nodes: List[Dict[str, Any]] = []
        
        # **关键**：如果context_type是loop且parent_statement存在，它就是循环语句
        if context_type == 'loop' and parent_statement and not parent_loop_statement:
            parent_loop_statement = parent_statement
        
        for idx, statement in enumerate(block):
            if isinstance(statement, dict):
                if statement.get("tag") == "block":
                    continue
                
                # 确定连接方向
                use_dir = connection_dir if current_node == parent_node else "down"
                
                # 正常处理当前语句
                stmt_current, stmt_return, stmt_x, stmt_y = self.process_statement(
                    statement, current_x, current_y, current_node, use_dir,
                    context_type=context_type, parent_block=block, block_index=idx,
                    parent_loop_statement=parent_loop_statement
                )

                # 如果存在挂起的 switch case 末尾节点，将它们的down连到当前语句的up
                if pending_switch_case_last_nodes and stmt_current:
                    for last_node in pending_switch_case_last_nodes:
                        if last_node and last_node.get("id") != stmt_current.get("id"):
                            self.connection_manager.add_connection(
                                last_node["id"], "down", stmt_current["id"], "up"
                            )
                    pending_switch_case_last_nodes = []
                
                # 处理if块的最后节点
                if statement.get("type") == "if_block" and stmt_current:
                    if "children" in statement:
                        for child in statement["children"]:
                            if isinstance(child, dict) and child.get("type") != "else_block":
                                temp_node, _, _, _, _ = self.process_block(
                                    child.get("children", []),
                                    x + self.condition_offset_x,
                                    current_y + self.condition_offset_y,
                                    stmt_current,
                                    "down",
                                    parent_loop_statement=parent_loop_statement
                                )
                                if temp_node:
                                    if_block_last_node = temp_node
                                break
                
                # 保存回连信息（如果是if-else结构）
                if statement.get("tag") in ["condition", "branch"]:
                    # **关键修复**：传递parent_loop_statement（如果在循环中）
                    # 这样嵌套的if-else才能获取正确的循环节点
                    effective_parent = parent_loop_statement if parent_loop_statement else parent_statement
                    self._save_if_else_reconnect_in_block(
                        statement, stmt_current, idx, block, context_type, effective_parent
                    )
                
                current_node = stmt_current
                has_return = has_return or stmt_return
                current_y = stmt_y
                
                # 如果当前语句是 switch 且记录了各个 case 的最后节点，则将它们挂起，
                # 等待与下一个语句的第一个节点相连
                switch_last_nodes = statement.get("_switch_case_last_nodes")
                if switch_last_nodes:
                    pending_switch_case_last_nodes = switch_last_nodes
        
        return current_node, has_return, current_x, current_y, if_block_last_node
    
    def _save_if_else_reconnect_in_block(self, statement: Dict[str, Any],
                                        stmt_current: Dict[str, Any], idx: int,
                                        block: List[Dict[str, Any]], context_type: str,
                                        parent_statement: Dict[str, Any]):
        """在块中保存if-else回连信息"""
        if_block_info = statement.get("_if_block_info")
        else_block_info = statement.get("_else_block_info")
        
        if if_block_info or else_block_info:
            # 获取实际的上下文类型
            actual_context_type = statement.get("_context_type") or context_type
            
            # 检查是否在循环内
            is_in_loop = False
            loop_condition_node = None
            if actual_context_type == 'loop':
                is_in_loop = True
                # **关键修复**：当context_type为loop时，也要从parent_statement获取loop_condition_node
                if parent_statement:
                    loop_condition_node = self.context_manager.get_loop_condition_node(parent_statement)
            elif parent_statement:
                loop_condition_node = self.context_manager.get_loop_condition_node(parent_statement)
                if loop_condition_node:
                    is_in_loop = True
                    actual_context_type = 'loop'
            
            # **关键修复**：只在没有找到loop_condition_node时才从input_json查找
            # 如果parent_statement已经提供了loop_condition_node，就不要再查找了
            # 否则在嵌套循环中会找到外层循环
            if not loop_condition_node and not is_in_loop:
                for loop_item in self.context_manager.input_json or []:
                    if isinstance(loop_item, dict):
                        loop_tag = loop_item.get("tag", "")
                        loop_orig = loop_item.get("original_unit", "").lower()
                        if ("for" in loop_orig or "while" in loop_orig or loop_tag in ["loop", "condition"]):
                            if is_statement_in_loop(statement, loop_item):
                                loop_condition_node = self.context_manager.get_loop_condition_node(loop_item)
                                if not loop_condition_node:
                                    for loop_idx, item in enumerate(self.context_manager.input_json or []):
                                        if item == loop_item:
                                            loop_condition_node = self.context_manager.get_statement_first_node(loop_idx)
                                            break
                                if loop_condition_node:
                                    is_in_loop = True
                                    actual_context_type = 'loop'
                                    break
            
            # 保存回连信息
            self.context_manager.add_pending_reconnect({
                'if_last_node': if_block_info["last_node"] if if_block_info else None,
                'else_last_node': else_block_info["last_node"] if else_block_info else None,
                'if_has_return': if_block_info["has_return"] if if_block_info else False,
                'else_has_return': else_block_info["has_return"] if else_block_info else False,
                'condition_node': stmt_current,
                'parent_block': block,
                'if_statement_index': idx,
                'context_type': actual_context_type,
                'loop_condition_node': loop_condition_node,
                'parent_statement': parent_statement
            })


def main():
    """主函数：执行转换"""
    from JSON_transfer import main as json_transfer_main
    result = json_transfer_main()
    if not result:
        return False
    
    input_file_path = 'output.json'
    output_file_path = 'output_flowchart.json'
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            input_json = json.load(f)
        
        converter = FlowchartConverter()
        output_json = converter.convert(input_json)
        
        logger.debug(json.dumps(output_json, indent=2, ensure_ascii=False))
        
        # 保存到文件
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(output_json, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n转换完成！结果已保存到: {output_file_path}")
    
    except FileNotFoundError:
        logger.error(f"错误：找不到文件 {input_file_path}")
        logger.error("请确保在目录下有output.json文件")
    
    except json.JSONDecodeError as e:
        logger.error(f"错误：JSON格式无效 - {e}")
        logger.error("请检查output.json文件的格式是否正确")
    
    except Exception as e:
        logger.error(f"转换过程中发生错误: {e}")
    
    return True


if __name__ == "__main__":
    main()

