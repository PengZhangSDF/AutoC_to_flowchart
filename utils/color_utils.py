"""颜色工具函数"""

from typing import Dict, List, Optional

from PyQt6.QtGui import QColor


COLOR_PRESETS: Dict[str, List[int]] = {
    "柔和灰": [240, 240, 240],
    "纯白": [255, 255, 255],
    "浅灰": [230, 230, 230],
    "深灰": [200, 200, 200],
    "天空蓝": [200, 230, 255],
    "浅蓝": [220, 235, 255],
    "薄荷绿": [220, 255, 235],
    "淡粉": [255, 230, 240],
    "浅黄": [255, 247, 220],
    "浅紫": [235, 220, 255]
}


def normalize_color(value, default: Optional[List[int]] = None) -> List[int]:
    """将各种格式的颜色值转换为 RGB 列表"""
    if default is None:
        default = [255, 255, 255]

    if isinstance(value, list) and len(value) == 3:
        return [int(v) for v in value]

    if isinstance(value, QColor):
        return [value.red(), value.green(), value.blue()]

    if isinstance(value, str):
        preset = COLOR_PRESETS.get(value.strip())
        if preset:
            return preset

        # 尝试解析 "r,g,b" 字符串
        parts = value.split(',')
        if len(parts) == 3:
            try:
                return [int(p.strip()) for p in parts]
            except ValueError:
                pass

    return default


def to_qcolor(value, default: Optional[List[int]] = None) -> QColor:
    """转换为 QColor"""
    rgb = normalize_color(value, default)
    return QColor(*rgb)


def find_color_name(rgb_list: List[int]) -> Optional[str]:
    """根据 RGB 列表查找预设名称"""
    target = [int(v) for v in rgb_list]
    for name, rgb in COLOR_PRESETS.items():
        if rgb == target:
            return name
    return None


def get_palette_names() -> List[str]:
    """返回所有预设颜色名称"""
    return list(COLOR_PRESETS.keys())


def get_palette_color(name: str) -> List[int]:
    """根据名称获取颜色 RGB"""
    return COLOR_PRESETS.get(name, [255, 255, 255])

