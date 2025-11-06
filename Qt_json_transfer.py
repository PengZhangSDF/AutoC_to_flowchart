import json
import logging
# 移除重复的logging导入以避免冲突
from logger import logger, print_to_log as print

# 配置调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[DEBUG] %(message)s'
)
logger = logging.getLogger(__name__)


def is_else_node(node):
    """判断是否为else节点（tag=branch且内容为else/否则）"""
    if node.get('tag') != 'branch':
        return False
    original_unit = node.get('original_unit', '').lower()
    translated = node.get('translated', '').lower()
    return 'else' in original_unit or '否则' in translated


def process_node(node, depth, offset, used_offsets, result):
    """递归处理节点：剔除branch类型的else节点（否则），保留其子语句"""
    if not isinstance(node, dict):
        logger.debug(f"跳过非字典节点: {node}")
        return

    # 1. 关键修复：处理tag=branch的else节点（显示为"否则"的节点）
    if is_else_node(node):
        logger.debug(f"不生成'否则'节点本身，开始处理其下的子语句")
        # 提取else节点的子语句，直接处理（不生成该"否则"节点）
        children = [c for c in node.get('children', []) if isinstance(c, dict)]
        current_child_depth = depth  # 子语句深度由调用方控制（按规则应为if深度+1）
        current_child_offset = offset
        for child in children:
            process_node(child, current_child_depth, current_child_offset, used_offsets, result)
            current_child_depth += 1
        return  # 不生成"否则"节点，直接返回

    tag = node.get('tag')
    if tag is None:
        block_type = node.get('type')
        # 处理else_block（即使无tag，也按规则保留子语句）
        if block_type == 'else_block':
            logger.debug(f"处理else_block子语句，不生成块节点")
            children = [c for c in node.get('children', []) if isinstance(c, dict)]
            current_child_depth = depth
            current_child_offset = offset
            for child in children:
                process_node(child, current_child_depth, current_child_offset, used_offsets, result)
                current_child_depth += 1
            return
        # 处理正常块节点（for_block/if_block）
        elif block_type in ['for_block', 'if_block']:
            logger.debug(f"处理块节点: type={block_type}")
            children = [c for c in node.get('children', []) if isinstance(c, dict)]
            current_child_depth = depth
            current_child_offset = offset
            for child in children:
                process_node(child, current_child_depth, current_child_offset, used_offsets, result)
                current_child_depth += 1
            return
        else:
            logger.debug(f"跳过无'tag'且非目标块的节点: {node.keys()}")
            return

    logger.debug(f"\n处理节点: tag={tag}, depth={depth}, offset={offset}")
    logger.debug(f"节点内容: {json.dumps(node, ensure_ascii=False, indent=1)[:200]}...")

    # 跳过block类型节点（{}符号）
    if tag == 'block':
        logger.debug(f"跳过block节点")
        return

    # 2. 确定节点形状
    original_unit = node.get('original_unit', '')
    if tag == 'i/o':
        shape = 'Parallelogram'
    elif tag in ['branch', 'if', 'loop', 'while']:
        shape = 'Rhombus'
        logger.debug(f"识别为分支/循环节点，形状设为菱形")
    elif 'return' in original_unit:
        shape = 'special'
    else:
        shape = 'rectangle'

    # 3. 确定节点文本（排除else节点，已在前面处理）
    if tag in ['branch', 'if']:
        text = node.get('translated', '条件判断')
    elif tag in ['loop', 'while']:
        text = node.get('translated', '循环')
    elif 'return' in original_unit:
        text = '结束'
    else:
        text = node.get('translated', '')

    # 4. 记录节点位置（仅生成非else节点）
    position = f"{depth}_{offset}"
    result.append({
        'position': position,
        'shape': shape,
        'text': text
    })
    logger.debug(f"添加节点: position={position}, shape={shape}, text={text}")

    # 记录当前深度已使用的偏移
    if depth not in used_offsets:
        used_offsets[depth] = set()
    used_offsets[depth].add(offset)

    # 5. 处理子节点（分支位置规则+循环内无偏移）
    children = node.get('children', [])
    children = [c for c in children if isinstance(c, dict)]
    logger.debug(f"过滤后子节点数量: {len(children)}")

    # 分支节点（branch/if）处理：区分if和else分支（else已在前面处理）
    if tag in ['branch', 'if']:
        for block in children:
            block_type = block.get('type')
            # 处理if_block：子语句同深度横向偏移+1（如if在1_0→子语句1_1）
            if block_type == 'if_block':
                logger.debug(f"处理if_block子语句，同深度横向偏移")
                base_child_depth = depth
                base_offset = offset + 1
                # 冲突处理
                while base_offset in used_offsets.get(base_child_depth, set()):
                    base_offset = offset - 1 if base_offset > offset else offset + 2
                logger.debug(f"if子语句位置: depth={base_child_depth}, offset={base_offset}")
                process_node(block, base_child_depth, base_offset, used_offsets, result)

            # 处理else_block：子语句深度+1、同父偏移（如if在1_0→else子语句2_0）
            elif block_type == 'else_block':
                logger.debug(f"处理else_block子语句，深度+1、同父偏移")
                base_child_depth = depth + 1
                base_offset = offset
                logger.debug(f"else子语句位置: depth={base_child_depth}, offset={base_offset}")
                process_node(block, base_child_depth, base_offset, used_offsets, result)

    # 循环节点（loop/while）处理：子节点无横向偏移
    elif tag in ['loop', 'while']:
        logger.debug(f"处理循环子节点，无横向偏移")
        base_child_depth = depth + 1
        base_offset = offset  # 与循环同偏移，无横向偏移
        for child in children:
            process_node(child, base_child_depth, base_offset, used_offsets, result)

    # 普通节点处理：竖直向下
    else:
        current_child_depth = depth + 1
        child_offset = offset
        for child in children:
            process_node(child, current_child_depth, child_offset, used_offsets, result)
            current_child_depth += 1


def main():
    try:
        with open('output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.debug(f"\n===== 原始数据加载完成 =====")
        logger.debug(f"原始节点总数: {len(data)}")
        # 重点检查是否有tag=branch且内容为else/否则的节点
        for i, node in enumerate(data[:5]):
            if isinstance(node, dict):
                is_else = is_else_node(node)
                logger.debug(
                    f"原始节点{i}: tag={node.get('tag')}, translated={node.get('translated')}, 是否为else节点: {is_else}")
            else:
                logger.debug(f"原始节点{i}不是字典: {type(node)}")

        filtered_nodes = [node for node in data if isinstance(node, dict)]
        logger.debug(f"过滤后有效顶级节点数: {len(filtered_nodes)}")

        qt_nodes = []
        used_offsets = {}
        current_depth = 1

        for node in filtered_nodes:
            logger.debug(f"\n===== 开始处理顶级节点 =====")
            process_node(node, current_depth, 0, used_offsets, qt_nodes)
            current_depth += 1

        with open('Qt.json', 'w', encoding='utf-8') as f:
            json.dump(qt_nodes, f, ensure_ascii=False, indent=2)

        logger.debug(f"\n===== 处理完成 =====")
        logger.debug(f"生成的Qt节点数: {len(qt_nodes)}")
        logger.debug(f"生成的节点文本列表: {[n['text'] for n in qt_nodes]}")  # 重点检查是否有"否则"

    except Exception as e:
        logger.error(f"处理出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("程序开始运行")
    logger.info(main())
    logger.info("程序运行结束")
