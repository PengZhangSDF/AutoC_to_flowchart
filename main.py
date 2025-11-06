"""
流程图工具主文件
"""
import sys
import uuid
from logger import logger, print_to_log as print
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QMenuBar, QMenu,
                             QGraphicsScene, QGraphicsView, QGraphicsItem,
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
                             QGraphicsEllipseItem, QMenu, QMessageBox, QTextEdit, QLabel)
from PyQt6.QtGui import (QPen, QBrush, QColor, QFont, QPainterPath,
                         QTransform, QPolygonF, QVector2D, QPainter, QAction)
from PyQt6.QtCore import Qt, QPointF, QRectF

# 流程图元素类型
ITEM_TYPES = {
    'start': {'name': '开始/结束', 'shape': 'oval'},
    'end': {'name': '开始/结束', 'shape': 'oval'},
    'input': {'name': '输入/输出', 'shape': 'parallelogram'},
    'process': {'name': '语句', 'shape': 'rectangle'},
    'decision': {'name': '判断/循环', 'shape': 'diamond'}
}

# 连接点位置
CONNECTION_POINTS = ['up', 'down', 'left', 'right']


class ConnectionPoint(QGraphicsEllipseItem):
    """连接点类"""

    def __init__(self, parent_item, point_type):
        super().__init__(parent_item)
        self.parent_item = parent_item
        self.point_type = point_type  # 'up', 'down', 'left', 'right'
        self.radius = 5
        self.hit_radius = 10  # 点击判定范围半径，比显示半径大
        self.setRect(-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        self.setBrush(QBrush(Qt.GlobalColor.red))
        self.setPen(QPen(Qt.GlobalColor.darkRed, 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(10)  # 确保连接点在最上层

    def shape(self):
        """重定义形状以增大点击判定范围"""
        path = QPainterPath()
        path.addEllipse(-self.hit_radius, -self.hit_radius, self.hit_radius * 2, self.hit_radius * 2)
        return path

    def boundingRect(self):
        """重定义边界矩形以匹配增大的点击判定范围"""
        return QRectF(-self.hit_radius, -self.hit_radius, self.hit_radius * 2, self.hit_radius * 2)

    def update_position(self):
        """更新连接点位置"""
        item_rect = self.parent_item.boundingRect()
        if self.point_type == 'up':
            self.setPos(item_rect.center().x(), item_rect.top())
        elif self.point_type == 'down':
            self.setPos(item_rect.center().x(), item_rect.bottom())
        elif self.point_type == 'left':
            self.setPos(item_rect.left(), item_rect.center().y())
        elif self.point_type == 'right':
            self.setPos(item_rect.right(), item_rect.center().y())

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        logger.debug(f"\n=== ConnectionPoint 鼠标按下事件 ===")
        logger.debug(f"连接点类型: {self.point_type}")
        logger.debug(f"连接点位置: {self.scenePos()}")
        logger.debug(f"事件按钮: {event.button()}")

        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()  # 先接受事件，阻止进一步传播
            logger.debug(f"连接点点击已接受，直接调用场景处理连接")

            # 获取场景
            scene = self.scene()
            if scene and hasattr(scene, 'handle_connection_point_click'):
                # 直接调用场景的方法处理连接点点击
                scene.handle_connection_point_click(self, event)
            else:
                logger.debug(f"无法获取场景或场景没有handle_connection_point_click方法")
        else:
            logger.debug(f"非左键点击，转发给父类")
            super().mousePressEvent(event)


class FlowchartItem(QGraphicsItem):
    """流程图元素基类"""

    def __init__(self, item_type, x, y, width=125, height=75):  # 增大25%
        super().__init__()
        self.item_type = item_type
        self.id = str(uuid.uuid4())
        self.text = ""
        self.setPos(x, y)
        self.width = width
        self.height = height
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)  # 使元素可以获得焦点

        # 创建连接点
        self.connection_points = {}
        for point_type in CONNECTION_POINTS:
            point = ConnectionPoint(self, point_type)
            self.connection_points[point_type] = point
            # 确保连接点可以接收鼠标事件
            point.setAcceptHoverEvents(True)

        # 创建文本元素（不可编辑，文字直接显示在块上）
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.text_item.setFont(QFont("Arial", 12))
        # 设置文本居中对齐
        self.text_item.setHtml('<div align="center">' + self.text + '</div>')
        # 设置文本为不可编辑，不可选择，不可移动
        self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

        # 连接文本变化信号，实现实时居中
        self.text_item.document().contentsChanged.connect(self.update_text_position)

        self.update_connection_points()
        self.update_text_position()

    def boundingRect(self):
        """重定义边界矩形"""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        """重定义绘制方法"""
        # 设置画笔和画刷
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))

        # 根据元素类型绘制不同的形状
        if ITEM_TYPES[self.item_type]['shape'] == 'oval':
            # 绘制椭圆形（开始/结束）
            painter.drawEllipse(self.boundingRect())
        elif ITEM_TYPES[self.item_type]['shape'] == 'parallelogram':
            # 绘制平行四边形（输入/输出）
            path = QPainterPath()
            rect = self.boundingRect()
            offset = rect.height() / 4
            path.moveTo(rect.left() + offset, rect.top())
            path.lineTo(rect.right() - offset, rect.top())
            path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.left(), rect.bottom())
            path.closeSubpath()
            painter.drawPath(path)
        elif ITEM_TYPES[self.item_type]['shape'] == 'diamond':
            # 绘制菱形（判断/循环）
            path = QPainterPath()
            rect = self.boundingRect()
            path.moveTo(rect.center().x(), rect.top())
            path.lineTo(rect.right(), rect.center().y())
            path.lineTo(rect.center().x(), rect.bottom())
            path.lineTo(rect.left(), rect.center().y())
            path.closeSubpath()
            painter.drawPath(path)
        else:
            # 默认绘制矩形（语句）
            painter.drawRect(self.boundingRect())

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        self.show_context_menu(event.screenPos())

    def show_context_menu(self, global_pos):
        """显示右键菜单（通用方法）"""
        menu = QMenu()
        delete_action = menu.addAction("删除")
        action = menu.exec(global_pos)

        if action == delete_action:
            # 获取场景
            scene = self.scene()
            if scene:
                # 删除与该元素相关的所有连接
                connections_to_remove = []
                for connection in scene.connections:
                    if connection.start_item == self or connection.end_item == self:
                        connections_to_remove.append(connection)

                for connection in connections_to_remove:
                    scene.removeItem(connection)
                    scene.connections.remove(connection)

                # 删除元素本身
                scene.removeItem(self)

    def update_connection_points(self):
        """更新所有连接点位置"""
        for point in self.connection_points.values():
            point.update_position()

    def update_text_position(self):
        """更新文本位置"""
        if self.text_item:
            item_rect = self.boundingRect()
            # 设置文本宽度限制，留出一些边距
            text_width = item_rect.width() - 20  # 左右各留10像素边距
            text_height = item_rect.height() - 20  # 上下各留10像素边距

            # 设置文本宽度，自动换行
            self.text_item.setTextWidth(text_width)

            # 获取调整后的文本矩形
            text_rect = self.text_item.boundingRect()

            # 计算居中位置
            text_x = (item_rect.width() - text_rect.width()) / 2
            text_y = (item_rect.height() - text_rect.height()) / 2

            # 确保文本在元素内部
            if text_y < 10:
                text_y = 10
            elif text_y + text_rect.height() > item_rect.height() - 10:
                text_y = item_rect.height() - 10 - text_rect.height()

            self.text_item.setPos(text_x, text_y)

    def setText(self, text):
        """设置文本"""
        self.text = text
        # 对特殊字符进行HTML转义，确保正确显示
        escaped_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # 设置文本居中对齐
        self.text_item.setHtml('<div align="center">' + escaped_text + '</div>')
        self.update_text_position()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在连接点上
            pos = event.pos()
            for point in self.connection_points.values():
                if point.contains(pos):
                    # 如果点击在连接点上，让连接点自己处理事件
                    return

            # 点击在元素上（包括文本），选中该元素并准备拖动
            self.setSelected(True)
            # 记录拖动起始位置
            self.drag_start_pos = event.pos()

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击事件 - 不处理文本编辑"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 双击击也选中元素，不进入文本编辑模式
            self.setSelected(True)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        """失去焦点事件"""
        self.text = self.text_item.toPlainText()
        # 确保文本始终不可编辑，只能通过工具栏编辑
        self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().focusOutEvent(event)

    def sceneEventFilter(self, watched, event):
        """事件过滤器，确保点击文本时也能选中并拖动整个块"""
        if watched == self.text_item:
            # 处理鼠标按下事件
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                # 将事件转发给父元素，这样点击文本也会选中整个块
                new_event = type(event)(
                    event.type(),
                    self.mapFromScene(event.scenePos()),
                    event.button(),
                    event.buttons(),
                    event.modifiers()
                )
                QApplication.postEvent(self, new_event)
                return True  # 接受事件，不再进一步处理

        return super().sceneEventFilter(watched, event)

    def itemChange(self, change, value):
        """处理项目变化"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 更新连接点位置
            self.update_connection_points()
            # 更新连接线
            scene = self.scene()
            if scene and hasattr(scene, 'connections'):
                for connection in scene.connections:
                    if connection.start_item == self or connection.end_item == self:
                        connection.update_path()
                # 更新画布大小以适应元素位置变化
                if hasattr(scene, 'update_scene_bounds'):
                    scene.update_scene_bounds()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        """绘制流程图元素"""
        # 设置画笔和画刷
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))

        rect = self.boundingRect()

        # 根据类型绘制不同形状
        if self.item_type == 'start' or self.item_type == 'end':
            # 跑道形状
            painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        elif self.item_type == 'input':
            # 平行四边形
            path = QPainterPath()
            offset = rect.width() * 0.2
            path.moveTo(rect.left() + offset, rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right() - offset, rect.bottom())
            path.lineTo(rect.left(), rect.bottom())
            path.closeSubpath()
            painter.drawPath(path)
        elif self.item_type == 'process':
            # 矩形
            painter.drawRect(rect)
        elif self.item_type == 'decision':
            # 菱形
            path = QPainterPath()
            path.moveTo(rect.center().x(), rect.top())
            path.lineTo(rect.right(), rect.center().y())
            path.lineTo(rect.center().x(), rect.bottom())
            path.lineTo(rect.left(), rect.center().y())
            path.closeSubpath()
            painter.drawPath(path)

        # 绘制文本（由text_item处理）


class ConnectionLabelItem(QGraphicsTextItem):
    """连接线标签项，支持右键菜单"""
    def __init__(self, text, parent_connection):
        super().__init__(text)
        self.parent_connection = parent_connection  # 保存对连接线的引用
        
    def contextMenuEvent(self, event):
        # 调用父连接线的右键菜单显示方法
        self.parent_connection.contextMenuEvent(event)


class ConnectionLine(QGraphicsPathItem):
    """连接线类"""

    def __init__(self, start_item, start_point_type, end_item, end_point_type):
        super().__init__()
        self.start_item = start_item
        self.start_point_type = start_point_type
        self.end_item = end_item
        self.end_point_type = end_point_type

        # 创建带箭头的画笔
        self.pen = QPen(Qt.GlobalColor.black, 2)
        self.setPen(self.pen)
        self.setZValue(5)  # 确保连接线在元素下方

        # 箭头设置
        self.arrow_size = 10

        # 标签相关
        self.label = None  # 标签文本
        self.label_item = None  # 标签图形项

        # 检查是否需要自动添加默认标签
        self.check_default_label()
        
        # 初始化时更新路径，确保加载文件时应用正确的连接规则
        self.update_path()

    def check_default_label(self):
        """检查是否需要自动添加默认标签"""
        # 检查起点是否为判断类型元素
        if self.start_item.item_type == 'decision':
            # 默认在判断下方的线左侧中点（如有线）加上"否"
            if self.start_point_type == 'down':
                self.label = "否"
                self.create_label()
            # 左侧或者右侧引出的线（不是引入）加上"是"
            elif self.start_point_type in ['left', 'right']:
                self.label = "是"
                self.create_label()
        # 确保在update_path时也应用标签
        if self.label and not self.label_item and self.scene():
            self.create_label()

    def create_label(self):
        """创建标签图形项"""
        if not self.label or not self.scene():
            return

        # 如果已存在标签，先移除
        if self.label_item:
            self.remove_label()

        # 创建自定义标签文本项，传入对连接线的引用
        self.label_item = ConnectionLabelItem(self.label, self)
        self.label_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.label_item.setFont(QFont("Arial", 12))  # 放大字体
        self.label_item.setZValue(10)  # 确保标签在最上层

        # 添加到场景
        self.scene().addItem(self.label_item)

        # 更新标签位置
        self.update_label_position()

    def update_label_position(self):
        """更新标签位置"""
        if not self.label_item or self.path().isEmpty():
            return

        path = self.path()
        # 获取路径的中点
        if path.elementCount() >= 2:
            # 对于多段线，找到中间的线段
            mid_index = path.elementCount() // 2
            if mid_index >= path.elementCount() - 1:
                mid_index = path.elementCount() - 2

            point1 = QPointF(path.elementAt(mid_index).x, path.elementAt(mid_index).y)
            point2 = QPointF(path.elementAt(mid_index + 1).x, path.elementAt(mid_index + 1).y)

            # 计算线段中点
            mid_point = (point1 + point2) / 2

            # 获取标签尺寸
            label_rect = self.label_item.boundingRect()

            # 设置标签位置（在线段中点上方或旁边）
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
            # 从场景中移除标签项
            self.scene().removeItem(self.label_item)
            self.label_item = None
        self.label = None
    
    def handle_menu_action(self, action):
        """处理菜单动作，避免代码重复"""
        if action is None:
            return
            
        action_text = action.text()
        if action_text == "删除":
            # 获取场景
            scene = self.scene()
            if scene and hasattr(scene, 'connections'):
                # 先移除标签，确保不会有残留
                self.remove_label()
                # 从场景的连接列表中移除
                if self in scene.connections:
                    scene.connections.remove(self)
                # 从场景中移除
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
        from PyQt6.QtWidgets import QMenu
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

        # 获取路径
        path = self.path()
        if path.isEmpty():
            return

        # 获取路径的最后一段
        last_point = path.currentPosition()
        penultimate_point = path.elementAt(path.elementCount() - 2)
        penultimate_point = QPointF(penultimate_point.x, penultimate_point.y)

        # 计算箭头方向
        direction = last_point - penultimate_point
        # 使用QVector2D进行归一化
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

        # 绘制箭头
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawPolygon(arrow_polygon)

    def update_path(self):
        """更新连接线路径"""
        if not (self.start_item and self.end_item):
            return

        # 获取连接点位置（场景坐标）
        start_point = self.start_item.connection_points[self.start_point_type].scenePos()
        end_point = self.end_item.connection_points[self.end_point_type].scenePos()

        path = QPainterPath()
        path.moveTo(start_point)

        # 检查终点是否为判断类型元素
        is_end_decision = (self.end_item.item_type == 'decision')

        # 根据连接类型生成不同路径
        if (self.start_point_type == 'down' and self.end_point_type == 'up'):
            # down->up连接模式
            
            # 判断目标up点是否在出发点下方（y坐标更大，视觉上更靠下）
            if end_point.y() > start_point.y():
                # 目标在下方：使用特殊逻辑
                # 查找目标节点上方块的down点位置
                upper_block_down_y = None
                if self.scene():
                    # 遍历所有连接，找到连接到目标节点up点的连接（即目标块的上方块）
                    for conn in self.scene().connections:
                        if (conn != self and 
                            conn.end_item == self.end_item and 
                            conn.end_point_type == 'up' and
                            conn.start_point_type == 'down'):
                            # 找到上方块的down点
                            upper_block_down_point = conn.start_item.connection_points['down'].scenePos()
                            upper_block_down_y = upper_block_down_point.y()
                            break
                
                # 计算中点位置
                if upper_block_down_y is not None:
                    # 计算目标up点和上方块down点的中点y坐标
                    mid_y = (end_point.y() + upper_block_down_y) / 2
                else:
                    # 如果没有找到上方块，使用目标up点上方一段距离
                    mid_y = end_point.y() - 40
                
                # 只有当出发点在中点上方时，才使用中点偏移逻辑
                if start_point.y() < mid_y:
                    # 第一段：向下移动到中点位置
                    path.lineTo(start_point.x(), mid_y)
                    
                    # 第二段：水平移动到up点的正上方
                    path.lineTo(end_point.x(), mid_y)
                    
                    # 第三段：向下连接到目标点
                    path.lineTo(end_point)
                else:
                    # 出发点在中点下方或同一位置，使用原始连接逻辑
                    y_diff = abs(end_point.y() - start_point.y())
                    down_distance = y_diff / 2
                    
                    # 第一段：向下移动abs(y2-y1)/2距离
                    path.lineTo(start_point.x(), start_point.y() + down_distance)
                    
                    # 第二段：水平移动到up点的正上方
                    path.lineTo(end_point.x(), path.currentPosition().y())
                    
                    # 第三段：向下连接到目标点
                    path.lineTo(end_point)
            else:
                # 目标在上方或同一水平：使用原有逻辑
                # 先向下移动abs(y2-y1)/2，再水平移动到up点的上方，再向下连接
                y_diff = abs(end_point.y() - start_point.y())
                down_distance = y_diff / 2

                # 第一段：向下移动abs(y2-y1)/2距离
                path.lineTo(start_point.x(), start_point.y() + down_distance)

                # 第二段：水平移动到up点的正上方
                path.lineTo(end_point.x(), path.currentPosition().y())

                # 第三段：向下连接到目标点
                path.lineTo(end_point)
        elif (self.start_point_type == 'up' and self.end_point_type == 'down'):
            # up->down连接模式：先向下偏移，再水平偏移超过图形宽的一半，再向上，再水平，最后连接
            down_offset = 30  # 向下偏移量
            horizontal_offset = self.start_item.rect().width() * 0.7  # 水平偏移超过图形宽的一半
            mid_y = end_point.y() - 40  # 终点上方的高度

            # 第一段：向下偏移
            path.lineTo(start_point.x(), start_point.y() + down_offset)

            # 第二段：水平偏移超过图形宽的一半
            path.lineTo(start_point.x() + horizontal_offset, path.currentPosition().y())

            # 第三段：向上到终点上方
            path.lineTo(path.currentPosition().x(), mid_y)

            # 第四段：水平到终点正上方
            path.lineTo(end_point.x(), mid_y)

            # 第五段：连接到终点
            path.lineTo(end_point)
        elif (self.start_point_type == 'right' and self.end_point_type == 'left'):
            # 水平连接
            path.lineTo(end_point)
        elif (self.start_point_type == 'right' and self.end_point_type == 'right'):
            # right->right连接模式：先水平向外平移，再竖直平移到目标点高度，再水平平移到连接点
            horizontal_offset = 50  # 水平向外偏移量

            # 第一段：水平向外平移
            path.lineTo(start_point.x() + horizontal_offset, start_point.y())

            # 第二段：竖直平移到目标点高度
            path.lineTo(path.currentPosition().x(), end_point.y())

            # 第三段：水平平移到连接点
            path.lineTo(end_point.x(), path.currentPosition().y())

            # 第四段：连接到终点
            path.lineTo(end_point)
        elif (self.start_point_type == 'left' and self.end_point_type == 'left'):
            # left->left连接模式：先水平向外平移，再竖直平移到目标点高度，再水平平移到连接点
            horizontal_offset = -50  # 水平向外偏移量（负值表示向左）

            # 第一段：水平向外平移
            path.lineTo(start_point.x() + horizontal_offset, start_point.y())

            # 第二段：竖直平移到目标点高度
            path.lineTo(path.currentPosition().x(), end_point.y())

            # 第三段：水平平移到连接点
            path.lineTo(end_point.x(), path.currentPosition().y())

            # 第四段：连接到终点
            path.lineTo(end_point)
        #TODO **等待修复
        elif is_end_decision and self.end_point_type != 'up' and \
                self.start_point_type in ['left', 'right', 'down']:
            # 对于判断结构，从左点、右点、下点连接到上点的特殊循环连接
            if self.start_point_type in ['left', 'right']:
                # 从left/right点到up点：先水平移动到终点正上方，再竖直连接（两段）
                # 第一段：水平移动到终点正上方
                path.lineTo(end_point.x(), start_point.y())

                # 第二段：竖直连接到终点
                path.lineTo(end_point)
            else:  # down
                # 从down点到up点的四段式连接
                offset = 30  # 水平偏移量
                mid_y = end_point.y() - 40  # 终点上方的高度

                # 第一段：水平偏移
                path.lineTo(start_point.x() + offset, start_point.y())

                # 第二段：垂直向上
                path.lineTo(path.currentPosition().x(), mid_y)

                # 第三段：水平连接到终点正上方
                path.lineTo(end_point.x(), mid_y)

                # 第四段：垂直向下到终点
                path.lineTo(end_point)
        elif self.start_point_type == 'right' and self.end_point_type == 'up':
            # 从right点到up点的连接逻辑
            
            # 无论目标元素类型如何，都统一应用四段式路径
            # 首先根据位置关系确定连接规则
            if end_point.y() < start_point.y():  # up点的y值比当前高度低（视觉上更高）
                # 四段式路径：先水平偏移，再向上，再水平，最后向下 - 适用于所有类型的目标节点（包括判断节点）
                
                # 动态计算水平偏移距离
                # 1. 找到场景中最右边的块
                rightmost_x = start_point.x()
                if self.scene():
                    for item in self.scene().items():
                        if hasattr(item, 'item_type') and item.item_type in ['process', 'decision', 'start', 'input']:
                            item_right_edge = item.x() + item.width
                            if item_right_edge > rightmost_x:
                                rightmost_x = item_right_edge
                
                # 2. 计算连向同一目标的其他 right->up 连接数量，确保不重叠
                same_target_count = 0
                if self.scene():
                    for conn in self.scene().connections:
                        if (conn != self and 
                            conn.end_item == self.end_item and 
                            conn.end_point_type == 'up' and
                            conn.start_point_type == 'right'):
                            same_target_count += 1
                
                # 3. 计算最终的水平偏移位置：最右边 + 基础间距 + 动态间距
                base_spacing = 50  # 基础间距
                dynamic_spacing = same_target_count * 30  # 每个连接增加30的间距
                horizontal_offset = (rightmost_x - start_point.x()) + base_spacing + dynamic_spacing
                
                extra_up_distance = 20  # 额外向上的距离

                # 第一段：水平向右偏移到计算出的位置
                path.lineTo(start_point.x() + horizontal_offset, start_point.y())

                # 第二段：向上到up点y值再高一段距离
                path.lineTo(path.currentPosition().x(), end_point.y() - extra_up_distance)

                # 第三段：水平平移到up点上方
                path.lineTo(end_point.x(), path.currentPosition().y())

                # 第四段：向下连接到up点
                path.lineTo(end_point)
            else:
                # up点在起点下方的情况
                # 对于所有类型节点统一使用两段式路径
                # 第一段：水平移动到终点正上方
                path.lineTo(end_point.x(), start_point.y())

                # 第二段：竖直连接到终点
                path.lineTo(end_point)
        elif self.start_point_type == 'left' and self.end_point_type == 'up':
            # 从left点到up点的连接逻辑（使用传统的简单逻辑）
            
            if end_point.y() < start_point.y():  # up点的y值比当前高度低（视觉上更高）
                # 四段式路径：先水平向左偏移，再向上，再水平，最后向下
                horizontal_offset = 50  # 水平偏移距离
                extra_up_distance = 20  # 额外向上的距离

                # 第一段：水平向左偏移一段距离
                path.lineTo(start_point.x() - horizontal_offset, start_point.y())

                # 第二段：向上到up点y值再高一段距离
                path.lineTo(path.currentPosition().x(), end_point.y() - extra_up_distance)

                # 第三段：水平平移到up点上方
                path.lineTo(end_point.x(), path.currentPosition().y())

                # 第四段：向下连接到up点
                path.lineTo(end_point)
            else:
                # up点在起点下方的情况
                # 对于所有类型节点统一使用两段式路径
                # 第一段：水平移动到终点正上方
                path.lineTo(end_point.x(), start_point.y())

                # 第二段：竖直连接到终点
                path.lineTo(end_point)
        elif is_end_decision and self.end_point_type == 'up' and \
                self.start_point_type == 'down':
            # 对于判断结构，从下点连接到上点的特殊循环连接
            # 从down点到up点的四段式连接
            offset = 30  # 水平偏移量
            mid_y = end_point.y() - 40  # 终点上方的高度

            # 第一段：水平偏移
            path.lineTo(start_point.x() + offset, start_point.y())

            # 第二段：垂直向上
            path.lineTo(path.currentPosition().x(), mid_y)

            # 第三段：水平连接到终点正上方
            path.lineTo(end_point.x(), mid_y)

            # 第四段：垂直向下到终点
            path.lineTo(end_point)
        else:
            # 默认直接连接
            path.lineTo(end_point)

        self.setPath(path)

        # 更新标签位置
        self.update_label_position()


class FlowchartScene(QGraphicsScene):
    """流程图场景"""

    def __init__(self):
        super().__init__()
        self.connections = []
        self.start_connection = None  # 起始连接点

        # 初始化画布参数（起点固定，尺寸动态调整）
        self.scene_origin_x = -5000
        self.scene_origin_y = -5000
        self.min_width = 1000  # 最小宽度
        self.min_height = 1000  # 最小高度
        self.current_max_width = self.min_width  # 当前最大宽度（只增不减）
        self.current_max_height = self.min_height  # 当前最大高度（只增不减）
        self.padding = 500  # 边距留白
        self.batch_loading = False  # 批量加载模式标志

        # 设置初始画布范围
        self.setSceneRect(self.scene_origin_x, self.scene_origin_y, 
                         self.current_max_width, self.current_max_height)

        # 设置背景网格
        self.setBackgroundBrush(QBrush(QColor(230, 230, 230)))
        self.grid_size = 20

    def drawBackground(self, painter, rect):
        """绘制背景网格"""
        super().drawBackground(painter, rect)

        # 绘制网格
        painter.setPen(QPen(QColor(200, 200, 200), 1))

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
        # 使用场景的 itemsBoundingRect 方法获取所有项目的边界
        items_rect = self.itemsBoundingRect()
        
        if items_rect.isNull() or items_rect.isEmpty():
            # 没有元素时，使用最小尺寸
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
        
        # 只增大，不减小（起点可以左移/上移，尺寸只能增大）
        actual_origin_x = min(self.scene_origin_x, new_origin_x)
        actual_origin_y = min(self.scene_origin_y, new_origin_y)
        
        # 重新计算宽度和高度（考虑起点可能的变化）
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
            
            # 更新场景矩形
            self.setSceneRect(self.scene_origin_x, self.scene_origin_y,
                            self.current_max_width, self.current_max_height)
            
            # 调试信息
            print(f"画布更新: origin=({self.scene_origin_x:.0f}, {self.scene_origin_y:.0f}), "
                  f"size=({self.current_max_width:.0f} x {self.current_max_height:.0f})")
    
    def addItem(self, item):
        """重写addItem方法，在添加元素后更新画布大小"""
        super().addItem(item)
        # 如果添加的是FlowchartItem，且不在批量加载模式下，更新画布大小
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
            connection_point.update()  # 强制更新显示
            print(f"开始连接: {connection_point.point_type}")
            print(f"连接点颜色已设置为蓝色，强制更新显示")
        else:
            # 结束连接
            end_connection = connection_point

            # 检查是否连接到同一元素
            if self.start_connection.parent_item == end_connection.parent_item:
                QMessageBox.warning(None, "错误", "不能连接同一元素的连接点")
                self.start_connection.setBrush(QBrush(Qt.GlobalColor.red))
                self.start_connection.update()  # 强制更新显示
                self.start_connection = None
                print(f"连接无效：同一元素，连接点颜色已设置为红色，强制更新显示")
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
                # 对于判断结构，允许从左点、右点、下点连接到上点
                if start_point_type in ['left', 'right', 'down']:
                    valid = True
            # 其他连接规则
            elif (start_point_type in ['left', 'right']) and end_point_type == 'up':
                valid = True

            # 调试：打印连接规则检查结果
            print(f"\n=== 连接规则检查 ===")
            print(f"连接类型: {start_point_type} → {end_point_type}")
            print(f"终点元素类型: {end_item_type}")
            print(f"连接是否有效: {valid}")

            if not valid:
                QMessageBox.warning(None, "错误", f"不允许的连接方式: {start_point_type} → {end_point_type}")
                self.start_connection.setBrush(QBrush(Qt.GlobalColor.red))
                self.start_connection.update()  # 强制更新显示
                self.start_connection = None
                print(f"连接无效：不允许的连接方式，连接点颜色已设置为红色，强制更新显示")
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

            # 调试：打印连接创建信息
            print(f"\n=== 连接创建成功 ===")
            print(f"起始元素: {self.start_connection.parent_item}")
            print(f"起始点类型: {start_point_type}")
            print(f"结束元素: {end_connection.parent_item}")
            print(f"结束点类型: {end_point_type}")
            print(f"连接对象: {connection}")
            print(f"当前连接数量: {len(self.connections)}")
            print(f"场景中的项目数量: {len(self.items())}")

            # 重置起始连接点
            self.start_connection.setBrush(QBrush(Qt.GlobalColor.red))
            self.start_connection = None
            print(f"连接创建完成，已重置起始连接点")

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        item = self.itemAt(event.scenePos(), QTransform())

        # 调试：打印鼠标点击信息
        print(f"\n=== 鼠标按下事件 ===")
        print(f"点击位置: {event.scenePos()}")
        print(f"点击的项目类型: {item.__class__.__name__ if item else 'None'}")

        if item:
            print(f"项目信息: {item}")
            # 如果是连接点，打印更多信息
            if isinstance(item, ConnectionPoint):
                print(f"连接点类型: {item.point_type}")
                print(f"连接点位置: {item.scenePos()}")
                print(f"连接点父元素: {item.parent_item}")
                print(f"连接点可选择: {item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable}")
            # 如果是FlowchartItem，打印连接点信息
            elif isinstance(item, FlowchartItem):
                print(f"流程图元素类型: {item.item_type}")
                print(f"元素位置: {item.scenePos()}")
                print(f"元素连接点: {item.connection_points.keys()}")

        # 移除原有的ConnectionPoint处理逻辑，避免重复处理

        super().mousePressEvent(event)

    def clear(self):
        """清空场景"""
        super().clear()
        self.connections.clear()
        self.start_connection = None
        
        # 重置画布大小为初始最小尺寸
        self.current_max_width = self.min_width
        self.current_max_height = self.min_height
        self.setSceneRect(self.scene_origin_x, self.scene_origin_y,
                         self.current_max_width, self.current_max_height)


class FlowchartView(QGraphicsView):
    """流程图视图"""

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # 支持缩放
        self.scale_factor = 1.0

    def wheelEvent(self, event):
        """滚轮事件，支持缩放"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 缩放因子
            zoom_in_factor = 1.25
            zoom_out_factor = 0.8

            # 获取鼠标位置
            mouse_pos = event.position()
            scene_pos = self.mapToScene(mouse_pos.toPoint())

            # 保存当前视图中心
            self.centerOn(scene_pos)

            # 缩放
            if event.angleDelta().y() > 0:
                # 放大
                self.scale(zoom_in_factor, zoom_in_factor)
                self.scale_factor *= zoom_in_factor
            else:
                # 缩小
                if self.scale_factor > 0.2:  # 最小缩放限制
                    self.scale(zoom_out_factor, zoom_out_factor)
                    self.scale_factor *= zoom_out_factor

            # 恢复视图中心
            self.centerOn(scene_pos)
            event.accept()
        else:
            super().wheelEvent(event)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("流程图工具")
        self.setGeometry(100, 100, 1200, 800)

        # ========== 可配置的提示文本（在这里修改） ==========
        # 提示信息（支持多行，粗体显示）
        self.tip_text = "💡 提示：\n1.将C++代码放入Cfile.cpp文件中，点击「从代码导入」即可自动生成流程图\n2.使用Ctrl+滚轮缩放画布\n3.点击红色点作为连线起点，再点击另一个点作为连线终点"
        
        # 开源地址（支持HTML链接）
        self.repo_text = '🔗 程序免费开源地址：<a href="https://github.com/PengZhangSDF/AutoC_to_flowchart">https://github.com/PengZhangSDF/AutoC_to_flowchart</a>'
        # ===================================================

        # 创建场景和视图
        self.scene = FlowchartScene()
        self.view = FlowchartView(self.scene)

        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()  # 修改为水平布局，以便添加右侧工具栏
        main_widget.setLayout(main_layout)

        # 创建左侧布局（包含工具栏和视图）
        left_layout = QVBoxLayout()

        # 创建顶部工具栏
        toolbar = QHBoxLayout()
        left_layout.addLayout(toolbar)

        # 添加按钮
        self.add_button(toolbar, "添加开始/结束模块", lambda: self.add_flowchart_item('start'))
        self.add_button(toolbar, "添加处理/语句模块", lambda: self.add_flowchart_item('process'))
        self.add_button(toolbar, "添加判断/循环模块", lambda: self.add_flowchart_item('decision'))
        self.add_button(toolbar, "添加输入/输出模块", lambda: self.add_flowchart_item('input'))
        self.add_button(toolbar, "保存为文件", self.save_flowchart)
        self.add_button(toolbar, "从保存的文件打开", self.load_flowchart)
        self.add_button(toolbar, "清空界面所有元素", self.clear_scene)

        left_layout.addWidget(self.view)
        main_layout.addLayout(left_layout, 3)  # 左侧占3/4宽度

        # 创建右侧工具栏
        self.create_right_toolbar(main_layout)

        self.setCentralWidget(main_widget)

        # 创建菜单
        self.create_menus()

        # 连接选择变化信号
        self.scene.selectionChanged.connect(self.on_selection_changed)

    def add_button(self, layout, text, callback):
        """添加按钮"""
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)

    def create_menus(self):
        """创建菜单"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_flowchart)
        file_menu.addAction(save_action)

        open_action = QAction("打开", self)
        open_action.triggered.connect(self.load_flowchart)
        file_menu.addAction(open_action)

        clear_action = QAction("清空", self)
        clear_action.triggered.connect(self.clear_scene)
        file_menu.addAction(clear_action)

    def create_right_toolbar(self, main_layout):
        """创建右侧工具栏"""
        # 创建右侧工具栏容器
        right_toolbar = QWidget()
        right_toolbar.setFixedWidth(250)
        right_toolbar.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-left: 1px solid #cccccc;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                margin: 10px 0 5px 10px;
            }
            QTextEdit {
                margin: 0 10px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                margin: 10px;
                padding: 5px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        # 创建垂直布局
        layout = QVBoxLayout(right_toolbar)

        # 添加元素信息
        self.element_type_label = QLabel("类型: -")
        layout.addWidget(self.element_type_label)

        # 添加文本编辑区域
        self.text_label = QLabel("文本编辑:")
        layout.addWidget(self.text_label)


        self.text_edit = QTextEdit()
        self.text_edit.setDisabled(True)  # 默认禁用
        # 连接文本变化信号，实现实时更新
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)

        # 添加导出按钮（放大，突出显示）
        export_label = QLabel("导出:")
        layout.addWidget(export_label)

        self.export_button = QPushButton("导出为图片")
        self.export_button.clicked.connect(self.export_to_image)
        # 设置放大的按钮样式
        self.export_button.setStyleSheet("""
            QPushButton {
                margin: 10px;
                padding: 10px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        layout.addWidget(self.export_button)

        # 添加从代码导入按钮（与导出按钮形状相同）
        self.import_button = QPushButton("从代码导入")
        self.import_button.clicked.connect(self.import_from_code)
        # 设置相同的按钮样式
        self.import_button.setStyleSheet("""
            QPushButton {
                margin: 10px;
                padding: 10px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        layout.addWidget(self.import_button)

        # 添加提示信息标签（粗体）
        self.tip_label = QLabel(self.tip_text)
        self.tip_label.setWordWrap(True)  # 自动换行
        self.tip_label.setStyleSheet("""
            QLabel {
                margin: 10px;
                padding: 10px;
                background-color: #FFF3CD;
                color: #856404;
                border: 1px solid #FFE69C;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.tip_label)

        # 添加开源地址标签
        self.repo_label = QLabel(self.repo_text)
        self.repo_label.setWordWrap(True)  # 自动换行
        self.repo_label.setOpenExternalLinks(True)  # 允许点击链接
        self.repo_label.setStyleSheet("""
            QLabel {
                margin: 10px;
                padding: 10px;
                background-color: #E7F3FF;
                color: #004085;
                border: 1px solid #B8DAFF;
                border-radius: 4px;
                font-size: 12px;
            }
            QLabel a {
                color: #0066CC;
                text-decoration: none;
            }
        """)
        layout.addWidget(self.repo_label)

        # 添加垂直拉伸
        layout.addStretch()

        # 将右侧工具栏添加到主布局
        main_layout.addWidget(right_toolbar, 1)

    def add_flowchart_item(self, item_type):
        """添加流程图元素"""
        # 在视图中心位置添加元素
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        # 调整位置，考虑到增大后的尺寸
        item = FlowchartItem(item_type, view_center.x() - 62.5, view_center.y() - 37.5)
        self.scene.addItem(item)

        # 选中新添加的元素
        item.setSelected(True)

    def save_flowchart(self):
        """保存流程图"""
        try:
            from io_operations import save_flowchart
            save_flowchart(self.scene, self)
        except ImportError as e:
            print(f"导入保存功能失败: {e}")
            import traceback
            traceback.print_exc()

    def load_flowchart(self):
        """加载流程图"""
        try:
            from io_operations import load_flowchart
            load_flowchart(self.scene, self)
        except ImportError as e:
            print(f"导入加载功能失败: {e}")
            import traceback
            traceback.print_exc()

    def clear_scene(self):
        """清空场景"""
        self.scene.clear()

    def export_to_image(self):
        """导出流程图为图片 - 创建临时场景副本，不包含连接点，修复边界计算和渲染问题"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QGraphicsView
        from PyQt6.QtGui import QPixmap, QImage, QPainter
        from PyQt6.QtCore import QRectF, QPoint, Qt, QSize

        # 获取场景中所有元素（跳过连接点）
        items = []
        for item in self.scene.items():
            if not isinstance(item, ConnectionPoint):
                items.append(item)

        if not items:
            QMessageBox.warning(self, "警告", "场景中没有元素可导出")
            return

        # 计算包含所有元素的边界矩形
        # 初始化边界值为第一个元素的边界
        first_item_rect = items[0].sceneBoundingRect()
        min_x = first_item_rect.left()
        max_x = first_item_rect.right()
        min_y = first_item_rect.top()
        max_y = first_item_rect.bottom()

        # 扩展边界以包含所有元素
        for item in items[1:]:
            rect = item.sceneBoundingRect()
            min_x = min(min_x, rect.left())
            max_x = max(max_x, rect.right())
            min_y = min(min_y, rect.top())
            max_y = max(max_y, rect.bottom())

        # 添加足够的边距
        margin = 30
        export_rect = QRectF(
            min_x - margin,
            min_y - margin,
            max_x - min_x + 2 * margin,
            max_y - min_y + 2 * margin
        )

        # 确保最小尺寸
        min_width = 500
        min_height = 400
        if export_rect.width() < min_width:
            center_x = export_rect.center().x()
            export_rect.setWidth(min_width)
            export_rect.moveCenter(QPointF(center_x, export_rect.center().y()))

        if export_rect.height() < min_height:
            center_y = export_rect.center().y()
            export_rect.setHeight(min_height)
            export_rect.moveCenter(QPointF(export_rect.center().x(), center_y))

        try:
            # 创建一个全新的场景，而不是使用FlowchartScene，避免网格背景问题
            from PyQt6.QtWidgets import QGraphicsScene
            temp_scene = QGraphicsScene()
            temp_scene.setBackgroundBrush(Qt.GlobalColor.white)  # 确保白色背景
            temp_view = QGraphicsView(temp_scene)

            # 设置视图属性
            temp_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            temp_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            temp_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            temp_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            temp_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

            # 复制所有元素到临时场景
            item_map = {}  # 用于映射原元素到副本

            for item in self.scene.items():
                # 跳过连接点
                if isinstance(item, ConnectionPoint):
                    continue

                # 复制FlowchartItem
                if hasattr(item, 'item_type'):  # 检查是否是FlowchartItem
                    # 创建新的FlowchartItem
                    # 计算相对于导出区域的位置，确保元素在正确的位置
                    relative_x = item.x() - export_rect.left()  # 相对于导出区域左侧
                    relative_y = item.y() - export_rect.top()   # 相对于导出区域顶部

                    temp_item = FlowchartItem(
                        item.item_type,
                        relative_x,
                        relative_y,
                        item.width,
                        item.height
                    )
                    # 设置文本
                    temp_item.setText(item.text)

                    # 隐藏连接点
                    for point in temp_item.connection_points.values():
                        point.setVisible(False)

                    temp_scene.addItem(temp_item)
                    item_map[item] = temp_item

            # 复制所有连接线
            for connection in self.scene.connections:
                # 确保起始和结束元素都已复制
                if connection.start_item in item_map and connection.end_item in item_map:
                    temp_connection = ConnectionLine(
                        item_map[connection.start_item],
                        connection.start_point_type,
                        item_map[connection.end_item],
                        connection.end_point_type
                    )
                    # 复制标签
                    temp_connection.label = getattr(connection, 'label', None)
                    
                    # 先添加连接到场景
                    temp_scene.addItem(temp_connection)
                    temp_scene.connections = getattr(temp_scene, 'connections', []) + [temp_connection]
                    
                    # 更新路径
                    temp_connection.update_path()
                    
                    # 创建并设置标签
                    if temp_connection.label:
                        temp_connection.create_label()
                        # 确保标签位置正确
                        temp_connection.update_label_position()
                        # 确保标签被添加到场景
                        if temp_connection.label_item and temp_connection.label_item.scene() is None:
                            temp_scene.addItem(temp_connection.label_item)

            # 设置视图大小以适应导出区域
            temp_scene.setSceneRect(0, 0, export_rect.width(), export_rect.height())
            temp_view.resize(int(export_rect.width()), int(export_rect.height()))
            temp_view.setScene(temp_scene)

            # 创建图像，确保尺寸足够大
            image = QImage(
                int(export_rect.width()),
                int(export_rect.height()),
                QImage.Format.Format_RGB32
            )
            image.fill(Qt.GlobalColor.white)  # 确保白色背景

            # 渲染临时场景，使用正确的渲染区域
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            temp_scene.render(painter)  # 直接渲染场景，而不是视图
            painter.end()

            # 显示保存文件对话框
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self,
                "导出为图片",
                "C流程图.png",
                "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;All Files (*)"
            )

            if not file_path:
                return

            # 确保文件扩展名为.png或.jpg
            if not (file_path.endswith(".png") or file_path.endswith(".jpg") or file_path.endswith(".jpeg")):
                file_path += ".png"

            # 保存图像
            if image.save(file_path):
                QMessageBox.information(self, "成功", f"流程图已成功导出到:\n{file_path}")
            else:
                QMessageBox.warning(self, "失败", "导出图片失败")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出图片时发生错误:\n{str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # 清理临时对象
            del temp_view
            del temp_scene

    def on_selection_changed(self):
        """处理选择变化事件"""
        selected_items = self.scene.selectedItems()

        # 调试：打印选中的项目信息
        print(f"\n=== 选择变化事件 ===")
        print(f"选中的项目数量: {len(selected_items)}")

        for i, item in enumerate(selected_items):
            print(f"\n项目 {i+1}:")
            print(f"  类型: {item.__class__.__name__}")
            print(f"  ID: {getattr(item, 'id', '无ID')}")
            print(f"  是FlowchartItem实例: {isinstance(item, FlowchartItem)}")

            # 如果是FlowchartItem，打印更多信息
            if isinstance(item, FlowchartItem):
                print(f"  item_type属性: {item.item_type}")
                print(f"  text_item: {item.text_item}")
                if item.text_item:
                    print(f"  文本内容: '{item.text_item.toPlainText()}'")

        # 过滤出FlowchartItem（使用类型名称检查作为备选）
        flowchart_items = []
        for item in selected_items:
            if isinstance(item, FlowchartItem) or item.__class__.__name__ == "FlowchartItem":
                flowchart_items.append(item)

        if flowchart_items:
            # 只处理第一个选中的FlowchartItem
            selected_item = flowchart_items[0]

            # 启用文本编辑控件
            self.text_edit.setDisabled(False)

            # 设置文本内容
            # 暂时断开信号连接，避免触发不必要的更新
            self.text_edit.textChanged.disconnect(self.on_text_changed)
            self.text_edit.setPlainText(selected_item.text_item.toPlainText())
            # 重新连接信号
            self.text_edit.textChanged.connect(self.on_text_changed)

            # 更新元素信息
            item_type_name = ITEM_TYPES.get(selected_item.item_type, {}).get('name', selected_item.item_type)
            self.element_type_label.setText(f"类型: {item_type_name}")

            print(f"\n✓ 成功更新右侧工具栏")
            print(f"  元素类型: {item_type_name}")
            print(f"  文本内容: '{selected_item.text_item.toPlainText()}'")
        else:
            # 没有选中FlowchartItem，禁用文本编辑控件
            self.text_edit.setDisabled(True)
            self.text_edit.clear()
            self.element_type_label.setText("类型: -")

            print(f"\n✗ 没有选中FlowchartItem")

    def on_text_changed(self):
        """处理文本变化事件，实现实时更新"""
        selected_items = self.scene.selectedItems()

        # 过滤出FlowchartItem（使用类型名称检查作为备选）
        flowchart_items = []
        for item in selected_items:
            if isinstance(item, FlowchartItem) or item.__class__.__name__ == "FlowchartItem":
                flowchart_items.append(item)

        if flowchart_items:
            selected_item = flowchart_items[0]
            new_text = self.text_edit.toPlainText()

            # 更新元素文本
            selected_item.text_item.setPlainText(new_text)
            selected_item.text = new_text
            selected_item.update_text_position()

            # 可选：打印调试信息
            # print(f"实时更新元素文本: {new_text}")

    def import_from_code(self):
        """从代码导入流程图（由用户实现）"""
        from code_to_flowchart_refactored import main
        result = main()
        if not result:
            return
        try:
            from io_operations import load_flowchart
            load_flowchart(self.scene, self,"output_flowchart.json")
        except ImportError as e:
            print(f"导入加载功能失败: {e}")
            import traceback
            traceback.print_exc()

        pass


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
