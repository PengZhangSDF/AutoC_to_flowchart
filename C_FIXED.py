import re
import sys
import os
from logger.logger import logger

# 尝试导入tkinter，如果失败则设置一个标志
try:
    import tkinter as tk
    from tkinter import filedialog

    tkinter_available = True
except ImportError:
    tkinter_available = False


class CppCodeFormatter:
    def __init__(self):
        self.if_pattern = re.compile(r'^\s*if\s*\(.*?\)\s*$')  # 匹配单独一行的if(...)
        self.else_pattern = re.compile(r'^\s*else\s*$')  # 匹配单独一行的else
        self.single_line_if_pattern = re.compile(r'^\s*if\s*\(.*?\)\s*[^\{;]*;\s*$')  # 匹配单行if语句（如if (x) y;）
        self.single_line_for_pattern = re.compile(r'^\s*for\s*\(.*?\)\s*[^\{;]*;\s*$')  # 匹配单行for循环（如for (i=0; i<10; i++) x++;）
        self.single_line_while_pattern = re.compile(r'^\s*while\s*\(.*?\)\s*[^\{;]*;\s*$')  # 匹配单行while循环（如while (x>0) x--;）
        self.main_pattern = re.compile(r'^\s*(int\s+)?main\s*\(.*?\)\s*(\{)?')  # 匹配main函数声明
        self.return_pattern = re.compile(r'^\s*return\s+\d+\s*;')  # 匹配return语句
        self.in_string = False  # 跟踪字符串内状态
        self.in_main = False  # 跟踪是否在main函数内
        self.main_has_return = False  # 跟踪main函数是否有return语句

    def remove_unnecessary_spaces(self, line):
        """清理单行内的冗余空格，保留必要格式"""
        processed = []
        pos = 0
        n = len(line)
        while pos < n:
            c = line[pos]

            # 字符串内内容完全保留
            if c in ('"', "'"):
                processed.append(c)
                self.in_string = not self.in_string
                pos += 1
                while pos < n and line[pos] != c:
                    processed.append(line[pos])
                    pos += 1
                if pos < n:
                    processed.append(c)
                    self.in_string = not self.in_string
                pos += 1
                continue

            # 非字符串内：清理冗余空格
            if not self.in_string:
                if c == ' ' and pos + 1 < n and line[pos + 1] == ' ':
                    pos += 1
                    continue
                if c in '(){}' and pos + 1 < n and line[pos + 1] == ' ':
                    processed.append(c)
                    pos += 2
                    continue
                if c in '(){}' and pos > 0 and processed[-1] == ' ':
                    processed.pop()
                    processed.append(c)
                    pos += 1
                    continue

            processed.append(c)
            pos += 1

        result = ''.join(processed).strip()
        result = re.sub(r'if\(', 'if (', result)
        result = re.sub(r'for\(', 'for (', result)
        result = re.sub(r'while\(', 'while (', result)
        return result

    def process_single_line_control(self, line):
        """处理单行控制语句，确保执行部分被大括号包裹"""
        # 检查是否为单行控制语句且不在大括号内
        if '{' not in line:
            # 首先检查是否为for循环
            if 'for (' in line or 'for(' in line:
                # 找到循环条件的结束位置
                bracket_count = 0
                end_pos = -1
                for i, char in enumerate(line):
                    if char == '(':
                        bracket_count += 1
                    elif char == ')':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_pos = i
                            break
                
                if end_pos > 0 and ';' in line[end_pos+1:]:
                    # 提取循环条件和执行语句
                    condition = line[:end_pos + 1].strip()
                    statement_part = line[end_pos + 1:]
                    # 找到第一个分号的位置
                    semicolon_pos = statement_part.find(';')
                    if semicolon_pos >= 0:
                        statement = statement_part[:semicolon_pos].strip()
                        if statement:
                            # 返回带大括号的循环语句
                            return f"{condition} {{ {statement}; }}"
            
            # 检查是否为while循环
            elif 'while (' in line or 'while(' in line:
                # 找到循环条件的结束位置
                bracket_count = 0
                end_pos = -1
                for i, char in enumerate(line):
                    if char == '(':
                        bracket_count += 1
                    elif char == ')':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_pos = i
                            break
                
                if end_pos > 0 and ';' in line[end_pos+1:]:
                    # 提取循环条件和执行语句
                    condition = line[:end_pos + 1].strip()
                    statement_part = line[end_pos + 1:]
                    # 找到第一个分号的位置
                    semicolon_pos = statement_part.find(';')
                    if semicolon_pos >= 0:
                        statement = statement_part[:semicolon_pos].strip()
                        if statement:
                            # 返回带大括号的循环语句
                            return f"{condition} {{ {statement}; }}"
            
            # 检查是否为单行if语句
            elif self.single_line_if_pattern.match(line):
                # 提取条件和执行语句
                bracket_pos = line.find(')')
                if bracket_pos > 0:
                    condition = line[:bracket_pos + 1].strip()
                    # 提取执行语句
                    statement_part = line[bracket_pos + 1:]
                    if ';' in statement_part:
                        statement_end = statement_part.find(';')
                        statement = statement_part[:statement_end].strip()
                        if statement:
                            return f"{condition} {{ {statement}; }}"
        return line

    def process_multi_line_control(self, lines):
        """处理跨多行的if/else结构和循环结构（控制语句与主体分行）"""
        processed = []
        i = 0
        n = len(lines)
        
        # 添加for和while循环的正则表达式模式
        for_pattern = re.compile(r'^\s*for\s*\(.*?\)\s*$')  # 匹配单独一行的for(...)
        while_pattern = re.compile(r'^\s*while\s*\(.*?\)\s*$')  # 匹配单独一行的while(...)

        while i < n:
            line = lines[i].strip()
            if not line:
                processed.append(line)
                i += 1
                continue

            # 先处理单行控制语句
            processed_line = self.process_single_line_control(line)
            if processed_line != line:
                processed.append(processed_line)
                i += 1
                continue

            # 处理单独一行的if（下一行是主体）
            if self.if_pattern.match(line):
                # 确保有下一行作为主体
                if i + 1 < n:
                    next_line = lines[i + 1].strip()

                    # 检查下一行是否是大括号
                    if next_line == '{':
                        # 如果下一行是大括号，保持原有结构
                        processed.append(line)
                        processed.append(next_line)
                        i += 2
                    else:
                        # 否则将主体行与if语句合并
                        processed.append(f"{line} {{ {next_line} }}")
                        i += 2
                else:
                    # 异常：if无主体，仍加空括号
                    processed.append(f"{line} {{}}")
                    i += 1
                continue

            # 处理单独一行的else（下一行是主体）
            if self.else_pattern.match(line):
                if i + 1 < n:
                    next_line = lines[i + 1].strip()

                    # 检查下一行是否是大括号
                    if next_line == '{':
                        # 如果下一行是大括号，保持原有结构
                        processed.append(line)
                        processed.append(next_line)
                        i += 2
                    else:
                        # 否则将主体行与else语句合并
                        processed.append(f"{line} {{ {next_line} }}")
                        i += 2
                else:
                    processed.append(f"{line} {{}}")
                    i += 1
                continue
                
            # 处理单独一行的for循环（下一行是主体）
            if for_pattern.match(line):
                # 确保有下一行作为主体
                if i + 1 < n:
                    next_line = lines[i + 1].strip()

                    # 检查下一行是否是大括号
                    if next_line == '{':
                        # 如果下一行是大括号，保持原有结构
                        processed.append(line)
                        processed.append(next_line)
                        i += 2
                    else:
                        # 否则将主体行与for循环语句合并
                        processed.append(f"{line} {{ {next_line} }}")
                        i += 2
                else:
                    # 异常：for循环无主体，仍加空括号
                    processed.append(f"{line} {{}}")
                    i += 1
                continue
                
            # 处理单独一行的while循环（下一行是主体）
            if while_pattern.match(line):
                # 确保有下一行作为主体
                if i + 1 < n:
                    next_line = lines[i + 1].strip()

                    # 检查下一行是否是大括号
                    if next_line == '{':
                        # 如果下一行是大括号，保持原有结构
                        processed.append(line)
                        processed.append(next_line)
                        i += 2
                    else:
                        # 否则将主体行与while循环语句合并
                        processed.append(f"{line} {{ {next_line} }}")
                        i += 2
                else:
                    # 异常：while循环无主体，仍加空括号
                    processed.append(f"{line} {{}}")
                    i += 1
                continue

            # 非控制语句直接添加
            processed.append(line)
            i += 1

        return processed

    def add_return_to_main(self, lines):
        """使用字符串处理方法在main函数末尾添加return 0;语句"""
        # 创建结果行列表
        result_lines = lines.copy()
        
        # 将所有代码行合并为一个字符串，这样更容易处理压缩的代码格式
        code_str = ''.join(result_lines)
        
        # 查找main函数的开始位置
        main_start = code_str.find('int main(')
        if main_start == -1:
            main_start = code_str.find('main(')
        
        if main_start != -1:
            # 查找main函数的左大括号
            brace_start = code_str.find('{', main_start)
            if brace_start != -1:
                # 跟踪大括号嵌套层级，找到匹配的右大括号
                brace_count = 1
                brace_end = brace_start + 1
                
                while brace_end < len(code_str) and brace_count > 0:
                    if code_str[brace_end] == '{':
                        brace_count += 1
                    elif code_str[brace_end] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到main函数的结束大括号
                            break
                    brace_end += 1
                
                if brace_count == 0:
                    # 现在我们找到了main函数的开始和结束位置
                    # 检查main函数内部是否有在最后一个右大括号前的return语句
                    main_content = code_str[main_start:brace_end]
                    
                    # 查找最后一个return语句的位置
                    last_return_pos = main_content.rfind('return')
                    if last_return_pos != -1:
                        # 确保这个return语句不是在注释中，并且在最后一个右大括号前
                        last_return_end = main_content.find(';', last_return_pos)
                        if last_return_end != -1 and last_return_end < main_content.rfind('}'):
                            # 有return语句，但需要确认是否在main函数的最后位置
                            # 检查return语句之后是否只有空白和右大括号
                            after_return = main_content[last_return_end+1:].strip()
                            if after_return != '}':
                                # 在最后一个右大括号前添加return 0;
                                new_code = code_str[:brace_end] + 'return 0;' + code_str[brace_end:]
                                result_lines = new_code.split('\n')
                    else:
                        # 没有return语句，在最后一个右大括号前添加
                        new_code = code_str[:brace_end] + 'return 0;' + code_str[brace_end:]
                        result_lines = new_code.split('\n')
        
        # 如果上述方法失败，使用备用方案：直接在文件末尾的最后一个右大括号前添加
        # 这种方法更简单，适合处理压缩代码
        if not any('return 0;' in line for line in result_lines):
            # 重新合并为字符串进行简单处理
            simple_code = ''.join(result_lines)
            # 找到最后一个右大括号的位置
            last_brace_pos = simple_code.rfind('}')
            if last_brace_pos != -1:
                # 检查这个右大括号前是否是main函数
                main_pos = simple_code.rfind('int main(', 0, last_brace_pos)
                if main_pos == -1:
                    main_pos = simple_code.rfind('main(', 0, last_brace_pos)
                
                if main_pos != -1:
                    # 在最后一个右大括号前添加return 0;
                    new_code = simple_code[:last_brace_pos] + 'return 0;' + simple_code[last_brace_pos:]
                    result_lines = new_code.split('\n')
        
        return result_lines
    
    def remove_comments(self, lines):
        """消除所有注释行（以//开头的行）和行内注释（保留到//前的内容）"""
        result = []
        for line in lines:
            # 跳过空行
            if not line.strip():
                continue
            
            # 检查是否是整行注释
            if line.strip().startswith('//'):
                continue
            
            # 检查是否有行内注释
            # 需要考虑字符串内的//，不能误删
            in_string = False
            quote_char = None
            i = 0
            while i < len(line):
                # 处理字符串
                if line[i] in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        quote_char = line[i]
                    elif line[i] == quote_char:
                        in_string = False
                # 找到非字符串内的//
                elif not in_string and i+1 < len(line) and line[i:i+2] == '//':
                    # 只保留注释前的内容
                    result.append(line[:i].strip())
                    break
                i += 1
            else:
                # 没有找到行内注释，保留整行
                result.append(line.strip())
        return result

    def format(self, code_lines):
        """主流程：先移除注释→再清理空格→再处理跨行控制语句→确保main函数有return 0"""
        self.in_string = False
        # 1. 先移除所有注释行和行内注释
        no_comments_lines = self.remove_comments(code_lines)
        # 2. 清理每行的冗余空格（保留换行结构）
        cleaned_lines = [self.remove_unnecessary_spaces(line) for line in no_comments_lines]
        # 3. 处理跨多行的if/else（核心修复换行场景）
        processed_lines = self.process_multi_line_control(cleaned_lines)
        # 4. 确保main函数末尾有return 0;
        final_lines = self.add_return_to_main(processed_lines)
        return final_lines


