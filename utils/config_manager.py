"""
配置管理器 - 读取和管理 config.yaml 配置文件
"""
import os
import yaml
from pathlib import Path
from logger.logger import logger


class ConfigManager:
    """配置管理器单例类"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
        
        if not config_path.exists():
            print(f"警告：配置文件 {config_path} 不存在，使用默认配置")
            self._config = self._get_default_config()
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            print(f"✓ 成功加载配置文件: {config_path}")
        except Exception as e:
            print(f"警告：加载配置文件失败 ({e})，使用默认配置")
            self._config = self._get_default_config()
    
    def _get_default_config(self):
        """获取默认配置（如果配置文件不存在）"""
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
            'parser': {
                'multi_function': False
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
            'layout': {
                'function_offset_x': 250
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
    
    def get(self, *keys, default=None):
        """
        获取配置值
        
        Args:
            *keys: 配置键路径，例如 get('scene', 'origin_x')
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def reload(self):
        """重新加载配置文件"""
        self.load_config()

    def update_in_memory(self, data):
        """使用提供的数据更新内存中的配置副本"""
        self._config = data

    def set_value(self, keys, value):
        """更新配置并写回文件"""
        logger.info(f"[ConfigManager] set_value keys={keys}, value={value}")
        if not isinstance(keys, (list, tuple)) or not keys:
            raise ValueError("keys 应该是非空的列表或元组")

        if self._config is None:
            self._config = self._get_default_config()

        current = self._config
        for key in keys[:-1]:
            if not isinstance(current, dict):
                return False
            child = current.get(key)
            if not isinstance(child, dict):
                current[key] = {}
            current = current[key]

        if not isinstance(current, dict):
            return False
        current[keys[-1]] = value

        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info(f"[ConfigManager] 已写入 {config_path}, 当前parser.multi_function={self._config.get('parser', {}).get('multi_function')}")

        return True


# 创建全局配置实例
config = ConfigManager()


# 便捷函数
def get_config(*keys, default=None):
    """获取配置值的便捷函数"""
    return config.get(*keys, default=default)


def set_config_value(keys, value):
    """设置配置值的便捷函数"""
    return config.set_value(keys, value)

