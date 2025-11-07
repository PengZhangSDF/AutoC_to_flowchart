"""
if-else及嵌套结构处理模块
负责处理if-else条件分支及其嵌套结构的回连逻辑
"""
from typing import Dict, Any, List, Tuple
from logger.logger import logger
from ..utils import find_all_nested_if_else, find_parent_block


class IfElseProcessor:
    """if-else结构处理器：负责处理if-else分支及嵌套结构"""
    
    def _find_node_by_statement(self, statement: Dict[str, Any], 
                                 exclude_node: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        根据语句查找对应的节点
        
        参数:
            statement: 要查找的语句
            exclude_node: 要排除的节点
            
        返回:
            Dict: 找到的节点，如果未找到则返回None
        """
        if not statement:
            return None
        
        stmt_text = statement.get("translated", "")
        if not stmt_text:
            return None
        
        # 遍历所有节点查找匹配的文本
        for node in self.node_manager.get_all_nodes():
            # 排除指定的节点
            if exclude_node and node.get("id") == exclude_node.get("id"):
                continue
            
            # 匹配文本
            if node.get("text") == stmt_text:
                return node
        
        return None
    
    def __init__(self, node_manager, connection_manager, context_manager):
        """
        初始化if-else处理器
        
        参数:
            node_manager: 节点管理器
            connection_manager: 连接管理器
            context_manager: 上下文管理器
        """
        self.node_manager = node_manager
        self.connection_manager = connection_manager
        self.context_manager = context_manager
        # **添加**：跟踪已处理的if-else，避免重复处理
        self.processed_if_else = set()
    
    def handle_if_else_reconnect(self, if_last_node: Dict[str, Any], 
                                 else_last_node: Dict[str, Any],
                                 if_has_return: bool, else_has_return: bool,
                                 condition_node: Dict[str, Any],
                                 parent_block: List[Dict[str, Any]], 
                                 if_statement_index: int,
                                 next_statement_first_node: Dict[str, Any] = None,
                                 loop_condition_node: Dict[str, Any] = None,
                                 context_stack: List = None,
                                 current_context_type: str = None) -> None:
        """
        处理 if-else 模块的回连逻辑（包括嵌套的if-else）
        
        按照用户要求：
        1. 如果最后一个语句是return，则不进行任何回连
        2. 检查本层级的if-else模块之后是否还有语句，若有，由最后的语句的down连接到其up
        3. 若没有，判断当前if-else所处children类型：
           - 若为循环，则由if和else的right点连到本层循环的判断块的up
           - 若为if或else块，则继续回溯上层if-else块之后有没有语句
        4. 直到检索不到所处块（即到了主顺序位置），确认主顺序位置在第一个分支后没有后续块了，则不连接
        
        参数:
            if_last_node: if块的最后一个节点
            else_last_node: else块的最后一个节点
            if_has_return: if块是否有return
            else_has_return: else块是否有return
            condition_node: 条件判断节点
            parent_block: 父代码块
            if_statement_index: if语句在父块中的索引
            next_statement_first_node: 后续语句的第一个节点
            loop_condition_node: 循环条件节点（如果在循环内）
            context_stack: 上下文栈
            current_context_type: 当前上下文类型
        """
        
        # **防重复处理**：检查这个if-else是否已经处理过
        # 使用节点ID作为key就足够了，不需要parent_block和index
        if_id = if_last_node.get('id') if if_last_node else 'None'
        else_id = else_last_node.get('id') if else_last_node else 'None'
        reconnect_key = (if_id, else_id)
        
        if reconnect_key in self.processed_if_else:
            logger.debug(f"[跳过] 该if-else已处理过: if={if_id}, else={else_id}")
            return
        
        self.processed_if_else.add(reconnect_key)
        
        # 1. 处理 if 块的回连（如果最后一个语句不是return）
        if not if_has_return and if_last_node:
            # **调试**：记录处理的节点
            if_suffix = if_last_node.get('id', '').split('_')[-1] if '_' in if_last_node.get('id', '') else '?'
            
            target_node, start_point, end_point = self._find_reconnect_target(
                parent_block, if_statement_index, next_statement_first_node,
                loop_condition_node, condition_node, context_stack, else_last_node,
                current_context_type=current_context_type
            )
            
            if target_node:
                target_suffix = target_node.get('id', '').split('_')[-1] if '_' in target_node.get('id', '') else '?'
                logger.debug(f"[if回连] _{if_suffix} -> _{target_suffix} ({start_point}), context={current_context_type}")
            
            if target_node:
                # **验证**：如果目标节点在起始节点上方（y < start_y）但连接类型是down，则跳过
                if_y = if_last_node.get('y', 0)
                target_y = target_node.get('y', 0)
                if start_point == 'down' and target_y < if_y:
                    logger.debug(f"[警告] 跳过错误的down连接（目标在上方）: {if_last_node['id']}  -> {target_node['id']}, if_y={if_y}, target_y={target_y}")
                else:
                    # 检查是否已存在该连接
                    existing = any(
                        conn["start_item_id"] == if_last_node["id"] and
                        conn["start_point_type"] == start_point and
                        conn["end_item_id"] == target_node["id"] and
                        conn["end_point_type"] == end_point
                        for conn in self.connection_manager.connections
                    )
                    if not existing:
                        self.connection_manager.add_connection(
                            if_last_node["id"], start_point, target_node["id"], end_point
                        )
                        logger.debug(f"添加 if 块回连: {if_last_node['id']} ({start_point}) -> {target_node['id']} ({end_point})")
            else:
                # **调试**：记录未找到目标的情况
                logger.debug(f"[警告] if块未找到回连目标: {if_last_node['id']}, context={current_context_type}, loop_node={'有' if loop_condition_node else '无'}")
        
        # 2. 处理 else 块的回连（如果最后一个语句不是return）
        if else_last_node and not else_has_return:
            target_node, start_point, end_point = self._find_reconnect_target(
                parent_block, if_statement_index, next_statement_first_node,
                loop_condition_node, condition_node, context_stack, else_last_node,
                current_context_type=current_context_type
            )
            
            if target_node:
                # **验证**：如果目标节点在起始节点上方（y < start_y）但连接类型是down，则跳过
                else_y = else_last_node.get('y', 0)
                target_y = target_node.get('y', 0)
                if start_point == 'down' and target_y < else_y:
                    logger.debug(f"[警告] 跳过错误的down连接（目标在上方）: {else_last_node['id']} -> {target_node['id']}, else_y={else_y}, target_y={target_y}")
                else:
                    # 检查是否已存在该连接
                    existing = any(
                        conn["start_item_id"] == else_last_node["id"] and
                        conn["start_point_type"] == start_point and
                        conn["end_item_id"] == target_node["id"] and
                        conn["end_point_type"] == end_point
                        for conn in self.connection_manager.connections
                    )
                    if not existing:
                        self.connection_manager.add_connection(
                            else_last_node["id"], start_point, target_node["id"], end_point
                        )
                        logger.debug(f"添加 else 块回连: {else_last_node['id']} ({start_point}) -> {target_node['id']} ({end_point})")
    
    def _find_reconnect_target(self, parent_block: List[Dict[str, Any]], 
                               if_statement_index: int,
                               next_statement_first_node: Dict[str, Any] = None,
                               loop_condition_node: Dict[str, Any] = None,
                               condition_node: Dict[str, Any] = None,
                               context_stack: List = None,
                               else_last_node: Dict[str, Any] = None,
                               current_context_type: str = None) -> Tuple[Dict[str, Any], str, str]:
        """
        内部方法：查找回连目标节点
        
        返回: (target_node, start_point_type, end_point_type) 或 (None, None, None) 表示不连接
        
        参数:
            else_last_node: else块的最后一个节点，用于验证目标节点不是else块的最后一个节点
            current_context_type: 当前if-else所在的上下文类型 ('loop', 'if_block', 'else_block', 'main')
        """
        logger.debug(f"\n[查找回连目标] if_statement_index={if_statement_index}, context_type={current_context_type}")
        logger.debug(f"  next_statement_first_node: {next_statement_first_node.get('id') if next_statement_first_node else 'None'}")
        logger.debug(f"  loop_condition_node: {loop_condition_node.get('id') if loop_condition_node else 'None'}")
        
        # 1. 首先检查本层级的 if-else 模块之后是否还有语句
        if parent_block is not None and if_statement_index >= 0:
            # 跳过整个if-else结构（包括所有else块）来查找后续语句
            skip_count = 1
            current_idx = if_statement_index + 1
            while current_idx < len(parent_block):
                next_stmt = parent_block[current_idx]
                if isinstance(next_stmt, dict):
                    if next_stmt.get("tag") == "branch" and "否则" in next_stmt.get("translated", ""):
                        skip_count += 1
                        current_idx += 1
                    else:
                        break
                else:
                    break
            
            # 查找真正的后续语句
            for i in range(if_statement_index + skip_count, len(parent_block)):
                next_stmt = parent_block[i]
                if isinstance(next_stmt, dict) and next_stmt.get("tag") != "block":
                    # 找到了后续语句
                    target_node = None
                    
                    # 优先使用提供的节点
                    if next_statement_first_node:
                        # 验证：确保这个节点不是else块的最后一个节点
                        if else_last_node and next_statement_first_node.get("id") == else_last_node.get("id"):
                            # 这是else块的最后一个节点，不应该作为目标节点，继续查找
                            continue
                        target_node = next_statement_first_node
                    else:
                        # 如果没有提供节点，尝试查找
                        if parent_block == self.context_manager.input_json:
                            # 主流程：从statement_first_nodes查找
                            candidate_node = self.context_manager.get_statement_first_node(i)
                            if candidate_node:
                                # 再次验证：确保不是else块的最后一个节点
                                if else_last_node:
                                    if candidate_node.get("id") == else_last_node.get("id"):
                                        continue
                                target_node = candidate_node
                        else:
                            # **关键修复**：不在主流程中（如循环体内），根据语句文本查找节点
                            target_node = self._find_node_by_statement(next_stmt, else_last_node)
                    
                    if target_node:
                        # 本层级有后续语句，使用down→up连接
                        return target_node, "down", "up"
        
        # 2. **改进**：不立即根据context_type='loop'返回循环节点
        # 而是继续检查是否有其他可能的后续语句
        
        # 尝试通过parent_block向上查找（模拟context_stack的功能）
        # 注意：这是一个简化的回溯，不如完整的context_stack准确，但能处理大部分情况
        
        # 如果在循环内但有next_statement_first_node，说明外层有后续语句，应该优先连接到它
        if current_context_type == 'loop' and next_statement_first_node:
            # 验证next_statement_first_node不是循环条件节点
            if loop_condition_node and next_statement_first_node.get('id') != loop_condition_node.get('id'):
                logger.debug(f"    [优先] 虽在循环内，但有外层后续语句，使用down")
                return next_statement_first_node, "down", "up"
        
        # **推迟循环回连的判断**：先检查context_stack和其他可能性
        # 记录是否在循环内，稍后再决定是否回连
        should_check_loop_later = (current_context_type == 'loop' and loop_condition_node is not None)
        
        # 3. 回溯检查上层结构（通过上下文栈）
        if context_stack:
            for ctx_idx in range(len(context_stack) - 1, -1, -1):
                # 支持新旧格式的上下文栈
                if len(context_stack[ctx_idx]) >= 5:
                    ctx_statement, ctx_parent_block, ctx_block_index, ctx_context_type, ctx_next_node = context_stack[ctx_idx]
                else:
                    ctx_statement, ctx_parent_block, ctx_block_index = context_stack[ctx_idx][:3]
                    ctx_next_node = context_stack[ctx_idx][3] if len(context_stack[ctx_idx]) > 3 else None
                    ctx_context_type = None
                
                # 检查当前上下文语句的类型
                ctx_tag = ctx_statement.get("tag", "") if ctx_statement else ""
                ctx_original = ctx_statement.get("original_unit", "").lower() if ctx_statement else ""
                ctx_type = ctx_statement.get("type", "") if ctx_statement else ""
                
                # 如果是循环
                if ctx_context_type == 'loop' or (ctx_statement and (
                    "for" in ctx_original or "while" in ctx_original or 
                    ctx_tag in ["loop"] or 
                    ctx_type in ["for_block", "while_block", "while_true_block"])):
                    # **改进**：不立即返回循环节点，先检查该循环中是否有后续语句
                    # 查找循环的children（while_true_block, for_true_block等）
                    loop_children = None
                    if ctx_statement and 'children' in ctx_statement:
                        for loop_child in ctx_statement['children']:
                            if isinstance(loop_child, dict) and loop_child.get('type') in [
                                'while_true_block', 'for_true_block', 'for_block', 'while_block'
                            ]:
                                loop_children = loop_child.get('children', [])
                                break
                    
                    # 如果找到了loop_children，检查当前if-else在其中的位置
                    # 以及之后是否有语句
                    if loop_children:
                        # 尝试在loop_children中找到包含当前if-else的位置
                        # 注意：当前if-else可能嵌套在更深的结构中
                        # 简化处理：检查loop_children中是否有除了当前if-else之外的语句
                        # 如果有，说明不应该立即回连到循环
                        # 这部分逻辑比较复杂，暂时跳过，继续向上查找
                        pass
                    
                    # 记住这是一个循环，但先不返回，继续查找
                    # 如果最后没有找到任何后续语句，再返回循环节点
                    # 这里不返回，让代码继续到最后的检查
                    continue
                
                # 如果是 if 或者 else 块
                elif ctx_context_type in ['if_block', 'else_block'] or (ctx_statement and (
                      ctx_tag in ["condition", "branch"] or 
                      ctx_type in ["if_block", "else_block"])):
                    # 检查该children同级之后还有没有语句
                    if ctx_parent_block is not None and ctx_block_index >= 0:
                        # 跳过整个if-else结构（包括所有else块）
                        skip_count = 1
                        current_idx = ctx_block_index + 1
                        while current_idx < len(ctx_parent_block):
                            next_stmt = ctx_parent_block[current_idx]
                            if isinstance(next_stmt, dict):
                                if next_stmt.get("tag") == "branch" and "否则" in next_stmt.get("translated", ""):
                                    skip_count += 1
                                    current_idx += 1
                                else:
                                    break
                            else:
                                break
                        
                        # 查找后续语句
                        for next_idx in range(ctx_block_index + skip_count, len(ctx_parent_block)):
                            next_stmt = ctx_parent_block[next_idx]
                            if isinstance(next_stmt, dict) and next_stmt.get("tag") != "block":
                                # 找到了后续语句
                                target_node = None
                                
                                # 优先使用提供的节点
                                if ctx_next_node:
                                    # 验证：确保不是else块的最后一个节点
                                    if else_last_node and ctx_next_node.get("id") == else_last_node.get("id"):
                                        continue
                                    target_node = ctx_next_node
                                elif next_statement_first_node:
                                    # 验证：确保不是else块的最后一个节点
                                    if else_last_node and next_statement_first_node.get("id") == else_last_node.get("id"):
                                        continue
                                    target_node = next_statement_first_node
                                else:
                                    # 尝试从statement_first_nodes查找
                                    if ctx_parent_block == self.context_manager.input_json:
                                        candidate_node = self.context_manager.get_statement_first_node(next_idx)
                                        if candidate_node:
                                            # 验证：确保不是else块的最后一个节点
                                            if else_last_node:
                                                if candidate_node.get("id") == else_last_node.get("id"):
                                                    continue
                                            target_node = candidate_node
                                
                                if target_node:
                                    return target_node, "down", "up"
                        
                        # 如果没有找到同级后续语句，继续向上回溯
                        continue
                
                # 如果到达主顺序位置（ctx_statement为None或不在任何children中）
                if ctx_statement is None or ctx_context_type == 'main':
                    # 在主顺序位置，检查第一个分支后是否有后续块
                    if ctx_parent_block is not None and ctx_block_index >= 0:
                        # 跳过整个if-else结构
                        skip_count = 1
                        current_idx = ctx_block_index + 1
                        while current_idx < len(ctx_parent_block):
                            next_stmt = ctx_parent_block[current_idx]
                            if isinstance(next_stmt, dict):
                                if next_stmt.get("tag") == "branch" and "否则" in next_stmt.get("translated", ""):
                                    skip_count += 1
                                    current_idx += 1
                                else:
                                    break
                            else:
                                break
                        
                        # 查找后续语句
                        for next_idx in range(ctx_block_index + skip_count, len(ctx_parent_block)):
                            next_stmt = ctx_parent_block[next_idx]
                            if isinstance(next_stmt, dict) and next_stmt.get("tag") != "block":
                                # 找到了后续语句
                                target_node = None
                                
                                # 优先使用提供的节点
                                if ctx_next_node:
                                    target_node = ctx_next_node
                                elif next_statement_first_node:
                                    # 验证：确保不是else块的最后一个节点
                                    if else_last_node and next_statement_first_node.get("id") == else_last_node.get("id"):
                                        continue
                                    target_node = next_statement_first_node
                                else:
                                    # 尝试从statement_first_nodes查找
                                    if ctx_parent_block == self.context_manager.input_json:
                                        candidate_node = self.context_manager.get_statement_first_node(next_idx)
                                        if candidate_node:
                                            target_node = candidate_node
                                
                                if target_node:
                                    return target_node, "down", "up"
                        
                        # 如果没有找到后续语句，说明主顺序位置第一个分支后没有后续块，不连接
                        return None, None, None
        
        # 4. **关键修复**：如果在parent_block中找不到后续语句
        # 且context_type='main'（不在循环中），尝试向上查找
        # 这处理了嵌套if-else（在if/else块内）找不到外层后续语句的情况
        if current_context_type == 'main' and not loop_condition_node:
            logger.debug(f"    [回溯] context=main且无loop，尝试向上查找后续语句")
            # 尝试通过遍历所有节点找到可能的后续语句
            # 这是一个启发式方法：找到y坐标稍大于else_last_node或condition_node的节点
            # 优先选择：决策节点（decision）或主流程中的节点（x坐标接近base_x）
            if condition_node:
                base_x = -4600.0  # 主流程的x坐标
                cond_x = condition_node.get('x', base_x)
                cond_y = condition_node.get('y', 0)
                
                # 使用else_last_node的y坐标更准确
                if else_last_node:
                    target_y = else_last_node.get('y', cond_y)
                else:
                    target_y = cond_y
                
                closest_node = None
                min_distance = float('inf')
                
                # **改进的启发式查找**：识别中转节点，跳过它们
                # 中转节点：有向下出站连接的节点
                intermediate_nodes = set()
                for n in self.node_manager.get_all_nodes():
                    for conn in self.connection_manager.connections:
                        if conn['start_item_id'] == n.get('id') and conn['start_point_type'] == 'down':
                            target_node = self.node_manager.get_node_by_id(conn['end_item_id'])
                            if target_node and target_node.get('y') >= n.get('y'):
                                intermediate_nodes.add(n.get('id'))
                                break
                
                for node in self.node_manager.get_all_nodes():
                    node_y = node.get('y', 0)
                    node_x = node.get('x', 0)
                    
                    # 查找在目标y之下的节点
                    if node_y > target_y:
                        # 排除else_last_node、结束节点和中转节点
                        if (else_last_node and node.get('id') == else_last_node.get('id')) or \
                           node.get('text') == '结束':
                            continue
                        
                        distance = node_y - target_y
                        
                        # **跳过近距离的中转节点**
                        if node.get('id') in intermediate_nodes and distance < 200:
                            continue
                        
                        # **改进算法**：优先选择主流程且y距离在合理范围内的decision节点
                        is_main_flow = abs(node_x - base_x) < 50
                        is_decision = node.get('type') == 'decision'
                        
                        # 计算优先级分数（越小越优先）
                        score = distance
                        if is_main_flow:
                            score = score * 0.5  # 主流程节点优先
                        if is_decision and 150 < distance < 250:
                            score = score * 0.3  # 距离合理的decision节点最优先
                        
                        if score < min_distance:
                            min_distance = score
                            closest_node = node
                
                if closest_node:
                    logger.debug(f"    [回溯] 找到可能的后续节点: {closest_node.get('id')}")
                    return closest_node, "down", "up"
        
        # 5. 如果回溯到顶层还没有找到，说明在主顺序位置
        # 检查主顺序位置第一个分支后是否有后续块
        if parent_block == self.context_manager.input_json and if_statement_index >= 0:
            skip_count = 1
            current_idx = if_statement_index + 1
            while current_idx < len(parent_block):
                next_stmt = parent_block[current_idx]
                if isinstance(next_stmt, dict):
                    if next_stmt.get("tag") == "branch" and "否则" in next_stmt.get("translated", ""):
                        skip_count += 1
                        current_idx += 1
                    else:
                        break
                else:
                    break
            
            for i in range(if_statement_index + skip_count, len(parent_block)):
                next_stmt = parent_block[i]
                if isinstance(next_stmt, dict) and next_stmt.get("tag") != "block":
                    candidate_node = self.context_manager.get_statement_first_node(i)
                    if candidate_node:
                        if else_last_node and candidate_node.get("id") == else_last_node.get("id"):
                            continue
                        return candidate_node, "down", "up"
        
        # 6. **最后的选择**：如果确实在循环内且没有找到任何后续语句，回连到循环
        if should_check_loop_later and loop_condition_node:
            logger.debug(f"    [最后选择] 没有找到后续语句，回连到循环: {loop_condition_node.get('id')}")
            return loop_condition_node, "right", "up"
        
        # 7. 如果主顺序位置第一个分支后没有后续块，不连接
        # **注意**：返回None会让orphan_nodes处理来查找目标
        logger.debug(f"    [未找到] 没有找到回连目标")
        return None, None, None
    
    def handle_nested_if_else_reconnect(self, statement: Dict[str, Any],
                                       parent_block: List[Dict[str, Any]], 
                                       if_statement_index: int,
                                       next_statement_first_node: Dict[str, Any] = None,
                                       loop_condition_node: Dict[str, Any] = None,
                                       context_stack: List = None,
                                       parent_condition_node: Dict[str, Any] = None) -> None:
        """
        递归处理嵌套的 if-else 模块的回连逻辑
        
        参数:
            statement: 当前处理的if-else语句
            parent_block: 包含该 if-else 的父块
            if_statement_index: if 语句在 parent_block 中的索引
            next_statement_first_node: 后续语句的第一个节点（如果有）
            loop_condition_node: 如果该 if-else 在循环内，这是循环条件节点
            context_stack: 上下文栈，用于回溯
            parent_condition_node: 父级if-else的条件节点（用于嵌套回连）
        """
        if not statement or statement.get("tag") not in ["condition", "branch"]:
            return
        
        # 获取当前if-else的信息
        if_block_info = statement.get("_if_block_info")
        else_block_info = statement.get("_else_block_info")
        
        # 获取嵌套if-else的条件节点
        nested_condition_node = self._find_nested_condition_node(statement, if_block_info, parent_condition_node)
        
        # 查找嵌套if-else的后续语句节点
        nested_next_node = self._find_nested_next_node(statement, parent_block, next_statement_first_node, 
                                                       loop_condition_node, else_block_info)
        
        # 处理当前if-else的回连
        if if_block_info or else_block_info:
            # 获取嵌套if-else的上下文类型
            nested_context_type = self._determine_nested_context_type(statement, loop_condition_node, parent_condition_node)
            
            self.handle_if_else_reconnect(
                if_block_info["last_node"] if if_block_info else None,
                else_block_info["last_node"] if else_block_info else None,
                if_block_info["has_return"] if if_block_info else False,
                else_block_info["has_return"] if else_block_info else False,
                nested_condition_node,
                parent_block,
                if_statement_index,
                nested_next_node,
                loop_condition_node,
                context_stack,
                current_context_type=nested_context_type
            )
        
        # 递归处理嵌套的if-else
        self._process_deeply_nested_if_else(statement, parent_block, nested_next_node, 
                                            loop_condition_node, context_stack, nested_condition_node)
    
    def _find_nested_condition_node(self, statement: Dict[str, Any], 
                                   if_block_info: Dict[str, Any],
                                   parent_condition_node: Dict[str, Any]) -> Dict[str, Any]:
        """查找嵌套if-else的条件节点"""
        nested_condition_node = None
        if if_block_info and if_block_info.get("last_node"):
            # 从if_block的最后一个节点向上查找，找到条件节点
            if_last_node = if_block_info["last_node"]
            # 查找指向if_last_node的连接，其start节点应该是条件节点
            for conn in self.connection_manager.connections:
                if conn["end_item_id"] == if_last_node["id"] and conn["end_point_type"] == "up":
                    start_node_id = conn["start_item_id"]
                    nested_condition_node = self.node_manager.get_node_by_id(start_node_id)
                    if nested_condition_node and nested_condition_node.get("type") == "decision":
                        break
        
        # 如果没有找到，使用parent_condition_node（可能是错误的，但作为备用）
        if not nested_condition_node:
            nested_condition_node = parent_condition_node
        
        return nested_condition_node
    
    def _find_nested_next_node(self, statement: Dict[str, Any], parent_block: List[Dict[str, Any]],
                              next_statement_first_node: Dict[str, Any],
                              loop_condition_node: Dict[str, Any],
                              else_block_info: Dict[str, Any]) -> Dict[str, Any]:
        """查找嵌套if-else的后续语句节点"""
        nested_next_node = None
        if parent_block and isinstance(parent_block, list):
            found_statement = False
            for idx, stmt in enumerate(parent_block):
                if stmt == statement:
                    found_statement = True
                    # 跳过整个if-else结构（包括所有else块）
                    skip_count = 1
                    current_idx = idx + 1
                    while current_idx < len(parent_block):
                        next_stmt = parent_block[current_idx]
                        if isinstance(next_stmt, dict):
                            if next_stmt.get("tag") == "branch" and "否则" in next_stmt.get("translated", ""):
                                skip_count += 1
                                current_idx += 1
                            else:
                                break
                        else:
                            break
                    
                    # 查找真正的后续语句（跳过整个if-else结构）
                    current_else_last_node = None
                    if else_block_info:
                        current_else_last_node = else_block_info.get("last_node")
                    
                    for next_idx in range(idx + skip_count, len(parent_block)):
                        next_stmt = parent_block[next_idx]
                        if isinstance(next_stmt, dict) and next_stmt.get("tag") != "block":
                            if current_else_last_node and next_statement_first_node:
                                # 如果next_statement_first_node是else块的最后一个节点，不应该使用
                                if next_statement_first_node.get("id") == current_else_last_node.get("id"):
                                    # 这是else块的最后一个节点，使用循环条件节点或其他目标
                                    nested_next_node = loop_condition_node
                                else:
                                    nested_next_node = next_statement_first_node
                            else:
                                nested_next_node = next_statement_first_node or loop_condition_node
                            break
                    break
        
        # 如果没有找到后续语句，使用外层提供的next_statement_first_node或loop_condition_node
        if not nested_next_node:
            nested_next_node = next_statement_first_node or loop_condition_node
        
        return nested_next_node
    
    def _determine_nested_context_type(self, statement: Dict[str, Any],
                                      loop_condition_node: Dict[str, Any],
                                      parent_condition_node: Dict[str, Any]) -> str:
        """确定嵌套if-else的上下文类型"""
        nested_context_type = statement.get("_context_type")
        if not nested_context_type:
            # 如果提供了 loop_condition_node，说明在循环内
            if loop_condition_node:
                nested_context_type = 'loop'
            # 尝试从父级推断
            elif parent_condition_node:
                nested_context_type = 'loop'
            else:
                nested_context_type = 'main'
        return nested_context_type
    
    def _process_deeply_nested_if_else(self, statement: Dict[str, Any], parent_block: List[Dict[str, Any]],
                                      nested_next_node: Dict[str, Any], loop_condition_node: Dict[str, Any],
                                      context_stack: List, nested_condition_node: Dict[str, Any]):
        """处理更深层的嵌套if-else"""
        # 使用find_all_nested_if_else递归查找所有嵌套的if-else结构
        nested_if_else_list = []
        find_all_nested_if_else(statement, nested_if_else_list)
        
        # 处理找到的所有嵌套if-else
        for nested_stmt in nested_if_else_list:
            # 跳过当前语句本身（已在上面处理）
            if nested_stmt == statement:
                continue
            
            self._process_single_nested_if_else(nested_stmt, parent_block, nested_next_node,
                                               loop_condition_node, context_stack, nested_condition_node)
    
    def _process_single_nested_if_else(self, nested_stmt: Dict[str, Any], parent_block: List[Dict[str, Any]],
                                      nested_next_node: Dict[str, Any], loop_condition_node: Dict[str, Any],
                                      context_stack: List, nested_condition_node: Dict[str, Any]):
        """处理单个嵌套的if-else"""
        # 获取嵌套if-else的信息
        nested_if_info = nested_stmt.get("_if_block_info")
        nested_else_info = nested_stmt.get("_else_block_info")
        
        if not nested_if_info and not nested_else_info:
            return
        
        # 查找嵌套if-else的条件节点
        nested_cond_node = self._find_nested_condition_node(nested_stmt, nested_if_info, nested_condition_node)
        
        # 查找嵌套if-else的父块和索引
        nested_parent_block, nested_statement_index = self._find_nested_parent_block(nested_stmt, parent_block)
        
        # 查找嵌套if-else的后续节点
        nested_stmt_next_node = self._find_nested_stmt_next_node(nested_stmt, nested_parent_block,
                                                                 nested_statement_index, nested_next_node)
        
        # 获取嵌套if-else的上下文类型
        nested_ctx_type = self._determine_nested_context_type(nested_stmt, loop_condition_node, nested_condition_node)
        
        # 处理这个嵌套if-else的回连
        self.handle_if_else_reconnect(
            nested_if_info["last_node"] if nested_if_info else None,
            nested_else_info["last_node"] if nested_else_info else None,
            nested_if_info["has_return"] if nested_if_info else False,
            nested_else_info["has_return"] if nested_else_info else False,
            nested_cond_node,
            nested_parent_block or parent_block,
            nested_statement_index,
            nested_stmt_next_node,
            loop_condition_node,
            context_stack,
            current_context_type=nested_ctx_type
        )
        
        # 对于循环内的嵌套if-else，确保强制回连到循环条件节点
        self._ensure_loop_reconnect(nested_ctx_type, loop_condition_node, nested_if_info, nested_else_info)
        
        # 递归处理这个嵌套if-else内部的更深层嵌套
        self.handle_nested_if_else_reconnect(
            nested_stmt,
            nested_parent_block or parent_block,
            nested_statement_index,
            nested_stmt_next_node,
            loop_condition_node,
            context_stack,
            parent_condition_node=nested_cond_node
        )
    
    def _find_nested_parent_block(self, nested_stmt: Dict[str, Any], 
                                 statement: Dict[str, Any]) -> Tuple[List, int]:
        """查找嵌套if-else的父块和索引"""
        nested_parent_block = None
        nested_statement_index = -1
        
        # 从statement的children中查找
        if "children" in statement:
            for child in statement["children"]:
                if isinstance(child, dict):
                    if child.get("type") == "if_block" and "children" in child:
                        found_block, found_idx = find_parent_block(nested_stmt, child["children"], -1)
                        if found_block:
                            nested_parent_block = found_block
                            nested_statement_index = found_idx
                            break
                    elif child.get("type") == "else_block" and "children" in child:
                        found_block, found_idx = find_parent_block(nested_stmt, child["children"], -1)
                        if found_block:
                            nested_parent_block = found_block
                            nested_statement_index = found_idx
                            break
        
        # 如果没有找到，使用statement的children作为parent_block
        if not nested_parent_block and "children" in statement:
            for child in statement["children"]:
                if isinstance(child, dict) and child.get("type") in ["if_block", "else_block"]:
                    if "children" in child:
                        for idx, gc in enumerate(child["children"]):
                            if gc == nested_stmt:
                                nested_parent_block = child["children"]
                                nested_statement_index = idx
                                break
                        if nested_parent_block:
                            break
        
        return nested_parent_block, nested_statement_index
    
    def _find_nested_stmt_next_node(self, nested_stmt: Dict[str, Any], 
                                   nested_parent_block: List[Dict[str, Any]],
                                   nested_statement_index: int,
                                   nested_next_node: Dict[str, Any]) -> Dict[str, Any]:
        """查找嵌套if-else的后续节点"""
        nested_stmt_next_node = nested_next_node
        
        # 如果找到了父块，尝试查找该嵌套if-else之后的语句
        if nested_parent_block and nested_statement_index >= 0:
            # 跳过整个嵌套if-else结构
            skip_count = 1
            current_idx = nested_statement_index + 1
            while current_idx < len(nested_parent_block):
                next_stmt = nested_parent_block[current_idx]
                if isinstance(next_stmt, dict):
                    if next_stmt.get("tag") == "branch" and "否则" in next_stmt.get("translated", ""):
                        skip_count += 1
                        current_idx += 1
                    else:
                        break
                else:
                    break
            
            # 查找后续语句
            for next_idx in range(nested_statement_index + skip_count, len(nested_parent_block)):
                next_stmt = nested_parent_block[next_idx]
                if isinstance(next_stmt, dict) and next_stmt.get("tag") != "block":
                    # 找到了后续语句，但无法获取节点，使用外层的next_node
                    nested_stmt_next_node = nested_next_node
                    break
        
        return nested_stmt_next_node
    
    def _ensure_loop_reconnect(self, nested_ctx_type: str, loop_condition_node: Dict[str, Any],
                              nested_if_info: Dict[str, Any], nested_else_info: Dict[str, Any]):
        """确保循环内的嵌套if-else强制回连到循环条件节点
        
        **重要**：此方法暂时禁用，因为handle_if_else_reconnect已经处理了所有回连
        强制添加会导致重复或错误的连接
        """
        # **临时禁用**：handle_if_else_reconnect应该已经处理了所有情况
        # 强制添加可能导致不必要的连接
        return
        
        # if nested_ctx_type == 'loop' and loop_condition_node:
        #     # 处理if块
        #     if nested_if_info and nested_if_info["last_node"]:
        #         # **关键修复**：检查if块是否已经有任何出站连接
        #         existing_connections = self.connection_manager.get_connections_from_node(
        #             nested_if_info["last_node"]["id"]
        #         )
        #         # 如果已经有出站连接（如down到后续语句），就不强制添加right到循环
        #         if not existing_connections:
        #             if not self.connection_manager.connection_exists(
        #                 nested_if_info["last_node"]["id"],
        #                 loop_condition_node["id"]
        #             ):
        #                 self.connection_manager.add_connection(
        #                     nested_if_info["last_node"]["id"],
        #                     "right",
        #                     loop_condition_node["id"],
        #                     "up",
        #                     label=""
        #                 )
        #
        #     # 处理else块
        #     if nested_else_info and nested_else_info["last_node"]:
        #         # **关键修复**：检查else块是否已经有任何出站连接
        #         existing_connections = self.connection_manager.get_connections_from_node(
        #             nested_else_info["last_node"]["id"]
        #         )
        #         # 如果已经有出站连接，就不强制添加right到循环
        #         if not existing_connections:
        #             if not self.connection_manager.connection_exists(
        #                 nested_else_info["last_node"]["id"],
        #                 loop_condition_node["id"]
        #             ):
        #                 self.connection_manager.add_connection(
        #                     nested_else_info["last_node"]["id"],
        #                     "right",
        #                     loop_condition_node["id"],
        #                     "up",
        #                     label=""
        #                 )

