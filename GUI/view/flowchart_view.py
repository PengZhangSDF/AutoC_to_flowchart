"""
流程图视图类
"""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsRectItem
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtWidgets import QGraphicsItem
from utils.config_manager import get_config

from GUI.items import FlowchartItem


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
        
        # 框选相关变量
        self.rubber_band_rect = None
        self.rubber_band_item = None
        self.is_rubber_banding = False
        self.rubber_band_start = None

    def wheelEvent(self, event):
        """滚轮事件，支持缩放"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 从配置文件加载缩放因子
            zoom_in_factor = get_config('view', 'zoom', 'in_factor', default=1.25)
            zoom_out_factor = get_config('view', 'zoom', 'out_factor', default=0.8)
            min_scale = get_config('view', 'zoom', 'min_scale', default=0.2)

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
                if self.scale_factor > min_scale:
                    self.scale(zoom_out_factor, zoom_out_factor)
                    self.scale_factor *= zoom_out_factor

            # 恢复视图中心
            self.centerOn(scene_pos)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        # 如果按住Ctrl键且是左键，开始框选
        if (event.button() == Qt.MouseButton.LeftButton and 
            event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            # 检查是否点击在连接点上，如果点击在连接点上，不进行框选
            item = self.itemAt(event.pos())
            from GUI.items import ConnectionPoint
            
            # 如果点击在连接点上，交给连接点处理，不进行框选
            if item and isinstance(item, ConnectionPoint):
                super().mousePressEvent(event)
                return
            
            # 切换到框选模式
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.is_rubber_banding = True
            self.rubber_band_start = event.pos()
            
            # 清除之前的选择
            scene = self.scene()
            if scene:
                for item in scene.selectedItems():
                    item.setSelected(False)
            
            # 创建框选矩形项
            if self.rubber_band_item:
                self.scene().removeItem(self.rubber_band_item)
            
            self.rubber_band_item = QGraphicsRectItem()
            self.rubber_band_item.setPen(QPen(QColor(100, 150, 255), 2, Qt.PenStyle.DashLine))
            self.rubber_band_item.setBrush(QBrush(QColor(100, 150, 255, 50)))
            self.rubber_band_item.setZValue(-1)  # 确保在底层
            self.rubber_band_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            self.scene().addItem(self.rubber_band_item)
            
            event.accept()
            return  # 阻止事件进一步传播，避免元素被选中
        else:
            # 正常模式
            self.is_rubber_banding = False
            if self.rubber_band_item:
                self.scene().removeItem(self.rubber_band_item)
                self.rubber_band_item = None
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_rubber_banding and self.rubber_band_start:
            # 更新框选矩形
            current_pos = event.pos()
            start_scene = self.mapToScene(self.rubber_band_start)
            current_scene = self.mapToScene(current_pos)
            
            rect = QRectF(start_scene, current_scene).normalized()
            self.rubber_band_item.setRect(rect)
            
            # 更新选中项
            self._update_selection_from_rubber_band(rect)
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self.is_rubber_banding:
            self.is_rubber_banding = False
            
            # 清理框选矩形
            if self.rubber_band_item:
                self.scene().removeItem(self.rubber_band_item)
                self.rubber_band_item = None
            
            # 恢复拖拽模式
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.rubber_band_start = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def _update_selection_from_rubber_band(self, rect):
        """根据框选矩形更新选中项"""
        scene = self.scene()
        if not scene:
            return
        
        # 先清除所有选择
        for item in scene.selectedItems():
            if isinstance(item, FlowchartItem):
                item.setSelected(False)
        
        # 获取框选矩形内的所有FlowchartItem并选中
        for item in scene.items():
            if isinstance(item, FlowchartItem):
                item_rect = item.sceneBoundingRect()
                # 检查元素是否与框选矩形有交集
                # 使用更宽松的条件：只要元素与框选矩形有交集就选中
                if rect.intersects(item_rect):
                    item.setSelected(True)