def read_code_file(file_path):
    # 尝试多种编码方式读取文件
    encodings = ['utf-8', 'gbk', 'ansi']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.readlines()
                logger.info(f"成功以{encoding}编码读取文件")
                return content
        except UnicodeDecodeError:
            logger.debug(f"以{encoding}编码读取失败，尝试下一种编码...")
        except Exception as e:
            logger.error(f"读取文件时出现错误({encoding}): {e}")
    
    # 所有编码尝试失败
    logger.error("尝试所有编码方式都失败了")
    return None


def select_file_gui():
    """使用tkinter打开文件选择对话框"""
    try:
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口

        # 设置文件类型过滤器
        file_types = [
            ("C/C++ Files", "*.c *.cpp"),
            ("All Files", "*.*")
        ]

        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择C/C++文件",
            filetypes=file_types,
            initialdir=os.getcwd()
        )

        return file_path
    except Exception as e:
        logger.error(f"图形界面文件选择失败：{e}")
        return None


def select_file_cli():
    """命令行模式选择文件"""
    logger.info("请输入C/C++文件的路径：")
    file_path = input().strip()

    # 检查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"文件不存在：{file_path}")
        return None

    return file_path


def save_formatted_file(formatted_content, output_filename="Cfile_formatted.cpp"):
    """保存格式化后的代码到文件"""
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        logger.info(f"格式化后的代码已保存到: {os.path.abspath(output_filename)}")
        return True
    except Exception as e:
        logger.error(f"保存文件失败：{e}")
        return False


