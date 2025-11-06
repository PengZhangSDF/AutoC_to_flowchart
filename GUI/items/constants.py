"""
流程图元素常量定义
"""

# 流程图元素类型
ITEM_TYPES = {
    'start': {'name': '开始/结束', 'shape': 'oval'},
    'end': {'name': '开始/结束', 'shape': 'oval'},
    'input': {'name': '输入/输出', 'shape': 'parallelogram'},
    'process': {'name': '语句', 'shape': 'rectangle'},
    'decision': {'name': '判断/循环', 'shape': 'diamond'}
}

# 连接点位置
CONNECTION_POINTS = ['up', 'down', 'left', 'right']

