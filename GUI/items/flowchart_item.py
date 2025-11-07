"""
流程图元素类
"""
import uuid
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QMenu, QApplication
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainterPath
from PyQt6.QtCore import Qt, QRectF

from .constants import CONNECTION_POINTS
from .connection_point import ConnectionPoint
from utils.config_manager import get_config
from utils.color_utils import to_qcolor


class FlowchartItem(QGraphicsItem):
    """流程图元素基类"""

    def __init__(self, item_type, x, y, width=125, height=75):
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
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)

        # 创建连接点
        self.connection_points = {}
        for point_type in CONNECTION_POINTS:
            point = ConnectionPoint(self, point_type)
            self.connection_points[point_type] = point
            point.setAcceptHoverEvents(True)

        # 创建文本元素
        font_family = get_config('text', 'font_family', default='Arial')
        font_size = get_config('text', 'font_size', default=12)
        
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.text_item.setFont(QFont(font_family, font_size))
        self.text_item.setHtml('<div align="center">' + self.text + '</div>')
        self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

        # 连接文本变化信号
        self.text_item.document().contentsChanged.connect(self.update_text_position)

        self.update_connection_points()
        self.update_text_position()

    def boundingRect(self):
        """重定义边界矩形"""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """绘制流程图元素"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))

        colors_config = get_config('item', 'colors', default={}) or {}
        fill_color_value = colors_config.get(self.item_type, colors_config.get('default', [240, 240, 240]))
        painter.setBrush(QBrush(to_qcolor(fill_color_value, [240, 240, 240])))

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

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        self.show_context_menu(event.screenPos())

    def show_context_menu(self, global_pos):
        """显示右键菜单"""
        menu = QMenu()
        delete_action = menu.addAction("删除")
        action = menu.exec(global_pos)

        if action == delete_action:
            scene = self.scene()
            if scene:
                # 删除相关连接
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
            text_margin = get_config('text', 'text_margin', default=10)
            double_margin = text_margin * 2
            
            item_rect = self.boundingRect()
            text_width = item_rect.width() - double_margin
            text_height = item_rect.height() - double_margin

            self.text_item.setTextWidth(text_width)
            text_rect = self.text_item.boundingRect()

            # 计算居中位置
            text_x = (item_rect.width() - text_rect.width()) / 2
            text_y = (item_rect.height() - text_rect.height()) / 2

            # 确保文本在元素内部
            if text_y < text_margin:
                text_y = text_margin
            elif text_y + text_rect.height() > item_rect.height() - text_margin:
                text_y = item_rect.height() - text_margin - text_rect.height()

            self.text_item.setPos(text_x, text_y)

    def setText(self, text):
        """设置文本"""
        self.text = text
        # HTML转义
        escaped_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        self.text_item.setHtml('<div align="center">' + escaped_text + '</div>')
        self.update_text_position()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在连接点上
            pos = event.pos()
            for point in self.connection_points.values():
                if point.contains(pos):
                    return

            # 选中元素
            self.setSelected(True)
            self.drag_start_pos = event.pos()

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSelected(True)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        """失去焦点事件"""
        self.text = self.text_item.toPlainText()
        self.text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().focusOutEvent(event)

    def sceneEventFilter(self, watched, event):
        """事件过滤器"""
        if watched == self.text_item:
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                new_event = type(event)(
                    event.type(),
                    self.mapFromScene(event.scenePos()),
                    event.button(),
                    event.buttons(),
                    event.modifiers()
                )
                QApplication.postEvent(self, new_event)
                return True

        return super().sceneEventFilter(watched, event)

    def itemChange(self, change, value):
        """处理项目变化"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.update_connection_points()
            scene = self.scene()
            if scene and hasattr(scene, 'connections'):
                for connection in scene.connections:
                    if connection.start_item == self or connection.end_item == self:
                        connection.update_path()
                # 更新画布大小
                if hasattr(scene, 'update_scene_bounds'):
                    scene.update_scene_bounds()
        return super().itemChange(change, value)