def main(create_file=True):
    """主函数：选择文件并返回格式化后的内容

    Args:
        create_file (bool): 如果为True，则将格式化后的代码保存为Cfile_formatted.cpp文件

    Returns:
        str: 格式化后的代码内容，如果失败则返回None
    """
    file_path = None

    # 如果有命令行参数，直接使用第一个参数作为文件路径
    if len(sys.argv) >= 2:
        file_path = sys.argv[1]
        # 检查是否有第二个参数指定create_file
        if len(sys.argv) >= 3:
            create_file = sys.argv[2].lower() in ('true', '1', 'yes', 'y')

    else:
        # 尝试使用图形界面选择文件
        if tkinter_available:
            logger.info("正在打开文件选择对话框...")
            file_path = select_file_gui()
            if not file_path:
                return None
        else:
            # 直接使用命令行模式
            file_path = select_file_cli()

    if not file_path:
        logger.error("未提供有效的文件路径")
        return None

    # 检查文件类型
    if not (file_path.endswith('.c') or file_path.endswith('.cpp')):
        logger.error("输入文件必须是.c或.cpp格式")
        return None

    # 读取文件内容
    code_lines = read_code_file(file_path)

    if code_lines is None:
        return None

    # 格式化代码
    formatter = CppCodeFormatter()
    formatted_lines = formatter.format(code_lines)

    # 返回格式化后的内容
    formatted_content = '\n'.join(formatted_lines)

    # 确保保存到文件
    save_formatted_file(formatted_content)

    return formatted_content


if __name__ == "__main__":
    # 运行并打印结果
    result = main()
    if result:
        logger.info("格式化完成！")
        logger.info("=" * 50)
        logger.info(result)
