"""
流程图视图类定义
"""
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTransform

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
        """处理鼠标滚轮事件（缩放）"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 缩放因子
            zoom_in_factor = 1.25
            zoom_out_factor = 0.8

            # 计算新的缩放因子
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            self.scale(zoom_factor, zoom_factor)
            self.scale_factor *= zoom_factor
            event.accept()
        else:
            super().wheelEvent(event)