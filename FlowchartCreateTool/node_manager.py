"""
节点创建与管理模块
负责流程图节点的创建、ID生成和管理
"""
from typing import Dict, Any, List


class NodeManager:
    """节点管理器：负责节点的创建、ID生成和存储"""
    
    def __init__(self):
        """初始化节点管理器"""
        self.nodes = []  # 存储所有节点
        self.node_counter = 0  # 节点计数器
        
        # 固定的节点ID模板
        self.ids = {
            "input": "bc58d5a1-d969-469f-9ee2-c8719b4ffd4b",
            "decision": "3991cbcd-8ad1-4d60-8a36-a224e101a382",
            "start": "e696f412-6290-4c08-86b0-2b4f2cf13745",
            "end": "f7a7g8h9-i0j1-k2l3-m4n5-o6p7q8r9s0t1",
            "process": "3658832b-0dcd-429a-b244-698063b79e2d"
        }
        
        self.start_node = None
        self.end_node = None
        self.last_node = None
    
    def get_unique_id(self, node_type: str) -> str:
        """
        生成唯一ID，基于固定ID加上计数器
        
        参数:
            node_type: 节点类型
            
        返回:
            str: 唯一的节点ID
        """
        base_id = self.ids.get(node_type, self.ids["process"])
        if self.node_counter == 0:
            self.node_counter += 1
            return base_id
        else:
            unique_id = f"{base_id}_{self.node_counter}"
            self.node_counter += 1
            return unique_id
    
    def create_node(self, node_type: str, text: str, x: float, y: float) -> Dict[str, Any]:
        """
        创建节点
        
        参数:
            node_type: 节点类型
            text: 节点文本
            x: x坐标
            y: y坐标
            
        返回:
            Dict: 创建的节点
        """
        node_id = self.get_unique_id(node_type)
        
        # 检查是否已经存在相同ID的节点
        existing_node = next((n for n in self.nodes if n["id"] == node_id), None)
        if existing_node:
            # 如果存在，更新其属性
            existing_node["text"] = text
            existing_node["x"] = x
            existing_node["y"] = y
            return existing_node
        
        node = {
            "id": node_id,
            "type": node_type,
            "x": x,
            "y": y,
            "width": 125,
            "height": 75,
            "text": text
        }
        self.nodes.append(node)
        return node
    
    def get_node_by_id(self, node_id: str) -> Dict[str, Any]:
        """
        根据ID查找节点
        
        参数:
            node_id: 节点ID
            
        返回:
            Dict: 找到的节点，如果未找到则返回None
        """
        return next((node for node in self.nodes if node["id"] == node_id), None)
    
    def reset(self):
        """重置节点管理器状态"""
        self.nodes = []
        self.node_counter = 0
        self.start_node = None
        self.end_node = None
        self.last_node = None
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        获取所有节点
        
        返回:
            List: 所有节点列表
        """
        return self.nodes
    
    def remove_duplicate_end_nodes(self):
        """移除重复的结束节点（保留最后创建的那个）"""
        if self.end_node:
            # 先找到所有结束节点
            end_nodes = [node for node in self.nodes 
                        if node["type"] == "start" and node["text"] == "结束" 
                        and node != self.end_node]
            # 从nodes列表中移除这些节点
            self.nodes = [node for node in self.nodes if node not in end_nodes]
            return [node["id"] for node in end_nodes]  # 返回被移除节点的ID列表
        return []

