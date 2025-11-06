"""
通用工具函数模块
提供嵌套检查、节点查找等辅助功能
"""
from typing import Dict, Any, List


def is_statement_in_loop(statement: Dict[str, Any], loop_item: Dict[str, Any]) -> bool:
    """
    检查 statement 是否在 loop_item 的循环体中
    
    参数:
        statement: 要检查的语句
        loop_item: 循环项
        
    返回:
        bool: 如果在循环体中返回True，否则返回False
    """
    if not isinstance(loop_item, dict) or not isinstance(statement, dict):
        return False
    
    # 检查 loop_item 的 children 中是否包含 statement
    if "children" in loop_item:
        for child in loop_item.get("children", []):
            if isinstance(child, dict):
                # 检查是否是循环体块
                if child.get("type") in ["for_block", "while_block", "while_true_block"]:
                    if "children" in child:
                        # 递归检查 statement 是否在循环体的 children 中
                        if is_statement_in_block(statement, child["children"]):
                            return True
                # 递归检查其他子节点
                elif is_statement_in_loop(statement, child):
                    return True
    
    return False


def is_statement_in_block(statement: Dict[str, Any], block: List[Dict[str, Any]]) -> bool:
    """
    检查 statement 是否在 block 中（递归检查）
    
    参数:
        statement: 要检查的语句
        block: 代码块列表
        
    返回:
        bool: 如果在块中返回True，否则返回False
    """
    if not isinstance(block, list):
        return False
    
    for item in block:
        if item == statement:
            return True
        if isinstance(item, dict):
            # 检查 children 中是否包含 statement
            if "children" in item:
                for child in item.get("children", []):
                    if isinstance(child, dict):
                        if child.get("type") in ["if_block", "else_block"]:
                            if "children" in child:
                                if is_statement_in_block(statement, child["children"]):
                                    return True
                        elif is_statement_in_block(statement, [child]):
                            return True
    
    return False


def find_all_nested_if_else(statement: Dict[str, Any], result: List[Dict[str, Any]]) -> None:
    """
    递归查找所有嵌套的if-else结构
    
    参数:
        statement: 当前语句
        result: 结果列表，用于存储找到的所有if-else语句
    """
    if not statement or not isinstance(statement, dict):
        return
    
    # 如果当前语句是if-else结构，添加到结果中
    if statement.get("tag") in ["condition", "branch"]:
        if_block_info = statement.get("_if_block_info")
        else_block_info = statement.get("_else_block_info")
        if if_block_info or else_block_info:
            result.append(statement)
    
    # 递归查找children中的所有嵌套if-else
    if "children" in statement:
        for child in statement["children"]:
            if isinstance(child, dict):
                # 如果child是if_block或else_block，查找其children中的嵌套if-else
                if child.get("type") in ["if_block", "else_block"]:
                    if "children" in child:
                        for grandchild in child["children"]:
                            if isinstance(grandchild, dict):
                                find_all_nested_if_else(grandchild, result)
                else:
                    # 否则直接递归
                    find_all_nested_if_else(child, result)


def count_statement_chain(node: Dict[str, Any], depth: int = 0) -> int:
    """
    递归计算语句链长度
    
    参数:
        node: 当前节点
        depth: 当前深度
        
    返回:
        int: 语句链的长度
    """
    local_max = 0
    current_length = 1 if node.get('tag') != 'block' else 0
    
    if "children" in node and node["children"]:
        for child in node["children"]:
            if isinstance(child, dict):
                # 递归计算子节点的语句链长度
                child_max = count_statement_chain(child, depth + 1)
                # 累加当前节点的长度和子节点最长链
                local_max = max(local_max, current_length + child_max)
    else:
        local_max = current_length
    
    return local_max


def find_parent_block(stmt: Dict[str, Any], current_block: List[Dict[str, Any]], 
                     current_idx: int) -> tuple:
    """
    在代码块中查找语句的父块和索引
    
    参数:
        stmt: 要查找的语句
        current_block: 当前代码块
        current_idx: 当前索引
        
    返回:
        tuple: (parent_block, index) 或 (None, -1)
    """
    if not isinstance(stmt, dict) or not isinstance(current_block, list):
        return None, -1
    
    for idx, child in enumerate(current_block):
        if child == stmt:
            return current_block, idx
        
        if isinstance(child, dict) and "children" in child:
            # 检查children中的if_block和else_block
            for gc in child.get("children", []):
                if isinstance(gc, dict) and gc.get("type") in ["if_block", "else_block"]:
                    if "children" in gc:
                        found_block, found_idx = find_parent_block(stmt, gc["children"], -1)
                        if found_block:
                            return found_block, found_idx
    
    return None, -1

