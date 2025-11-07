"""
流程图连接线和标签类
"""
from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsPathItem, QMenu
from PyQt6.QtGui import QPen, QBrush, QFont, QPainterPath, QPolygonF, QVector2D
from PyQt6.QtCore import Qt, QPointF
from utils.config_manager import get_config


class ConnectionLabelItem(QGraphicsTextItem):
    """连接线标签项，支持右键菜单"""
    
    def __init__(self, text, parent_connection):
        super().__init__(text)
        self.parent_connection = parent_connection
        
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        self.parent_connection.contextMenuEvent(event)


class ConnectionLine(QGraphicsPathItem):
    """连接线类"""

    def __init__(self, start_item, start_point_type, end_item, end_point_type):
        super().__init__()
        self.start_item = start_item
        self.start_point_type = start_point_type
        self.end_item = end_item
        self.end_point_type = end_point_type

        # 从配置文件加载连接线设置
        line_width = get_config('connection', 'line', 'width', default=2)
        line_z_value = get_config('connection', 'line', 'z_value', default=5)
        
        # 创建带箭头的画笔
        self.pen = QPen(Qt.GlobalColor.black, line_width)
        self.setPen(self.pen)
        self.setZValue(line_z_value)

        # 从配置文件加载箭头设置
        self.arrow_size = get_config('connection', 'arrow', 'size', default=10)
        
        # 从配置文件加载路径偏移量
        self.offsets = get_config('connection', 'path_offsets', default={})

        # 标签相关
        self.label = None
        self.label_item = None

        # 检查是否需要自动添加默认标签
        self.check_default_label()
        
        # 初始化时更新路径
        self.update_path()

    def check_default_label(self):
        """检查是否需要自动添加默认标签"""
        if self.start_item.item_type == 'decision':
            if self.start_point_type == 'down':
                self.label = "否"
                self.create_label()
            elif self.start_point_type in ['left', 'right']:
                self.label = "是"
                self.create_label()
        if self.label and not self.label_item and self.scene():
            self.create_label()

    def create_label(self):
        """创建标签图形项"""
        if not self.label or not self.scene():
            return

        if self.label_item:
            self.remove_label()

        # 从配置文件加载标签字体设置
        font_family = get_config('text', 'font_family', default='Arial')
        label_font_size = get_config('text', 'label_font_size', default=12)

        self.label_item = ConnectionLabelItem(self.label, self)
        self.label_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.label_item.setFont(QFont(font_family, label_font_size))
        self.label_item.setZValue(10)

        self.scene().addItem(self.label_item)
        self.update_label_position()

    def update_label_position(self):
        """更新标签位置"""
        if not self.label_item or self.path().isEmpty():
            return

        path = self.path()
        if path.elementCount() >= 2:
            mid_index = path.elementCount() // 2
            if mid_index >= path.elementCount() - 1:
                mid_index = path.elementCount() - 2

            point1 = QPointF(path.elementAt(mid_index).x, path.elementAt(mid_index).y)
            point2 = QPointF(path.elementAt(mid_index + 1).x, path.elementAt(mid_index + 1).y)

            mid_point = (point1 + point2) / 2
            label_rect = self.label_item.boundingRect()

            if point1.x() == point2.x():  # 垂直线段
                self.label_item.setPos(mid_point.x() - label_rect.width() - 5,
                                     mid_point.y() - label_rect.height() / 2)
            elif point1.y() == point2.y():  # 水平线段
                self.label_item.setPos(mid_point.x() - label_rect.width() / 2,
                                     mid_point.y() - label_rect.height() - 5)
            else:  # 斜线
                self.label_item.setPos(mid_point.x() - label_rect.width() / 2,
                                     mid_point.y() - label_rect.height() - 5)

    def remove_label(self):
        """移除标签"""
        if self.label_item and self.scene():
            self.scene().removeItem(self.label_item)
            self.label_item = None
        self.label = None
    
    def handle_menu_action(self, action):
        """处理菜单动作"""
        if action is None:
            return
            
        action_text = action.text()
        if action_text == "删除":
            scene = self.scene()
            if scene and hasattr(scene, 'connections'):
                self.remove_label()
                if self in scene.connections:
                    scene.connections.remove(self)
                scene.removeItem(self)
        elif action_text == "添加\"是\"标签":
            self.label = "是"
            self.create_label()
        elif action_text == "添加\"否\"标签":
            self.label = "否"
            self.create_label()
        elif action_text == "清除标签":
            self.remove_label()
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu()
        delete_action = menu.addAction("删除")
        yes_action = menu.addAction("添加\"是\"标签")
        no_action = menu.addAction("添加\"否\"标签")
        clear_action = menu.addAction("清除标签")

        action = menu.exec(event.screenPos())
        self.handle_menu_action(action)

    def paint(self, painter, option, widget=None):
        """绘制带箭头的连接线"""
        super().paint(painter, option, widget)

        path = self.path()
        if path.isEmpty():
            return

        # 获取路径的最后一段
        last_point = path.currentPosition()
        penultimate_point = path.elementAt(path.elementCount() - 2)
        penultimate_point = QPointF(penultimate_point.x, penultimate_point.y)

        # 计算箭头方向
        direction = last_point - penultimate_point
        vector = QVector2D(direction)
        vector.normalize()
        direction = QPointF(vector.x(), vector.y())

        # 创建箭头多边形
        arrow_polygon = QPolygonF()
        arrow_polygon.append(last_point)
        arrow_polygon.append(last_point - self.arrow_size * QPointF(direction.x() + direction.y(),
                                                                    -direction.x() + direction.y()))
        arrow_polygon.append(last_point - self.arrow_size * QPointF(direction.x() - direction.y(),
                                                                    direction.x() + direction.y()))

        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawPolygon(arrow_polygon)

    def update_path(self):
        """更新连接线路径"""
        if not (self.start_item and self.end_item):
            return

        start_point = self.start_item.connection_points[self.start_point_type].scenePos()
        end_point = self.end_item.connection_points[self.end_point_type].scenePos()

        path = QPainterPath()
        path.moveTo(start_point)

        is_end_decision = (self.end_item.item_type == 'decision')

        # 根据连接类型生成不同路径
        if (self.start_point_type == 'down' and self.end_point_type == 'up'):
            self._draw_down_to_up_path(path, start_point, end_point)
        elif (self.start_point_type == 'up' and self.end_point_type == 'down'):
            self._draw_up_to_down_path(path, start_point, end_point)
        elif (self.start_point_type == 'right' and self.end_point_type == 'left'):
            path.lineTo(end_point)
        elif (self.start_point_type == 'left' and self.end_point_type == 'right'):
            self._draw_left_to_right_path(path, start_point, end_point)
        elif (self.start_point_type == 'right' and self.end_point_type == 'right'):
            self._draw_right_to_right_path(path, start_point, end_point)
        elif (self.start_point_type == 'left' and self.end_point_type == 'left'):
            self._draw_left_to_left_path(path, start_point, end_point)
        elif self.start_point_type == 'down' and self.end_point_type in ('left', 'right'):
            self._draw_down_to_side_path(path, start_point, end_point)
        elif self.start_point_type == 'right' and self.end_point_type == 'up':
            self._draw_right_to_up_path(path, start_point, end_point)
        elif self.start_point_type == 'left' and self.end_point_type == 'up':
            self._draw_left_to_up_path(path, start_point, end_point)
        elif is_end_decision and self.end_point_type == 'up' and self.start_point_type == 'down':
            self._draw_down_to_up_decision_path(path, start_point, end_point)
        else:
            path.lineTo(end_point)

        self.setPath(path)
        self.update_label_position()

    def _collect_function_items(self):
        """收集与当前连接属于同一函数块的元素"""
        scene = self.scene()
        if not scene or not hasattr(scene, 'connections'):
            return set()

        visited = set()
        queue = []

        if self.start_item:
            visited.add(self.start_item)
            queue.append(self.start_item)

        if self.end_item and self.end_item not in visited:
            visited.add(self.end_item)
            queue.append(self.end_item)

        while queue:
            current = queue.pop(0)
            for conn in scene.connections:
                if not isinstance(conn, ConnectionLine):
                    continue

                neighbors = []
                if conn.start_item == current:
                    neighbors.append(conn.end_item)
                if conn.end_item == current:
                    neighbors.append(conn.start_item)

                for neighbor in neighbors:
                    if neighbor and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

        return visited

    def _get_function_rightmost_x(self):
        """获取当前函数块内最右侧元素的X坐标"""
        items = self._collect_function_items()
        rightmost = None

        for item in items:
            if hasattr(item, 'sceneBoundingRect'):
                rect = item.sceneBoundingRect()
                rect_right = rect.right()
                if rightmost is None or rect_right > rightmost:
                    rightmost = rect_right

        return rightmost

    def _draw_down_to_up_path(self, path, start_point, end_point):
        """down->up 连接路径"""
        mid_offset = self.offsets.get('down_to_up', {}).get('mid_offset', 40)
        
        if end_point.y() > start_point.y():
            upper_block_down_y = None
            if self.scene():
                for conn in self.scene().connections:
                    if (conn != self and 
                        conn.end_item == self.end_item and 
                        conn.end_point_type == 'up' and
                        conn.start_point_type == 'down'):
                        upper_block_down_point = conn.start_item.connection_points['down'].scenePos()
                        upper_block_down_y = upper_block_down_point.y()
                        break
            
            if upper_block_down_y is not None:
                mid_y = (end_point.y() + upper_block_down_y) / 2
            else:
                mid_y = end_point.y() - mid_offset
            
            if start_point.y() < mid_y:
                path.lineTo(start_point.x(), mid_y)
                path.lineTo(end_point.x(), mid_y)
                path.lineTo(end_point)
            else:
                y_diff = abs(end_point.y() - start_point.y())
                down_distance = y_diff / 2
                path.lineTo(start_point.x(), start_point.y() + down_distance)
                path.lineTo(end_point.x(), path.currentPosition().y())
                path.lineTo(end_point)
        else:
            y_diff = abs(end_point.y() - start_point.y())
            down_distance = y_diff / 2
            path.lineTo(start_point.x(), start_point.y() + down_distance)
            path.lineTo(end_point.x(), path.currentPosition().y())
            path.lineTo(end_point)

    def _draw_up_to_down_path(self, path, start_point, end_point):
        """up->down 连接路径"""
        down_offset = self.offsets.get('up_to_down', {}).get('down_offset', 30)
        horizontal_ratio = self.offsets.get('up_to_down', {}).get('horizontal_ratio', 0.7)
        mid_offset = self.offsets.get('up_to_down', {}).get('mid_offset', 40)
        
        horizontal_offset = self.start_item.boundingRect().width() * horizontal_ratio
        mid_y = end_point.y() - mid_offset

        path.lineTo(start_point.x(), start_point.y() + down_offset)
        path.lineTo(start_point.x() + horizontal_offset, path.currentPosition().y())
        path.lineTo(path.currentPosition().x(), mid_y)
        path.lineTo(end_point.x(), mid_y)
        path.lineTo(end_point)

    def _draw_right_to_right_path(self, path, start_point, end_point):
        """right->right 连接路径"""
        horizontal_offset = self.offsets.get('horizontal_loop', {}).get('offset', 50)
        path.lineTo(start_point.x() + horizontal_offset, start_point.y())
        path.lineTo(path.currentPosition().x(), end_point.y())
        path.lineTo(end_point.x(), path.currentPosition().y())
        path.lineTo(end_point)

    def _draw_left_to_left_path(self, path, start_point, end_point):
        """left->left 连接路径"""
        horizontal_offset = self.offsets.get('horizontal_loop', {}).get('offset', 50)
        path.lineTo(start_point.x() - horizontal_offset, start_point.y())
        path.lineTo(path.currentPosition().x(), end_point.y())
        path.lineTo(end_point.x(), path.currentPosition().y())
        path.lineTo(end_point)

    def _draw_left_to_right_path(self, path, start_point, end_point):
        """left->right 直接连接"""
        path.lineTo(end_point)

    def _draw_down_to_side_path(self, path, start_point, end_point):
        """down->left/right 先向下再水平"""
        path.lineTo(start_point.x(), end_point.y())
        path.lineTo(end_point.x(), end_point.y())

    def _draw_right_to_up_path(self, path, start_point, end_point):
        """right->up 连接路径"""
        base_spacing = self.offsets.get('right_to_up', {}).get('base_spacing', 50)
        dynamic_spacing_per_conn = self.offsets.get('right_to_up', {}).get('dynamic_spacing', 30)
        extra_up_distance = self.offsets.get('right_to_up', {}).get('extra_up_distance', 20)
        
        if end_point.y() < start_point.y():
            rightmost_x = start_point.x()
            function_rightmost = self._get_function_rightmost_x()

            if function_rightmost is not None:
                rightmost_x = max(rightmost_x, function_rightmost)
            elif self.scene():
                for item in self.scene().items():
                    if hasattr(item, 'sceneBoundingRect'):
                        item_right_edge = item.sceneBoundingRect().right()
                        if item_right_edge > rightmost_x:
                            rightmost_x = item_right_edge
            
            same_target_count = 0
            if self.scene():
                for conn in self.scene().connections:
                    if (conn != self and 
                        conn.end_item == self.end_item and 
                        conn.end_point_type == 'up' and
                        conn.start_point_type == 'right'):
                        same_target_count += 1
            
            dynamic_spacing = same_target_count * dynamic_spacing_per_conn
            horizontal_offset = (rightmost_x - start_point.x()) + base_spacing + dynamic_spacing

            path.lineTo(start_point.x() + horizontal_offset, start_point.y())
            path.lineTo(path.currentPosition().x(), end_point.y() - extra_up_distance)
            path.lineTo(end_point.x(), path.currentPosition().y())
            path.lineTo(end_point)
        else:
            path.lineTo(end_point.x(), start_point.y())
            path.lineTo(end_point)

    def _draw_left_to_up_path(self, path, start_point, end_point):
        """left->up 连接路径"""
        horizontal_offset = self.offsets.get('left_to_up', {}).get('horizontal_offset', 50)
        extra_up_distance = self.offsets.get('left_to_up', {}).get('extra_up_distance', 20)
        
        if end_point.y() < start_point.y():
            path.lineTo(start_point.x() - horizontal_offset, start_point.y())
            path.lineTo(path.currentPosition().x(), end_point.y() - extra_up_distance)
            path.lineTo(end_point.x(), path.currentPosition().y())
            path.lineTo(end_point)
        else:
            path.lineTo(end_point.x(), start_point.y())
            path.lineTo(end_point)

    def _draw_down_to_up_decision_path(self, path, start_point, end_point):
        """down->up decision 连接路径"""
        horizontal_offset = self.offsets.get('decision_loop', {}).get('horizontal_offset', 30)
        mid_offset = self.offsets.get('decision_loop', {}).get('mid_offset', 40)
        
        mid_y = end_point.y() - mid_offset

        path.lineTo(start_point.x() + horizontal_offset, start_point.y())
        path.lineTo(path.currentPosition().x(), mid_y)
        path.lineTo(end_point.x(), mid_y)
        path.lineTo(end_point)

