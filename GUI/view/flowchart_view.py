"""
流程图视图类
"""
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt


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

