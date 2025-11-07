"""

重构后的code_to_flowchart入口文件

使用FlowchartCreateTool包来执行转换



这个文件保持了与原code_to_flowchart.py相同的接口，

但使用重构后的模块化架构。

"""

import json

import re

from copy import deepcopy



from FlowchartCreateTool import FlowchartConverter

from logger.logger import logger

from utils.config_manager import get_config





def main():

    """主函数：执行转换"""

    # 读取input.json文件

    from JSON_transfer import main as json_transfer_main

    result = json_transfer_main()

    if not result:

        return False

    

    input_file_path = './output.json'

    output_file_path = './output_flowchart.json'

    

    try:

        with open(input_file_path, 'r', encoding='utf-8') as f:

            input_json = json.load(f)

        

        multi_function_enabled = get_config('parser', 'multi_function', default=False)

        function_offset_x = get_config('layout', 'function_offset_x', default=450)



        def sanitize_suffix(name: str) -> str:

            if not name:

                return 'func'

            return re.sub(r'[^0-9A-Za-z_]+', '_', name)



        def add_suffix(output_data, suffix: str):

            suffix = sanitize_suffix(suffix)

            id_map = {}

            for node in output_data['items']:

                old_id = node['id']

                new_id = f"{old_id}_{suffix}"

                id_map[old_id] = new_id

                node['id'] = new_id

            for conn in output_data['connections']:

                if conn['start_item_id'] in id_map:

                    conn['start_item_id'] = id_map[conn['start_item_id']]

                if conn['end_item_id'] in id_map:

                    conn['end_item_id'] = id_map[conn['end_item_id']]



        def shift_positions(items, dx: float, dy: float):

            for node in items:

                node['x'] += dx

                node['y'] += dy



        def get_last_translated_text(nodes):

            def is_valid_translation(text_value: str) -> bool:

                if not text_value:

                    return False

                stripped = text_value.strip()

                if not stripped:

                    return False

                if stripped in {'{', '}', '开始', '结束'}:

                    return False

                return True



            for node in reversed(nodes):

                if not isinstance(node, dict):

                    continue

                if node.get('tag') == 'block':

                    continue

                translated = node.get('translated', '')

                original_unit = node.get('original_unit', '')

                if original_unit.startswith('function '):

                    continue

                if not is_valid_translation(translated):

                    continue

                stripped_translated = translated.strip()

                if stripped_translated.startswith('返回'):

                    return stripped_translated



            for node in reversed(nodes):

                if not isinstance(node, dict):

                    continue

                if node.get('tag') == 'block':

                    continue

                translated = node.get('translated', '')

                original_unit = node.get('original_unit', '')

                if original_unit.startswith('function '):

                    continue

                if not is_valid_translation(translated):

                    continue

                return translated.strip()



            return None



        def apply_end_node_policy(output_data, end_text):

            items = output_data.get('items', [])

            end_nodes = [node for node in items if node.get('type') == 'end']

            if not end_nodes:

                return



            keep_end = bool(end_text) and ('返回' in end_text or '杩斿洖' in end_text)

            if keep_end:

                end_nodes[0]['text'] = end_text

                return



            end_ids = {node.get('id') for node in end_nodes}

            output_data['items'] = [node for node in items if node.get('id') not in end_ids]

            output_data['connections'] = [

                conn for conn in output_data.get('connections', [])

                if conn.get('start_item_id') not in end_ids and conn.get('end_item_id') not in end_ids

            ]



        def compute_max_x(items):

            if not items:

                return -4600.0

            return max(node['x'] + node.get('width', 0) for node in items)



        def compute_min_x(items):

            if not items:

                return -4600.0

            return min(node['x'] for node in items)



        def find_start_y(items):

            for node in items:

                if node.get('type') == 'start':

                    return node.get('y', -4800.0)

            return -4800.0



        def convert_nodes(nodes):

            converter = FlowchartConverter()

            return converter.convert(deepcopy(nodes))



        if multi_function_enabled and isinstance(input_json, dict):

            main_nodes = input_json.get('main', []) or []

            other_functions = input_json.get('functions', []) or []



            aggregated_items = []

            aggregated_connections = []

            overall_max_x = -4600.0

            base_start_y = -4800.0



            if main_nodes:

                main_output = convert_nodes(main_nodes)
                apply_end_node_policy(main_output, get_last_translated_text(main_nodes))

                # 主函数保持默认结束节点

                aggregated_items = deepcopy(main_output['items'])

                aggregated_connections = deepcopy(main_output['connections'])

                overall_max_x = compute_max_x(aggregated_items)

                base_start_y = find_start_y(aggregated_items)

            else:

                aggregated_items = []

                aggregated_connections = []



            for index, func in enumerate(other_functions, start=1):

                func_nodes = func.get('nodes', [])

                if not func_nodes:

                    continue



                func_output = convert_nodes(func_nodes)
                apply_end_node_policy(func_output, get_last_translated_text(func_nodes))
                suffix = func.get('name') or f'func_{index}'
                add_suffix(func_output, suffix)



                func_items = func_output['items']

                func_connections = func_output['connections']



                if not func_items:

                    continue



                func_min_x = compute_min_x(func_items)

                target_start_x = overall_max_x + function_offset_x if aggregated_items else func_min_x

                dx = target_start_x - func_min_x



                func_start_y = find_start_y(func_items)

                target_start_y = base_start_y if aggregated_items else func_start_y

                dy = target_start_y - func_start_y



                shift_positions(func_items, dx, dy)



                had_existing_items = bool(aggregated_items)

                aggregated_items.extend(func_items)

                aggregated_connections.extend(func_connections)

                if not had_existing_items:

                    base_start_y = find_start_y(func_items)

                overall_max_x = compute_max_x(aggregated_items)



            output_json = {

                "version": "1.0",

                "items": aggregated_items,

                "connections": aggregated_connections

            }

        else:

            converter = FlowchartConverter()

            output_json = converter.convert(input_json)

        

        logger.debug(json.dumps(output_json, indent=2, ensure_ascii=False))

        

        # 保存到文件

        with open(output_file_path, 'w', encoding='utf-8') as f:

            json.dump(output_json, f, indent=2, ensure_ascii=False)

        

        logger.info(f"\n转换完成！结果已保存到: {output_file_path}")

    

    except FileNotFoundError:

        logger.error(f"错误：找不到文件 {input_file_path}")

        logger.error("请确保在目录下有output.json文件")

        return False

    

    except json.JSONDecodeError as e:

        logger.error(f"错误：JSON格式无效 - {e}")

        logger.error("请检查output.json文件的格式是否正确")

        return False

    

    except Exception as e:

        logger.error(f"转换过程中发生错误: {e}")

        import traceback

        traceback.print_exc()

        return False

    

    return True





if __name__ == "__main__":

    main()