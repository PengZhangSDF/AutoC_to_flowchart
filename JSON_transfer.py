import json
import sys
import re
from copy import deepcopy
from logger.logger import logger
from utils.config_manager import get_config


class CppToJsonConverter:
    def __init__(self, debug=False):
        self.TYPE_KEYWORDS = {"int", "float", "double", "char", "bool", "long", "short", "unsigned", "signed", "auto",
                              "const", "void", "static", "extern", "register"}
        self.DECL_KEYWORDS = {"struct", "class", "enum", "typedef"}  # 类型声明关键字
        self.debug = debug
        # 输入函数特征（与原输入识别逻辑保持一致）
        self.INPUT_PATTERNS = ["cin>>", "std::cin>>", "scanf(", "get(", "getline(", "getchar("]

    def log(self, msg):
        if self.debug:
            logger.debug(msg)

    def is_escape_char(self, s, pos):
        escape_count = 0
        p = pos - 1
        while p >= 0 and s[p] == '\\':
            escape_count += 1
            p -= 1
        return escape_count % 2 == 1

    def split_into_units(self, formatted_code):
        """按分号+块标记拆分，确保每个语句独立"""
        self.log("开始拆分逻辑单元...")
        units = []
        current_unit = []
        in_string = False
        string_quote = ''
        brace_count = 0  # 跟踪括号嵌套深度（避免拆分for循环内部分号）

        for idx, c in enumerate(formatted_code):
            if c in ('"', "'") and not self.is_escape_char(formatted_code, idx):
                in_string = not in_string if c == string_quote else True
                string_quote = c if in_string else ''
                current_unit.append(c)
                continue

            if not in_string:
                # 跟踪括号深度
                if c == '(':
                    brace_count += 1
                elif c == ')':
                    if brace_count > 0:
                        brace_count -= 1

                # 分号拆分语句：仅当不在括号内时才拆分
                if c == ';' and brace_count == 0:
                    current_unit.append(c)
                    unit_str = ''.join(current_unit).strip()
                    if unit_str:
                        units.append(unit_str)
                        self.log(f"拆分语句单元: {unit_str}")
                    current_unit = []
                    continue

                # 块标记单独拆分
                if c in ('{', '}'):
                    if current_unit:
                        unit_str = ''.join(current_unit).strip()
                        if unit_str:
                            units.append(unit_str)
                            self.log(f"拆分语句单元: {unit_str}")
                        current_unit = []
                    units.append(c)
                    self.log(f"拆分块标记: {c}")
                    continue

            current_unit.append(c)

        if current_unit:
            unit_str = ''.join(current_unit).strip()
            if unit_str:
                units.append(unit_str)
                self.log(f"拆分剩余单元: {unit_str}")

        self.log(f"拆分完成，共{len(units)}个单元")
        return units

    def parse_cout_content(self, cout_unit):
        """解析cout输出内容"""
        content_part = re.sub(r'^std::cout\s*<<|^cout\s*<<', '', cout_unit).rstrip(';').strip()
        if not content_part:
            return ""

        parts = re.split(r'\s*<<\s*', content_part)
        output_parts = []
        for part in parts:
            part = part.strip()
            if part in ("endl", "std::endl", "flush"):
                continue
            if part.startswith(('"', "'")) and part.endswith(('"', "'")):
                output_parts.append(part[1:-1])
            else:
                output_parts.append(part)
        return ''.join(output_parts)
        
    def parse_printf_content(self, printf_unit):
        """解析printf输出内容"""
        # 提取printf括号内的内容
        match = re.search(r'printf\s*\((.*)\)', printf_unit)
        if not match:
            return ""
            
        args = match.group(1).strip().rstrip(';')
        if not args:
            return ""
            
        # 提取格式字符串（第一个参数）
        format_str_match = re.match(r'"(.*?)"', args)
        if format_str_match:
            format_str = format_str_match.group(1)
            # 替换常见的格式说明符
            format_str = re.sub(r'%[sdcf]', 'x', format_str)  # 将%d,%s,%c,%f等替换为x
            format_str = re.sub(r'%\.[0-9]+[sdcf]', 'x', format_str)  # 处理%.2f等格式
            return format_str
            
        return ""

    def in_string_context(self, unit):
        """判断关键字是否在字符串内"""
        in_string = False
        string_quote = ''
        for idx, c in enumerate(unit):
            if c in ('"', "'") and not self.is_escape_char(unit, idx):
                in_string = not in_string if c == string_quote else True
                string_quote = c if in_string else ''
            for kw in ["if", "while", "for", "else", "switch"]:
                if unit.startswith(kw, idx) and in_string:
                    return True
        return False

    def extract_condition(self, unit, keyword):
        """提取控制结构条件（增强for循环解析）"""
        kw_len = len(keyword)
        start = unit.find('(', unit.find(keyword) + kw_len)
        if start == -1:
            return "条件"

        pos = start + 1
        in_string = False
        string_quote = ''
        brace_count = 0
        while pos < len(unit):
            c = unit[pos]
            if c in ('"', "'") and not self.is_escape_char(unit, pos):
                in_string = not in_string if c == string_quote else True
                string_quote = c if in_string else ''
            if not in_string:
                if c == '(':
                    brace_count += 1
                elif c == ')':
                    if brace_count == 0:
                        condition_str = unit[start + 1:pos].strip()
                        # 针对for循环拆分三个部分
                        if keyword == "for" and ';' in condition_str:
                            parts = [p.strip() for p in condition_str.split(';')]
                            return f"{parts[1]}"
                        return condition_str
                    brace_count -= 1
            pos += 1
        return unit[start + 1:].strip()

    def check_function_definition(self, units, current_idx):
        """跨单元识别函数定义"""
        if current_idx + 1 >= len(units):
            return None

        decl_unit = units[current_idx].strip()
        next_unit = units[current_idx + 1].strip()

        if '(' in decl_unit and ')' in decl_unit and next_unit == '{':
            before_paren = decl_unit.split('(', 1)[0].strip()
            cleaned_before = before_paren.replace('*', ' ').replace('&', ' ').strip()
            func_name = cleaned_before.split()[-1] if cleaned_before else ''
            if func_name:
                self.log(f"识别函数: {func_name}")
                return func_name
        return None

    def is_void_function(self, decl_unit: str) -> bool:
        """判断函数声明是否为void返回类型"""
        if not decl_unit:
            return False

        signature = decl_unit.strip()
        signature = signature.rstrip('{').strip()
        match = re.match(r'([\w\s\*\&:<>,~]+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature)
        if not match:
            return False

        return_type = match.group(1).strip()
        tokens = return_type.replace('\t', ' ').split()
        return any(token == 'void' for token in tokens)

    def is_declaration(self, unit):
        """判断单元是否为任意声明（变量/函数/类型声明），是则返回True。
        注意：包含初始化的变量声明（如 int a = 5;）不会被判定为声明，而会被当作赋值语句处理"""
        unit_stripped = unit.strip().rstrip(';')
        if not unit_stripped:
            return False

        # 1. 类型声明（struct/class/enum/typedef）
        for decl_kw in self.DECL_KEYWORDS:
            if unit_stripped.startswith(decl_kw) and not self.in_string_context(unit):
                self.log(f"识别类型声明: {unit} → 跳过")
                return True

        # 2. 变量声明（带数据类型关键字，且非函数/控制结构）
        for type_kw in self.TYPE_KEYWORDS:
            if (unit_stripped.startswith(f"{type_kw} ") or
                unit_stripped.startswith(f"{type_kw}\t") or
                unit_stripped == type_kw):
                # 排除控制结构（if/while等）和函数调用
                if not any(kw in unit_stripped for kw in ["if", "while", "for", "else", "return"]) and '(' not in unit_stripped:
                    # 检查是否包含初始化（包含=号）
                    if '=' in unit_stripped:
                        self.log(f"识别带初始化的变量声明: {unit} → 不跳过，将作为赋值处理")
                        return False  # 不跳过，让后续逻辑将其识别为赋值
                    self.log(f"识别变量声明: {unit} → 跳过")
                    return True

        # 3. 函数声明（带()且无{}，非函数定义）
        # 函数声明通常有返回类型前缀，如: int add(int a, int b);
        # 函数调用没有返回类型前缀，如: add(a, b);
        if '(' in unit_stripped and ')' in unit_stripped and '{' not in unit_stripped:
            # 排除控制结构（if(...)、while(...)等）
            excluded_keywords = ["if", "while", "for", "else", "switch", "return",
                               "scanf", "fscanf", "cin", "getline", "getchar",
                               "cout", "printf", "puts", "putchar", "scanf_s",
                               "print_s", "put", "fputs", "get"]
            
            is_excluded = any(unit_stripped.startswith(kw) for kw in excluded_keywords)
            
            if not is_excluded:
                # 检查是否有类型关键字前缀（函数声明的特征）
                has_type_prefix = False
                words = unit_stripped.split()
                if len(words) >= 2:  # 至少有两个词，如 "int add(...)"
                    first_word = words[0]
                    # 检查第一个词是否是类型关键字
                    if first_word in self.TYPE_KEYWORDS or first_word in self.DECL_KEYWORDS:
                        has_type_prefix = True
                        self.log(f"识别函数声明（有类型前缀）: {unit} → 跳过")
                        return True
                
                # 没有类型前缀，可能是函数调用，不跳过
                if not has_type_prefix:
                    self.log(f"识别可能的函数调用（无类型前缀）: {unit} → 不跳过")
                    return False

        return False

    def find_matching_brace(self, units, start_idx):
        """找到匹配的}索引"""
        if start_idx >= len(units) or units[start_idx] != '{':
            self.log("无起始{，返回-1")
            return -1

        brace_count = 1
        current_idx = start_idx + 1
        while current_idx < len(units):
            if units[current_idx] == '{':
                brace_count += 1
            elif units[current_idx] == '}':
                brace_count -= 1
                if brace_count == 0:
                    self.log(f"匹配}}在索引{current_idx}")
                    return current_idx
            current_idx += 1
        return -1

    def has_input_in_loop(self, loop_child_nodes):
        """
        递归检查循环体内是否包含输入函数（cin/scanf/get等）
        loop_child_nodes: 循环体的子节点列表（含嵌套块）
        返回: True=含输入函数，False=不含
        """
        for node in loop_child_nodes:
            # 1. 检查当前节点是否为输入i/o节点（原逻辑已标记）
            if node.get("tag") == "i/o" and "输入变量x" in node.get("translated", ""):
                self.log(f"循环体内发现输入节点: {node['original_unit']}")
                return True

            # 2. 检查原始单元是否含输入函数特征（防止漏判未标记的输入）
            original_unit = node.get("original_unit", "").replace(" ", "")
            if any(pattern in original_unit for pattern in self.INPUT_PATTERNS):
                self.log(f"循环体内发现输入函数: {node['original_unit']}")
                return True

            # 3. 递归检查嵌套子节点（如if块、嵌套循环内的输入）
            for child_block in node.get("children", []):
                grand_children = child_block.get("children", [])
                if self.has_input_in_loop(grand_children):
                    return True

        return False

    def parse_units(self, units, start_idx=0, end_idx=None):
        """递归解析单元：跳过所有声明，只记录执行语句；循环含输入则仅记“输入变量x”"""
        nodes = []
        current_idx = start_idx
        if end_idx is None:
            end_idx = len(units) - 1

        while current_idx <= end_idx:
            unit = units[current_idx].strip()
            if not unit:
                current_idx += 1
                continue

            self.log(f"\n处理单元[{current_idx}]: {unit}")

            # 核心逻辑：跳过所有声明单元，不记录不翻译
            if self.is_declaration(unit):
                current_idx += 1
                continue

            # 非声明单元：正常解析
            node = {
                "original_unit": unit,
                "translated": "",
                "tag": "",
                "children": []
            }

            # 1. 块标记（{/}）
            if unit in ('{', '}'):
                node["translated"] = unit
                node["tag"] = "block"
                nodes.append(node)
                current_idx += 1
                continue

            # 2. 输入函数（cin/scanf等）
            input_patterns = ["scanf(", "fscanf(", "cin>>", "std::cin>>", "getline(", "getchar("]
            if any(pattern in unit.replace(" ", "") for pattern in input_patterns) and not self.in_string_context(unit):
                node["translated"] = "输入变量x"
                node["tag"] = "i/o"
                nodes.append(node)
                current_idx += 1
                continue

            # 3. 输出函数（cout/printf等）
            output_patterns = ["cout<<", "std::cout<<", "printf("]
            if any(pattern in unit.replace(" ", "") for pattern in output_patterns) and not self.in_string_context(
                    unit):
                if "cout" in unit:
                    content = self.parse_cout_content(unit)
                    node["translated"] = f"输出\"{content}\""
                elif "printf" in unit:
                    content = self.parse_printf_content(unit)
                    node["translated"] = f"输出\"{content}\"" if content else "输出内容"
                else:
                    node["translated"] = "输出内容"
                node["tag"] = "i/o"
                nodes.append(node)
                current_idx += 1
                continue

            # 4. if语句（branch标记）
            if (unit.startswith(("if(", "if (")) and not self.in_string_context(unit)):
                condition = self.extract_condition(unit, "if")
                node["translated"] = f"是否{condition}"
                node["tag"] = "branch"

                if current_idx + 1 <= end_idx and units[current_idx + 1] == '{':
                    brace_start = current_idx + 1
                    global_brace_end = self.find_matching_brace(units, brace_start)
                    child_end = min(global_brace_end - 1, end_idx)
                    if global_brace_end != -1:
                        child_nodes = self.parse_units(units, brace_start + 1, child_end)
                        node["children"].append({
                            "type": "if_block",
                            "children": child_nodes
                        })
                        current_idx = global_brace_end + 1
                    else:
                        current_idx += 1
                else:
                    current_idx += 1

                nodes.append(node)
                continue

            # 5. else语句（branch标记）
            if (unit.startswith(("else", "else if")) and not self.in_string_context(unit)):
                if "if" in unit:
                    condition = self.extract_condition(unit, "else if")
                    node["translated"] = f"否则当{condition}时"
                else:
                    node["translated"] = "否则"
                node["tag"] = "branch"

                if current_idx + 1 <= end_idx and units[current_idx + 1] == '{':
                    brace_start = current_idx + 1
                    global_brace_end = self.find_matching_brace(units, brace_start)
                    child_end = min(global_brace_end - 1, end_idx)
                    if global_brace_end != -1:
                        child_nodes = self.parse_units(units, brace_start + 1, child_end)
                        node["children"].append({"type": "else_block", "children": child_nodes})
                        current_idx = global_brace_end + 1
                    else:
                        current_idx += 1
                else:
                    current_idx += 1

                nodes.append(node)
                continue

            # 6. while循环（修改后：判断为父，块为子）
            if (unit.startswith(("while(", "while (")) and not self.in_string_context(unit)):
                # 步骤1：先提取循环判断条件，创建“判断节点”（父节点）
                condition = self.extract_condition(unit, "while")
                judge_node = {
                    "original_unit": unit,  # 保留原while语句用于追溯
                    "translated": f"判断：{condition}",  # 明确标记为判断
                    "tag": "loop",  # 新增判断节点标签，区分普通节点
                    "children": []  # 子节点存放真/假分支（此处仅需真分支：循环块）
                }

                # 步骤2：解析循环内部块（作为判断的真分支子类）
                child_nodes = []
                global_brace_end = -1
                if current_idx + 1 <= end_idx and units[current_idx + 1] == '{':
                    brace_start = current_idx + 1
                    global_brace_end = self.find_matching_brace(units, brace_start)
                    if global_brace_end != -1:
                        child_end = min(global_brace_end - 1, end_idx)
                        # 递归解析循环块内容，结果作为判断节点的子节点
                        child_nodes = self.parse_units(units, brace_start + 1, child_end)

                # 步骤3：检查循环块内是否含输入，决定节点类型
                has_input = self.has_input_in_loop(child_nodes)
                # 计算循环体内的语句数量（排除块标记节点）
                statement_count = sum(1 for node in child_nodes if node.get("tag") != "block")
                
                if has_input and statement_count <= 3:
                    # 含输入且语句数不超过3个：不生成循环结构，仅记录输入节点
                    input_node = {
                        "original_unit": unit,
                        "translated": "输入变量x",
                        "tag": "i/o",
                        "children": []
                    }
                    nodes.append(input_node)
                    self.log(f"while循环含输入且语句数较少({statement_count}个)，替换为输入节点")
                else:
                    # 不含输入 或 含输入但语句数超过3个：正常生成循环结构
                    if child_nodes:
                        judge_node["children"].append({
                            "type": "while_true_block",  # 标记为while判断的真分支
                            "translated": "循环体（判断为真时执行）",  # 明确分支含义
                            "children": child_nodes
                        })
                    # 将判断节点加入主节点列表（判断为父，块为子）
                    nodes.append(judge_node)
                    self.log(f"生成while判断节点，子节点为循环块（{len(child_nodes)}个节点）")

                # 更新索引：跳过循环块（已解析）
                current_idx = global_brace_end + 1 if global_brace_end != -1 else current_idx + 1
                continue

            # 7. for循环（修改后：判断为父，块为子）
            if (unit.startswith(("for(", "for (")) and not self.in_string_context(unit)):
                # 步骤1：提取for循环的核心判断条件（原逻辑已拆分初始化/条件/迭代，仅取条件）
                condition = self.extract_condition(unit, "for")
                judge_node = {
                    "original_unit": unit,  # 保留原for语句（含初始化和迭代）
                    "translated": f"判断：{condition}（for循环）",  # 明确for循环的判断
                    "tag": "condition",  # 统一判断节点标签
                    "children": []
                }

                # 步骤2：解析for循环内部块（作为判断的真分支子类）
                child_nodes = []
                global_brace_end = -1
                if current_idx + 1 <= end_idx and units[current_idx + 1] == '{':
                    brace_start = current_idx + 1
                    global_brace_end = self.find_matching_brace(units, brace_start)
                    if global_brace_end != -1:
                        child_end = min(global_brace_end - 1, end_idx)
                        child_nodes = self.parse_units(units, brace_start + 1, child_end)

                # 步骤3：检查循环块内是否含输入，决定节点类型
                has_input = self.has_input_in_loop(child_nodes)
                # 计算循环体内的语句数量（排除块标记节点）
                statement_count = sum(1 for node in child_nodes if node.get("tag") != "block")
                
                if has_input and statement_count <= 3:
                    # 含输入且语句数不超过3个：替换为输入节点
                    input_node = {
                        "original_unit": unit,
                        "translated": "输入变量x",
                        "tag": "i/o",
                        "children": []
                    }
                    nodes.append(input_node)
                    self.log(f"for循环含输入且语句数较少({statement_count}个)，替换为输入节点")
                else:
                    # 不含输入 或 含输入但语句数超过3个：正常生成循环结构
                    if child_nodes:
                        judge_node["children"].append({
                            "type": "for_block",  # 标记为for判断的真分支
                            "translated": "循环体（判断为真时执行）",
                            "children": child_nodes
                        })
                    nodes.append(judge_node)
                    self.log(f"生成for判断节点，子节点为循环块（{len(child_nodes)}个节点）")

                # 更新索引：跳过循环块
                current_idx = global_brace_end + 1 if global_brace_end != -1 else current_idx + 1
                continue

            # 8. return语句
            if unit.startswith("return") and not self.in_string_context(unit):
                return_val = unit.split('return', 1)[1].strip().rstrip(';').strip()
                node["translated"] = f"返回{return_val}" if return_val else "返回"
                node["tag"] = "statement"
                nodes.append(node)
                current_idx += 1
                continue

            # 9. 函数调用（在main中调用其他函数）
            # 识别模式：函数名(...) 但排除已处理的特殊函数和控制结构
            if '(' in unit and ')' in unit and not self.in_string_context(unit):
                # 排除控制结构和已处理的I/O函数
                excluded_keywords = ["if", "while", "for", "else", "switch", "return",
                                   "scanf", "fscanf", "cin", "getline", "getchar",
                                   "cout", "printf", "puts", "putchar"]
                
                # 检查是否以排除的关键字开头
                is_excluded = False
                for kw in excluded_keywords:
                    if unit.strip().startswith(kw):
                        is_excluded = True
                        break
                
                # 如果不是排除的关键字，则识别为函数调用
                if not is_excluded:
                    # 提取函数名（括号前的部分）
                    func_name_match = unit.strip().split('(')[0].strip()
                    # 移除可能的类型前缀（如果有的话）
                    func_name = func_name_match.split()[-1] if func_name_match else "未知函数"
                    
                    node["translated"] = f"调用{func_name}函数"
                    node["tag"] = "statement"
                    nodes.append(node)
                    self.log(f"识别函数调用: {unit} → 调用{func_name}函数")
                    current_idx += 1
                    continue

            # 10. 赋值语句（包括带初始化的声明）
            if '=' in unit and not self.in_string_context(unit) and not any(
                    kw in unit for kw in ["if", "while", "for", "else", "return"]):
                node["translated"] = "变量赋值"
                node["tag"] = "statement"
                nodes.append(node)
                current_idx += 1
                continue

            # 11. 其他非声明执行语句（保留原句）
            node["translated"] = unit
            node["tag"] = "statement"
            nodes.append(node)
            current_idx += 1

        return nodes

    def process_main_only(self, units):
        """只提取并解析main函数内的单元（跳过声明）"""
        self.log("\n查找main函数...")
        current_idx = 0
        n = len(units)

        while current_idx < n:
            if self.check_function_definition(units, current_idx) == "main":
                self.log("找到main函数，提取内部单元")
                brace_start = current_idx + 1
                global_brace_end = self.find_matching_brace(units, brace_start)
                if global_brace_end != -1:
                    main_nodes = self.parse_units(units, brace_start, global_brace_end)
                    self.log(f"main内部解析完成，节点数: {len(main_nodes)}")
                    return main_nodes
            current_idx += 1

        self.log("未找到main函数")
        return []

    def create_function_header_node(self, func_name):
        """创建函数名称节点"""
        return {
            "original_unit": f"function {func_name}",
            "translated": f"{func_name} 函数",
            "tag": "statement",
            "children": []
        }

    def process_all_functions(self, units):
        """提取并解析所有函数定义"""
        functions = []
        current_idx = 0
        total = len(units)

        while current_idx < total:
            func_name = self.check_function_definition(units, current_idx)
            if func_name:
                brace_start = current_idx + 1
                global_brace_end = self.find_matching_brace(units, brace_start)
                if global_brace_end != -1:
                    decl_unit = units[current_idx].strip()
                    is_void = self.is_void_function(decl_unit)
                    nodes = self.parse_units(units, brace_start, global_brace_end)
                    header_node = self.create_function_header_node(func_name)
                    nodes.insert(0, header_node)
                    functions.append({
                        "name": func_name,
                        "nodes": nodes,
                        "is_void": is_void
                    })
                    current_idx = global_brace_end + 1
                    continue
            current_idx += 1

        return functions

    def convert(self, formatted_cpp_path, output_json_path):
        """主转换流程：跳过所有声明，只输出执行语句"""
        try:
            with open(formatted_cpp_path, 'r', encoding='utf-8') as f:
                formatted_code = f.read()
            self.log("文件读取成功")
        except Exception as e:
            logger.error(f"读取文件失败：{e}")
            return

        units = self.split_into_units(formatted_code)
        if not units:
            logger.error("未解析到有效代码单元")
            return

        multi_function_enabled = get_config('parser', 'multi_function', default=False)

        if multi_function_enabled:
            functions = self.process_all_functions(units)
            main_entry = next((f for f in functions if f['name'] == 'main'), None)
            main_nodes = deepcopy(main_entry['nodes']) if main_entry else []
            other_functions = [
                {"name": f['name'], "nodes": deepcopy(f['nodes'])}
                for f in functions if f['name'] != 'main'
            ]
            output_payload = {
                "main": main_nodes,
                "functions": other_functions
            }
        else:
            main_nodes = self.process_main_only(units)
            output_payload = main_nodes

        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(output_payload, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON转换完成，保存至：{output_json_path}")
        except Exception as e:
            logger.error(f"保存JSON失败：{e}")

def main():
    DEBUG = True
    input_file_path = 'Cfile_formatted.cpp'
    output_file_path = 'output.json'
    from C_FIXED import main
    result = main(create_file=True)
    if result==False:
        return False
    if not DEBUG and len(sys.argv) == 3:
        input_file_path = sys.argv[1]
        output_file_path = sys.argv[2]
    elif not DEBUG:
            logger.info("用法：python cpp_to_json.py <已格式化的C++文件路径> <输出JSON文件路径>")
            sys.exit(1)

    converter = CppToJsonConverter(debug=DEBUG)
    converter.convert(input_file_path, output_file_path)
    return result

if __name__ == "__main__":
    DEBUG = True
    formatted_file = "Cfile_formatted.cpp"  # 你的格式化文件路径
    output_json = "./output.json"

    if not DEBUG and len(sys.argv) == 3:
        formatted_file = sys.argv[1]
        output_json = sys.argv[2]
    elif not DEBUG:
        logger.info("用法：python cpp_to_json.py <已格式化的C++文件路径> <输出JSON文件路径>")
        sys.exit(1)

    converter = CppToJsonConverter(debug=DEBUG)
    converter.convert(formatted_file, output_json)