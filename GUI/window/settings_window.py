"""
设置窗口类
"""
import yaml
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QWidget, QLabel, QLineEdit, QPushButton, QMessageBox,
                             QFormLayout, QGroupBox, QScrollArea, QSpinBox, QDoubleSpinBox,
                             QComboBox, QCheckBox)
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import Qt

from GUI.items import FlowchartItem
from utils.color_utils import COLOR_PRESETS, normalize_color, find_color_name, to_qcolor
from utils.config_manager import config as global_config

class SettingsWindow(QDialog):
    """设置窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setGeometry(200, 200, 700, 600)
        self.setModal(True)  # 模态窗口
        
        self.config_path = Path(__file__).parent.parent.parent / "config.yaml"
        self.config_data = {}
        self.input_widgets = {}  # 存储所有输入控件
        self.color_defaults = {}
        self.custom_color_entries = {}
        
        # 加载配置
        self.load_config()
        
        # 创建UI
        self.init_ui()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载配置文件失败：{e}")
            self.config_data = {}
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建选项卡
        tabs = QTabWidget()
        
        # 创建各个配置页面
        tabs.addTab(self.create_scene_tab(), "🖼️ 画布场景")
        tabs.addTab(self.create_item_tab(), "📦 流程图元素")
        tabs.addTab(self.create_connection_tab(), "🔗 连接线")
        tabs.addTab(self.create_view_tab(), "👁️ 视图")
        tabs.addTab(self.create_export_tab(), "💾 导出")
        tabs.addTab(self.create_text_tab(), "📝 文本")
        tabs.addTab(self.create_parser_tab(), "⚙️ 解析")
        tabs.addTab(self.create_about_tab(), "ℹ️ 关于我们")
        
        layout.addWidget(tabs)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #999;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_scene_tab(self):
        """创建画布场景配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 画布尺寸组
        size_group = QGroupBox("画布尺寸")
        size_layout = QFormLayout()
        
        self.add_int_input(size_layout, "起点 X 坐标:", 'scene', 'origin_x')
        self.add_int_input(size_layout, "起点 Y 坐标:", 'scene', 'origin_y')
        self.add_int_input(size_layout, "最小宽度:", 'scene', 'min_width')
        self.add_int_input(size_layout, "最小高度:", 'scene', 'min_height')
        self.add_int_input(size_layout, "边距留白:", 'scene', 'padding')
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 网格组
        grid_group = QGroupBox("背景网格")
        grid_layout = QFormLayout()
        
        self.add_int_input(grid_layout, "网格大小:", 'scene', 'grid_size')
        self.add_color_combo(grid_layout, "背景颜色:", [230, 230, 230], 'scene', 'background_color')
        self.add_color_combo(grid_layout, "网格颜色:", [200, 200, 200], 'scene', 'grid_color')
        
        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)
        
        layout.addStretch()
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container
    
    def create_item_tab(self):
        """创建流程图元素配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 元素尺寸组
        size_group = QGroupBox("元素默认尺寸")
        size_layout = QFormLayout()
        
        self.add_int_input(size_layout, "默认宽度:", 'item', 'default_width')
        self.add_int_input(size_layout, "默认高度:", 'item', 'default_height')
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 连接点组
        point_group = QGroupBox("连接点参数")
        point_layout = QFormLayout()
        
        self.add_int_input(point_layout, "显示半径:", 'item', 'connection_point', 'radius')
        self.add_int_input(point_layout, "点击判定半径:", 'item', 'connection_point', 'hit_radius')
        self.add_int_input(point_layout, "图层高度:", 'item', 'connection_point', 'z_value')
        
        point_group.setLayout(point_layout)
        layout.addWidget(point_group)
        
        # 元素颜色组
        color_group = QGroupBox("元素颜色")
        color_layout = QFormLayout()

        self.add_color_combo(color_layout, "默认颜色:", [240, 240, 240], 'item', 'colors', 'default')
        self.add_color_combo(color_layout, "开始节点:", [240, 240, 240], 'item', 'colors', 'start')
        self.add_color_combo(color_layout, "结束节点:", [240, 240, 240], 'item', 'colors', 'end')
        self.add_color_combo(color_layout, "输入/输出:", [240, 240, 240], 'item', 'colors', 'input')
        self.add_color_combo(color_layout, "处理语句:", [240, 240, 240], 'item', 'colors', 'process')
        self.add_color_combo(color_layout, "判断/循环:", [240, 240, 240], 'item', 'colors', 'decision')

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        layout.addStretch()
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container
    
    def create_connection_tab(self):
        """创建连接线配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 箭头组
        arrow_group = QGroupBox("箭头设置")
        arrow_layout = QFormLayout()
        self.add_int_input(arrow_layout, "箭头大小:", 'connection', 'arrow', 'size')
        arrow_group.setLayout(arrow_layout)
        layout.addWidget(arrow_group)
        
        # 线条组
        line_group = QGroupBox("线条设置")
        line_layout = QFormLayout()
        self.add_int_input(line_layout, "线条宽度:", 'connection', 'line', 'width')
        self.add_int_input(line_layout, "图层高度:", 'connection', 'line', 'z_value')
        line_group.setLayout(line_layout)
        layout.addWidget(line_group)
        
        # 路径偏移量组
        offset_group = QGroupBox("路径偏移量")
        offset_layout = QFormLayout()
        
        # down_to_up
        self.add_int_input(offset_layout, "down→up 中点偏移:", 'connection', 'path_offsets', 'down_to_up', 'mid_offset')
        
        # up_to_down
        self.add_int_input(offset_layout, "up→down 下偏移:", 'connection', 'path_offsets', 'up_to_down', 'down_offset')
        self.add_float_input(offset_layout, "up→down 横向比例:", 'connection', 'path_offsets', 'up_to_down', 'horizontal_ratio')
        self.add_int_input(offset_layout, "up→down 中点偏移:", 'connection', 'path_offsets', 'up_to_down', 'mid_offset')
        
        # horizontal_loop
        self.add_int_input(offset_layout, "横向循环偏移:", 'connection', 'path_offsets', 'horizontal_loop', 'offset')
        
        # right_to_up
        self.add_int_input(offset_layout, "right→up 基础间距:", 'connection', 'path_offsets', 'right_to_up', 'base_spacing')
        self.add_int_input(offset_layout, "right→up 动态间距:", 'connection', 'path_offsets', 'right_to_up', 'dynamic_spacing')
        self.add_int_input(offset_layout, "right→up 额外上距:", 'connection', 'path_offsets', 'right_to_up', 'extra_up_distance')
        
        # left_to_up
        self.add_int_input(offset_layout, "left→up 横向偏移:", 'connection', 'path_offsets', 'left_to_up', 'horizontal_offset')
        self.add_int_input(offset_layout, "left→up 额外上距:", 'connection', 'path_offsets', 'left_to_up', 'extra_up_distance')
        
        # decision_loop
        self.add_int_input(offset_layout, "判断循环横向偏移:", 'connection', 'path_offsets', 'decision_loop', 'horizontal_offset')
        self.add_int_input(offset_layout, "判断循环中点偏移:", 'connection', 'path_offsets', 'decision_loop', 'mid_offset')
        
        offset_group.setLayout(offset_layout)
        layout.addWidget(offset_group)
        
        layout.addStretch()
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container
    
    def create_view_tab(self):
        """创建视图配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        # 缩放组
        zoom_group = QGroupBox("缩放设置")
        zoom_layout = QFormLayout()
        
        self.add_float_input(zoom_layout, "放大倍数:", 'view', 'zoom', 'in_factor')
        self.add_float_input(zoom_layout, "缩小倍数:", 'view', 'zoom', 'out_factor')
        self.add_float_input(zoom_layout, "最小缩放:", 'view', 'zoom', 'min_scale')
        
        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)
        
        layout.addStretch()
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container
    
    def create_export_tab(self):
        """创建导出配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        export_group = QGroupBox("导出设置")
        export_layout = QFormLayout()
        
        self.add_text_input(export_layout, "默认文件名:", 'export', 'default_filename')
        self.add_int_input(export_layout, "导出边距:", 'export', 'margin')
        self.add_int_input(export_layout, "最小宽度:", 'export', 'min_width')
        self.add_int_input(export_layout, "最小高度:", 'export', 'min_height')
        self.add_color_combo(export_layout, "背景颜色:", [255, 255, 255], 'export', 'background_color')
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container
    
    def create_text_tab(self):
        """创建文本配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        
        layout = QVBoxLayout(widget)
        
        text_group = QGroupBox("文本设置")
        text_layout = QFormLayout()
        
        self.add_text_input(text_layout, "字体名称:", 'text', 'font_family')
        self.add_int_input(text_layout, "字体大小:", 'text', 'font_size')
        self.add_int_input(text_layout, "文本边距:", 'text', 'text_margin')
        self.add_int_input(text_layout, "标签字体大小:", 'text', 'label_font_size')
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        layout.addStretch()
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container

    def create_parser_tab(self):
        """创建解析/函数配置页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        layout = QVBoxLayout(widget)

        parser_group = QGroupBox("函数解析")
        parser_layout = QFormLayout()
        self.add_bool_input(parser_layout, "启用多函数识别:", 'parser', 'multi_function')
        parser_group.setLayout(parser_layout)
        layout.addWidget(parser_group)

        layout_group = QGroupBox("函数布局")
        layout_form = QFormLayout()
        self.add_int_input(layout_form, "函数水平间距:", 'layout', 'function_offset_x')
        layout_group.setLayout(layout_form)
        layout.addWidget(layout_group)

        layout.addStretch()

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container

    def create_about_tab(self):
        """创建关于我们页面"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        layout = QVBoxLayout(widget)

        tips_config = self.config_data.get('tips', {}) or {}
        tip_text = tips_config.get('tip_text', '')
        repo_url = tips_config.get('repo_url', '')
        repo_prefix = tips_config.get('repo_text', '')

        if tip_text:
            tip_label = QLabel(tip_text)
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet("""
                QLabel {
                    margin: 12px;
                    padding: 12px;
                    background-color: #FFF3CD;
                    color: #856404;
                    border: 1px solid #FFE69C;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
            layout.addWidget(tip_label)

        if repo_url:
            repo_label = QLabel(f"{repo_prefix}<a href=\"{repo_url}\">{repo_url}</a>")
            repo_label.setWordWrap(True)
            repo_label.setOpenExternalLinks(True)
            repo_label.setStyleSheet("""
                QLabel {
                    margin: 12px;
                    padding: 12px;
                    background-color: #E7F3FF;
                    color: #004085;
                    border: 1px solid #B8DAFF;
                    border-radius: 6px;
                    font-size: 12px;
                }
                QLabel a {
                    color: #0066CC;
                    text-decoration: none;
                }
            """)
            layout.addWidget(repo_label)

        layout.addStretch()

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll)
        return container
    
    def add_int_input(self, layout, label, *keys):
        """添加整数输入框"""
        value = self.get_nested_value(self.config_data, keys)
        
        spinbox = QSpinBox()
        spinbox.setRange(-100000, 100000)
        spinbox.setValue(int(value) if value is not None else 0)
        spinbox.setMinimumWidth(150)
        
        # 实时保存
        spinbox.valueChanged.connect(lambda: self.save_value(keys, spinbox.value()))
        
        layout.addRow(label, spinbox)
        self.input_widgets[keys] = spinbox
    
    def add_float_input(self, layout, label, *keys):
        """添加浮点数输入框"""
        value = self.get_nested_value(self.config_data, keys)
        
        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.01, 100.0)
        spinbox.setSingleStep(0.05)
        spinbox.setDecimals(2)
        spinbox.setValue(float(value) if value is not None else 1.0)
        spinbox.setMinimumWidth(150)
        
        # 实时保存
        spinbox.valueChanged.connect(lambda: self.save_value(keys, spinbox.value()))
        
        layout.addRow(label, spinbox)
        self.input_widgets[keys] = spinbox
    
    def add_text_input(self, layout, label, *keys):
        """添加文本输入框"""
        value = self.get_nested_value(self.config_data, keys)
        
        line_edit = QLineEdit()
        line_edit.setText(str(value) if value is not None else "")
        line_edit.setMinimumWidth(200)
        
        # 失去焦点时保存
        line_edit.editingFinished.connect(lambda: self.save_value(keys, line_edit.text()))
        
        layout.addRow(label, line_edit)
        self.input_widgets[keys] = line_edit
    
    def add_bool_input(self, layout, label, *keys):
        """添加布尔开关"""
        value = self.get_nested_value(self.config_data, keys)
        checkbox = QCheckBox()
        checkbox.setChecked(bool(value))

        def on_state_changed(state):
            checked_state = Qt.CheckState(state)
            self.save_value(keys, checked_state == Qt.CheckState.Checked)

        checkbox.stateChanged.connect(on_state_changed)
        layout.addRow(label, checkbox)
        self.input_widgets[keys] = checkbox

    def add_color_combo(self, layout, label, default_rgb, *keys):
        """添加颜色选择下拉框"""
        combo = QComboBox()
        combo.setMinimumWidth(220)

        for name, rgb in COLOR_PRESETS.items():
            combo.addItem(name, tuple(rgb))

        value = self.get_nested_value(self.config_data, keys)
        self.color_defaults[keys] = list(default_rgb)

        combo.blockSignals(True)
        self.set_color_combo_value(combo, keys, value if value is not None else default_rgb, default_rgb)
        combo.blockSignals(False)

        combo.currentIndexChanged.connect(lambda _: self.on_color_combo_changed(combo, keys))

        layout.addRow(label, combo)
        self.input_widgets[keys] = combo

    def set_color_combo_value(self, combo, keys, value, default_rgb):
        """根据配置值更新颜色下拉框"""
        rgb = normalize_color(value, default_rgb)
        color_name = find_color_name(rgb)

        if color_name is not None:
            index = combo.findText(color_name)
            if index != -1:
                combo.setCurrentIndex(index)
                return

        data_tuple = tuple(rgb)
        if keys in self.custom_color_entries:
            custom_index = self.custom_color_entries[keys]
            if custom_index >= combo.count():
                combo.addItem(f"自定义 ({rgb[0]},{rgb[1]},{rgb[2]})", data_tuple)
                custom_index = combo.count() - 1
                self.custom_color_entries[keys] = custom_index
            else:
                combo.setItemText(custom_index, f"自定义 ({rgb[0]},{rgb[1]},{rgb[2]})")
                combo.setItemData(custom_index, data_tuple)
        else:
            combo.addItem(f"自定义 ({rgb[0]},{rgb[1]},{rgb[2]})", data_tuple)
            custom_index = combo.count() - 1
            self.custom_color_entries[keys] = custom_index

        combo.setCurrentIndex(self.custom_color_entries[keys])

    def on_color_combo_changed(self, combo, keys):
        """颜色下拉框变更事件"""
        data = combo.currentData()
        if data is None:
            return

        rgb_list = [int(v) for v in data]
        self.save_value(keys, rgb_list)
        self.apply_runtime_change(keys, rgb_list)

    def apply_runtime_change(self, keys, value):
        """根据键路径应用实时效果"""
        parent = self.parent()
        if parent is None:
            return

        scene = getattr(parent, 'scene', None)
        if scene is None:
            return

        if len(keys) >= 2 and keys[0] == 'scene':
            if keys[1] == 'background_color':
                scene.background_color = to_qcolor(value, [230, 230, 230])
                scene.setBackgroundBrush(QBrush(scene.background_color))
                scene.update()
            elif keys[1] == 'grid_color':
                rgb = normalize_color(value, [200, 200, 200])
                scene.grid_color = rgb
                scene.grid_qcolor = QColor(*rgb)
                scene.update()
        elif len(keys) >= 2 and keys[0] == 'item' and keys[1] == 'colors':
            from GUI.items import FlowchartItem
            for item in scene.items():
                if isinstance(item, FlowchartItem):
                    item.update()
    
    def get_nested_value(self, data, keys):
        """获取嵌套字典的值"""
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def set_nested_value(self, data, keys, value):
        """设置嵌套字典的值"""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def save_value(self, keys, value):
        """保存单个值到配置并立即写入文件"""
        self.set_nested_value(self.config_data, keys, value)
        self.write_config_to_file()
        global_config.update_in_memory(self.config_data)
        if keys == ('parser', 'multi_function'):
            parent = self.parent()
            from logger.logger import logger
            logger.info(f"[设置窗口] 保存多函数识别: {value}")
            if parent and hasattr(parent, 'set_multi_function_enabled'):
                parent.set_multi_function_enabled(bool(value), persist=False)

    def write_config_to_file(self):
        """将配置写入YAML文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"保存配置失败：{e}")
    
    def save_settings(self):
        """保存所有设置"""
        try:
            # 配置已经实时保存了，这里只需要提示
            QMessageBox.information(self, "成功", "设置已保存！\n重启程序后生效。")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败：{e}")
    
    def reset_to_defaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self, 
            "确认", 
            "确定要恢复所有默认设置吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 恢复默认配置
            self.config_data = self.get_default_config()
            self.write_config_to_file()
            global_config.update_in_memory(self.config_data)
            
            # 刷新所有输入框
            self.refresh_all_inputs()
            self.apply_runtime_color_updates()
            
            QMessageBox.information(self, "成功", "已恢复默认设置！\n重启程序后生效。")

    def apply_runtime_color_updates(self):
        """根据当前配置批量刷新颜色相关设置"""
        scene_config = self.config_data.get('scene', {})
        if 'background_color' in scene_config:
            self.apply_runtime_change(('scene', 'background_color'), scene_config['background_color'])
        if 'grid_color' in scene_config:
            self.apply_runtime_change(('scene', 'grid_color'), scene_config['grid_color'])

        item_config = self.config_data.get('item', {})
        color_config = item_config.get('colors', {})
        if color_config:
            for key, value in color_config.items():
                self.apply_runtime_change(('item', 'colors', key), value)
    
    def refresh_all_inputs(self):
        """刷新所有输入框的值"""
        for keys, widget in self.input_widgets.items():
            value = self.get_nested_value(self.config_data, keys)
            
            if isinstance(widget, QSpinBox):
                widget.setValue(int(value) if value is not None else 0)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value) if value is not None else 0.0)
            elif isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(bool(value))
                widget.blockSignals(False)
            elif isinstance(widget, QComboBox):
                default_rgb = self.color_defaults.get(keys, [255, 255, 255])
                widget.blockSignals(True)
                self.set_color_combo_value(widget, keys, value if value is not None else default_rgb, default_rgb)
                widget.blockSignals(False)
            elif isinstance(widget, QLineEdit):
                if isinstance(value, list):  # 颜色值
                    widget.setText(f"{value[0]},{value[1]},{value[2]}")
                else:
                    widget.setText(str(value) if value is not None else "")
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            'window': {
                'title': '流程图工具',
                'width': 1200,
                'height': 800,
                'x': 100,
                'y': 100
            },
            'scene': {
                'origin_x': -5000,
                'origin_y': -5000,
                'min_width': 1000,
                'min_height': 1000,
                'padding': 500,
                'grid_size': 20,
                'background_color': [230, 230, 230],
                'grid_color': [200, 200, 200]
            },
            'item': {
                'default_width': 125,
                'default_height': 75,
                'connection_point': {
                    'radius': 5,
                    'hit_radius': 10,
                    'z_value': 10
                },
                'colors': {
                    'default': [240, 240, 240],
                    'start': [240, 240, 240],
                    'end': [240, 240, 240],
                    'input': [240, 240, 240],
                    'process': [240, 240, 240],
                    'decision': [240, 240, 240]
                }
            },
            'connection': {
                'arrow': {'size': 10},
                'line': {'width': 2, 'color': 'black', 'z_value': 5},
                'path_offsets': {
                    'down_to_up': {'mid_offset': 40},
                    'up_to_down': {'down_offset': 30, 'horizontal_ratio': 0.7, 'mid_offset': 40},
                    'horizontal_loop': {'offset': 50},
                    'right_to_up': {'base_spacing': 50, 'dynamic_spacing': 30, 'extra_up_distance': 20},
                    'left_to_up': {'horizontal_offset': 50, 'extra_up_distance': 20},
                    'decision_loop': {'horizontal_offset': 30, 'mid_offset': 40}
                }
            },
            'view': {
                'zoom': {'in_factor': 1.25, 'out_factor': 0.8, 'min_scale': 0.2},
                'drag_mode': 'scroll'
            },
            'export': {
                'default_filename': 'C流程图.png',
                'margin': 30,
                'min_width': 500,
                'min_height': 400,
                'background_color': [255, 255, 255]
            },
            'text': {
                'font_family': 'Arial',
                'font_size': 12,
                'text_margin': 10,
                'label_font_size': 12
            },
            'tips': {
                'tip_text': '💡 提示：\n1.点击「从代码导入」选择C/C++文件即可自动生成流程图\n2.使用Ctrl+滚轮缩放画布\n3.点击红色点作为连线起点，再点击另一个点作为连线终点',
                'repo_url': 'https://github.com/PengZhangSDF/AutoC_to_flowchart',
                'repo_text': '🔗 程序免费开源地址：'
            }
        }

