"""
流程图场景类
"""
from PyQt6.QtWidgets import QGraphicsScene, QMessageBox
from PyQt6.QtGui import QBrush, QColor, QPen, QTransform
from PyQt6.QtCore import Qt

from GUI.items import FlowchartItem, ConnectionPoint, ConnectionLine
from utils.config_manager import get_config
from utils.color_utils import to_qcolor, normalize_color


class FlowchartScene(QGraphicsScene):
    """流程图场景"""

    def __init__(self):
        super().__init__()
        self.connections = []
        self.start_connection = None

        # 从配置文件加载画布参数
        self.scene_origin_x = get_config('scene', 'origin_x', default=-5000)
        self.scene_origin_y = get_config('scene', 'origin_y', default=-5000)
        self.min_width = get_config('scene', 'min_width', default=1000)
        self.min_height = get_config('scene', 'min_height', default=1000)
        self.current_max_width = self.min_width
        self.current_max_height = self.min_height
        self.padding = get_config('scene', 'padding', default=500)
        self.batch_loading = False

        # 设置初始画布范围
        self.setSceneRect(self.scene_origin_x, self.scene_origin_y, 
                         self.current_max_width, self.current_max_height)

        # 从配置文件加载背景设置
        bg_color_value = get_config('scene', 'background_color', default=[230, 230, 230])
        self.background_color = to_qcolor(bg_color_value, [230, 230, 230])
        self.setBackgroundBrush(QBrush(self.background_color))
        self.grid_size = get_config('scene', 'grid_size', default=20)
        grid_color_value = get_config('scene', 'grid_color', default=[200, 200, 200])
        self.grid_color = normalize_color(grid_color_value, [200, 200, 200])
        self.grid_qcolor = QColor(*self.grid_color)

    def drawBackground(self, painter, rect):
        """绘制背景网格"""
        super().drawBackground(painter, rect)

        painter.setPen(QPen(self.grid_qcolor, 1))

        # 绘制垂直线
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())
        for x in range(left, right, self.grid_size):
            painter.drawLine(x, top, x, bottom)

        # 绘制水平线
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        bottom = int(rect.bottom())
        left = int(rect.left())
        right = int(rect.right())
        for y in range(top, bottom, self.grid_size):
            painter.drawLine(left, y, right, y)

    def update_scene_bounds(self):
        """动态更新画布大小以容纳所有元素（只增大，不减小）"""
        items_rect = self.itemsBoundingRect()
        
        if items_rect.isNull() or items_rect.isEmpty():
            return
        
        # 添加边距
        min_left = items_rect.left() - self.padding
        min_top = items_rect.top() - self.padding
        max_right = items_rect.right() + self.padding
        max_bottom = items_rect.bottom() + self.padding
        
        # 调试信息
        print(f"项目边界: left={items_rect.left():.0f}, top={items_rect.top():.0f}, "
              f"right={items_rect.right():.0f}, bottom={items_rect.bottom():.0f}")
        
        # 计算新的起点和尺寸
        new_origin_x = min_left
        new_origin_y = min_top
        new_width = max_right - new_origin_x
        new_height = max_bottom - new_origin_y
        
        # 确保不小于最小尺寸
        new_width = max(new_width, self.min_width)
        new_height = max(new_height, self.min_height)
        
        # 只增大，不减小
        actual_origin_x = min(self.scene_origin_x, new_origin_x)
        actual_origin_y = min(self.scene_origin_y, new_origin_y)
        
        actual_width = max(max_right - actual_origin_x, self.current_max_width)
        actual_height = max(max_bottom - actual_origin_y, self.current_max_height)
        
        # 更新记录的起点和尺寸
        if (actual_origin_x != self.scene_origin_x or 
            actual_origin_y != self.scene_origin_y or
            actual_width > self.current_max_width or 
            actual_height > self.current_max_height):
            
            self.scene_origin_x = actual_origin_x
            self.scene_origin_y = actual_origin_y
            self.current_max_width = actual_width
            self.current_max_height = actual_height
            
            self.setSceneRect(self.scene_origin_x, self.scene_origin_y,
                            self.current_max_width, self.current_max_height)
            
            print(f"画布更新: origin=({self.scene_origin_x:.0f}, {self.scene_origin_y:.0f}), "
                  f"size=({self.current_max_width:.0f} x {self.current_max_height:.0f})")
    
    def addItem(self, item):
        """重写addItem方法，在添加元素后更新画布大小"""
        super().addItem(item)
        if isinstance(item, FlowchartItem) and not self.batch_loading:
            self.update_scene_bounds()

    def handle_connection_point_click(self, connection_point, event):
        """处理连接点点击事件"""
        print(f"\n=== 场景处理连接点点击 ===")
        print(f"连接点: {connection_point}")
        print(f"连接点类型: {connection_point.point_type}")
        print(f"start_connection: {self.start_connection}")

        if not self.start_connection:
            # 开始连接
            self.start_connection = connection_point
            connection_point.setBrush(QBrush(Qt.GlobalColor.blue))
            connection_point.update()
            print(f"开始连接: {connection_point.point_type}")
        else:
            # 结束连接
            end_connection = connection_point

            # 检查是否连接到同一元素
            if self.start_connection.parent_item == end_connection.parent_item:
                QMessageBox.warning(None, "错误", "不能连接同一元素的连接点")
                self.start_connection.setBrush(QBrush(Qt.GlobalColor.red))
                self.start_connection.update()
                self.start_connection = None
                return

            # 检查连接规则
            start_point_type = self.start_connection.point_type
            end_point_type = end_connection.point_type
            end_item_type = end_connection.parent_item.item_type

            valid = False
            # 直接连接规则
            if (start_point_type == 'down' and end_point_type == 'up') or \
                    (start_point_type == 'right' and end_point_type == 'left') or \
                    (start_point_type == 'right' and end_point_type == 'right') or \
                    (start_point_type == 'left' and end_point_type == 'left'):
                valid = True
            # 判断结构特殊连接规则
            elif end_item_type == 'decision' and end_point_type == 'up':
                if start_point_type in ['left', 'right', 'down']:
                    valid = True
            # 其他连接规则
            elif (start_point_type in ['left', 'right']) and end_point_type == 'up':
                valid = True

            print(f"\n=== 连接规则检查 ===")
            print(f"连接类型: {start_point_type} → {end_point_type}")
            print(f"终点元素类型: {end_item_type}")
            print(f"连接是否有效: {valid}")

            if not valid:
                QMessageBox.warning(None, "错误", f"不允许的连接方式: {start_point_type} → {end_point_type}")
                self.start_connection.setBrush(QBrush(Qt.GlobalColor.red))
                self.start_connection.update()
                self.start_connection = None
                return

            # 创建连接线
            connection = ConnectionLine(
                self.start_connection.parent_item,
                start_point_type,
                end_connection.parent_item,
                end_point_type
            )
            self.addItem(connection)
            self.connections.append(connection)
            connection.update_path()

            print(f"\n=== 连接创建成功 ===")
            print(f"当前连接数量: {len(self.connections)}")

            # 重置起始连接点
            self.start_connection.setBrush(QBrush(Qt.GlobalColor.red))
            self.start_connection = None

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        item = self.itemAt(event.scenePos(), QTransform())

        print(f"\n=== 鼠标按下事件 ===")
        print(f"点击位置: {event.scenePos()}")
        print(f"点击的项目类型: {item.__class__.__name__ if item else 'None'}")

        if item:
            print(f"项目信息: {item}")
            if isinstance(item, ConnectionPoint):
                print(f"连接点类型: {item.point_type}")
            elif isinstance(item, FlowchartItem):
                print(f"流程图元素类型: {item.item_type}")

        super().mousePressEvent(event)

    def clear(self):
        """清空场景"""
        super().clear()
        self.connections.clear()
        self.start_connection = None
        
        # 重置画布大小
        self.current_max_width = self.min_width
        self.current_max_height = self.min_height
        self.setSceneRect(self.scene_origin_x, self.scene_origin_y,
                         self.current_max_width, self.current_max_height)

