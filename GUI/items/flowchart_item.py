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
        
        # 用于防止多选拖动时的递归调用
        self._is_moving_with_group = False
        # 记录拖动开始时的位置（用于多选拖动）
        self._drag_start_position = None

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
        # 根据选中状态设置边框颜色
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 100, 255), 3))  # 选中时蓝色边框，稍粗
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 2))  # 未选中时黑色边框

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
        # 如果当前元素未被选中，先选中它
        if not self.isSelected():
            scene = self.scene()
            if scene:
                # 取消所有其他元素的选择
                for item in scene.selectedItems():
                    item.setSelected(False)
            self.setSelected(True)
        self.show_context_menu(event.screenPos())

    def show_context_menu(self, global_pos):
        """显示右键菜单"""
        menu = QMenu()
        scene = self.scene()
        
        # 获取所有选中的FlowchartItem
        selected_items = []
        if scene:
            for item in scene.selectedItems():
                if isinstance(item, FlowchartItem):
                    selected_items.append(item)
        
        # 根据选中数量显示不同的菜单文本
        if len(selected_items) > 1:
            delete_action = menu.addAction(f"删除选中项 ({len(selected_items)}个)")
        else:
            delete_action = menu.addAction("删除")
        
        action = menu.exec(global_pos)

        if action == delete_action:
            if scene:
                # 删除所有选中项的相关连接
                items_to_remove = selected_items if len(selected_items) > 1 else [self]
                connections_to_remove = []
                
                for item in items_to_remove:
                    for connection in scene.connections:
                        if connection.start_item == item or connection.end_item == item:
                            if connection not in connections_to_remove:
                                connections_to_remove.append(connection)

                # 删除连接
                for connection in connections_to_remove:
                    # 先删除标签，避免残留
                    if hasattr(connection, "remove_label"):
                        connection.remove_label()
                    scene.removeItem(connection)
                    if connection in scene.connections:
                        scene.connections.remove(connection)

                # 删除所有选中的元素
                for item in items_to_remove:
                    scene.removeItem(item)

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

            scene = self.scene()
            was_selected = self.isSelected()
            
            # 如果按住Ctrl键，切换当前元素的选择状态（多选模式）
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # 切换当前元素的选择状态
                self.setSelected(not self.isSelected())
            else:
                # 如果没有按住Ctrl键
                if not was_selected:
                    # 如果当前元素未选中，取消其他选择并选中当前元素
                    if scene:
                        # 取消所有其他元素的选择
                        for item in scene.selectedItems():
                            if item != self:
                                item.setSelected(False)
                    # 选中当前元素
                    self.setSelected(True)
                # 如果当前元素已选中，场景会处理保持多选状态
            
            self.drag_start_pos = event.pos()
            
            # 记录所有选中项的初始位置（用于多选拖动）
            if scene and self.isSelected():
                selected_items = [item for item in scene.selectedItems() 
                                 if isinstance(item, FlowchartItem)]
                for item in selected_items:
                    item._drag_start_position = item.pos()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        # 清除拖动起始位置记录
        scene = self.scene()
        if scene:
            selected_items = [item for item in scene.selectedItems() 
                             if isinstance(item, FlowchartItem)]
            for item in selected_items:
                item._drag_start_position = None
        super().mouseReleaseEvent(event)
    
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
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            # 选中状态改变时，更新显示（触发重绘）
            self.update()
        
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 如果是拖动操作，检查是否有其他选中的项需要一起移动
            # 避免递归调用
            if not self._is_moving_with_group and self._drag_start_position is not None:
                scene = self.scene()
                if scene and self.isSelected():
                    selected_items = [item for item in scene.selectedItems() 
                                     if isinstance(item, FlowchartItem) and item != self]
                    
                    if selected_items:
                        # 计算位置偏移（使用记录的初始位置）
                        new_pos = value
                        old_pos = self._drag_start_position
                        offset = new_pos - old_pos
                        
                        # 移动所有其他选中的项（设置标志避免递归）
                        for item in selected_items:
                            if item._drag_start_position is not None:
                                item._is_moving_with_group = True
                                item.setPos(item._drag_start_position + offset)
                                item._is_moving_with_group = False
        
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

