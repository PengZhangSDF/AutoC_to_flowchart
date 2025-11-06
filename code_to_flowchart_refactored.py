"""
重构后的code_to_flowchart入口文件
使用FlowchartCreateTool包来执行转换

这个文件保持了与原code_to_flowchart.py相同的接口，
但使用重构后的模块化架构。
"""
import json
from FlowchartCreateTool import FlowchartConverter
from logger import logger


def main():
    """主函数：执行转换"""
    # 读取input.json文件
    from JSON_transfer import main as json_transfer_main
    result = json_transfer_main()
    if not result:
        return False
    
    input_file_path = 'output.json'
    output_file_path = 'output_flowchart.json'
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            input_json = json.load(f)
        
        # 使用重构后的转换器
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

