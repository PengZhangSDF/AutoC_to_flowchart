"""
主窗口类
"""
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QFileDialog, QMessageBox, QGraphicsView)
from PyQt6.QtGui import QAction, QImage, QPainter, QPixmap
from PyQt6.QtCore import Qt, QRectF, QPointF

from GUI.items import ITEM_TYPES, FlowchartItem, ConnectionPoint, ConnectionLine
from GUI.scene import FlowchartScene
from GUI.view import FlowchartView


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("流程图工具")
        self.setGeometry(100, 100, 1200, 800)

        # 可配置的提示文本
        self.tip_text = "💡 提示：\n1.点击「从代码导入」选择C/C++文件即可自动生成流程图\n2.使用Ctrl+滚轮缩放画布\n3.点击红色点作为连线起点，再点击另一个点作为连线终点"
        self.repo_text = '🔗 程序免费开源地址：<a href="https://github.com/PengZhangSDF/AutoC_to_flowchart">https://github.com/PengZhangSDF/AutoC_to_flowchart</a>'

        # 创建场景和视图
        self.scene = FlowchartScene()
        self.view = FlowchartView(self.scene)

        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # 创建左侧布局
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
        main_layout.addLayout(left_layout, 3)

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

        layout = QVBoxLayout(right_toolbar)

        # 元素信息
        self.element_type_label = QLabel("类型: -")
        layout.addWidget(self.element_type_label)

        # 文本编辑区域
        self.text_label = QLabel("文本编辑:")
        layout.addWidget(self.text_label)

        self.text_edit = QTextEdit()
        self.text_edit.setDisabled(True)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)

        # 导出按钮
        export_label = QLabel("导出:")
        layout.addWidget(export_label)

        self.export_button = QPushButton("导出为图片")
        self.export_button.clicked.connect(self.export_to_image)
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

        # 从代码导入按钮
        self.import_button = QPushButton("从代码导入")
        self.import_button.clicked.connect(self.import_from_code)
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

        # 提示信息标签
        self.tip_label = QLabel(self.tip_text)
        self.tip_label.setWordWrap(True)
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

        # 开源地址标签
        self.repo_label = QLabel(self.repo_text)
        self.repo_label.setWordWrap(True)
        self.repo_label.setOpenExternalLinks(True)
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

        layout.addStretch()
        main_layout.addWidget(right_toolbar, 1)

    def add_flowchart_item(self, item_type):
        """添加流程图元素"""
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        item = FlowchartItem(item_type, view_center.x() - 62.5, view_center.y() - 37.5)
        self.scene.addItem(item)
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
        """导出流程图为图片"""
        from PyQt6.QtWidgets import QGraphicsScene

        # 获取场景中所有元素（跳过连接点）
        items = []
        for item in self.scene.items():
            if not isinstance(item, ConnectionPoint):
                items.append(item)

        if not items:
            QMessageBox.warning(self, "警告", "场景中没有元素可导出")
            return

        # 计算包含所有元素的边界矩形
        first_item_rect = items[0].sceneBoundingRect()
        min_x = first_item_rect.left()
        max_x = first_item_rect.right()
        min_y = first_item_rect.top()
        max_y = first_item_rect.bottom()

        for item in items[1:]:
            rect = item.sceneBoundingRect()
            min_x = min(min_x, rect.left())
            max_x = max(max_x, rect.right())
            min_y = min(min_y, rect.top())
            max_y = max(max_y, rect.bottom())

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
            # 创建临时场景
            temp_scene = QGraphicsScene()
            temp_scene.setBackgroundBrush(Qt.GlobalColor.white)
            temp_view = QGraphicsView(temp_scene)

            temp_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            temp_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            temp_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            temp_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            temp_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

            # 复制所有元素到临时场景
            item_map = {}

            for item in self.scene.items():
                if isinstance(item, ConnectionPoint):
                    continue

                if hasattr(item, 'item_type'):
                    relative_x = item.x() - export_rect.left()
                    relative_y = item.y() - export_rect.top()

                    temp_item = FlowchartItem(
                        item.item_type,
                        relative_x,
                        relative_y,
                        item.width,
                        item.height
                    )
                    temp_item.setText(item.text)

                    for point in temp_item.connection_points.values():
                        point.setVisible(False)

                    temp_scene.addItem(temp_item)
                    item_map[item] = temp_item

            # 复制所有连接线
            for connection in self.scene.connections:
                if connection.start_item in item_map and connection.end_item in item_map:
                    temp_connection = ConnectionLine(
                        item_map[connection.start_item],
                        connection.start_point_type,
                        item_map[connection.end_item],
                        connection.end_point_type
                    )
                    temp_connection.label = getattr(connection, 'label', None)
                    
                    temp_scene.addItem(temp_connection)
                    temp_scene.connections = getattr(temp_scene, 'connections', []) + [temp_connection]
                    
                    temp_connection.update_path()
                    
                    if temp_connection.label:
                        temp_connection.create_label()
                        temp_connection.update_label_position()
                        if temp_connection.label_item and temp_connection.label_item.scene() is None:
                            temp_scene.addItem(temp_connection.label_item)

            # 设置视图大小
            temp_scene.setSceneRect(0, 0, export_rect.width(), export_rect.height())
            temp_view.resize(int(export_rect.width()), int(export_rect.height()))
            temp_view.setScene(temp_scene)

            # 创建图像
            image = QImage(
                int(export_rect.width()),
                int(export_rect.height()),
                QImage.Format.Format_RGB32
            )
            image.fill(Qt.GlobalColor.white)

            # 渲染临时场景
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            temp_scene.render(painter)
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

            if not (file_path.endswith(".png") or file_path.endswith(".jpg") or file_path.endswith(".jpeg")):
                file_path += ".png"

            if image.save(file_path):
                QMessageBox.information(self, "成功", f"流程图已成功导出到:\n{file_path}")
            else:
                QMessageBox.warning(self, "失败", "导出图片失败")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出图片时发生错误:\n{str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            del temp_view
            del temp_scene

    def on_selection_changed(self):
        """处理选择变化事件"""
        selected_items = self.scene.selectedItems()

        print(f"\n=== 选择变化事件 ===")
        print(f"选中的项目数量: {len(selected_items)}")

        flowchart_items = []
        for item in selected_items:
            if isinstance(item, FlowchartItem) or item.__class__.__name__ == "FlowchartItem":
                flowchart_items.append(item)

        if flowchart_items:
            selected_item = flowchart_items[0]

            self.text_edit.setDisabled(False)

            self.text_edit.textChanged.disconnect(self.on_text_changed)
            self.text_edit.setPlainText(selected_item.text_item.toPlainText())
            self.text_edit.textChanged.connect(self.on_text_changed)

            item_type_name = ITEM_TYPES.get(selected_item.item_type, {}).get('name', selected_item.item_type)
            self.element_type_label.setText(f"类型: {item_type_name}")

            print(f"\n✓ 成功更新右侧工具栏")
        else:
            self.text_edit.setDisabled(True)
            self.text_edit.clear()
            self.element_type_label.setText("类型: -")

            print(f"\n✗ 没有选中FlowchartItem")

    def on_text_changed(self):
        """处理文本变化事件，实时更新"""
        selected_items = self.scene.selectedItems()

        flowchart_items = []
        for item in selected_items:
            if isinstance(item, FlowchartItem) or item.__class__.__name__ == "FlowchartItem":
                flowchart_items.append(item)

        if flowchart_items:
            selected_item = flowchart_items[0]
            new_text = self.text_edit.toPlainText()

            selected_item.text_item.setPlainText(new_text)
            selected_item.text = new_text
            selected_item.update_text_position()

    def import_from_code(self):
        """从代码导入流程图"""
        from code_to_flowchart_refactored import main
        result = main()
        if not result:
            return
        try:
            from io_operations import load_flowchart
            load_flowchart(self.scene, self, "output_flowchart.json")
        except ImportError as e:
            print(f"导入加载功能失败: {e}")
            import traceback
            traceback.print_exc()

