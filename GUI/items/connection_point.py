"""
流程图连接点类
"""
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QRectF
from logger.logger import logger
from utils.config_manager import get_config


class ConnectionPoint(QGraphicsEllipseItem):
    """连接点类"""

    def __init__(self, parent_item, point_type):
        super().__init__(parent_item)
        self.parent_item = parent_item
        self.point_type = point_type
        
        # 从配置文件加载连接点参数
        self.radius = get_config('item', 'connection_point', 'radius', default=5)
        self.hit_radius = get_config('item', 'connection_point', 'hit_radius', default=10)
        z_value = get_config('item', 'connection_point', 'z_value', default=10)
        
        self.setRect(-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        self.setBrush(QBrush(Qt.GlobalColor.red))
        self.setPen(QPen(Qt.GlobalColor.darkRed, 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(z_value)

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

