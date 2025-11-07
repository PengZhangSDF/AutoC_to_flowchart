"""
连接线创建与管理模块
负责流程图节点之间连接线的创建和管理
"""
from typing import Dict, Any, List


class ConnectionManager:
    """连接管理器：负责节点间连接线的创建和存储"""
    
    def __init__(self, node_manager):
        """
        初始化连接管理器
        
        参数:
            node_manager: 节点管理器实例，用于查找节点信息
        """
        self.connections = []  # 存储所有连接
        self.node_manager = node_manager
    
    def add_connection(self, start_node_id: str, start_point_type: str,
                      end_node_id: str, end_point_type: str, label: str = None):
        """
        添加连接
        
        参数:
            start_node_id: 起始节点ID
            start_point_type: 起始连接点类型（up/down/left/right）
            end_node_id: 结束节点ID
            end_point_type: 结束连接点类型（up/down/left/right）
            label: 连接线标签（可选）
        """
        # **安全检查1**：不能连接到自己
        if start_node_id == end_node_id:
            from logger.logger import logger
            logger.warning(f"[严重错误] 试图创建自连接: {start_node_id} -> {end_node_id}")
            return  # 阻止连接到自己
        
        # 检查开始节点是否是结束节点（type为"start"且text为"结束"）
        start_node = self.node_manager.get_node_by_id(start_node_id)
        if start_node and start_node["type"] == "start" and start_node["text"] == "结束":
            return  # 结束节点不应该有任何指出的连接
        
        # 检查连接是否已存在
        for conn in self.connections:
            if (conn["start_item_id"] == start_node_id and
                    conn["start_point_type"] == start_point_type and
                    conn["end_item_id"] == end_node_id and
                    conn["end_point_type"] == end_point_type):
                return
        
        # 确定连接线的标签（如果未提供）
        if label is None:
            # 检查开始节点是否是判断节点（decision类型）
            if start_node and start_node["type"] == "decision":
                # 对于判断节点，从down发出的线标签为"否"
                if start_point_type == "down":
                    label = "否"
                # 从right或left发出的线标签为"是"
                elif start_point_type in ["right", "left"]:
                    label = "是"
        
        connection = {
            "start_item_id": start_node_id,
            "start_point_type": start_point_type,
            "end_item_id": end_node_id,
            "end_point_type": end_point_type,
            "label": label
        }
        self.connections.append(connection)
    
    def connection_exists(self, start_node_id: str, end_node_id: str) -> bool:
        """
        检查两个节点之间是否存在连接
        
        参数:
            start_node_id: 起始节点ID
            end_node_id: 结束节点ID
            
        返回:
            bool: 如果存在连接返回True，否则返回False
        """
        return any(
            conn["start_item_id"] == start_node_id and 
            conn["end_item_id"] == end_node_id
            for conn in self.connections
        )
    
    def get_connections_from_node(self, node_id: str) -> List[Dict[str, Any]]:
        """
        获取从指定节点发出的所有连接
        
        参数:
            node_id: 节点ID
            
        返回:
            List: 连接列表
        """
        return [conn for conn in self.connections if conn["start_item_id"] == node_id]
    
    def get_connections_to_node(self, node_id: str) -> List[Dict[str, Any]]:
        """
        获取指向指定节点的所有连接
        
        参数:
            node_id: 节点ID
            
        返回:
            List: 连接列表
        """
        return [conn for conn in self.connections if conn["end_item_id"] == node_id]
    
    def reset(self):
        """重置连接管理器状态"""
        self.connections = []
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """
        获取所有连接
        
        返回:
            List: 所有连接列表
        """
        return self.connections
    
    def remove_connections_with_nodes(self, node_ids: List[str]):
        """
        移除涉及指定节点的所有连接
        
        参数:
            node_ids: 节点ID列表
        """
        self.connections = [
            conn for conn in self.connections 
            if conn["start_item_id"] not in node_ids 
            and conn["end_item_id"] not in node_ids
        ]

