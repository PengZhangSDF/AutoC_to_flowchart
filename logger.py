import os
import datetime

class Logger:
    def __init__(self, max_log_files=20):
        """
        初始化Logger
        
        Args:
            max_log_files: 保留的最大日志文件数量，默认为20
        """
        # 配置日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_dir = log_dir
        self.max_log_files = max_log_files
        
        # 生成日志文件名（包含日期时间戳）
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"app_{current_time}.log")
        
        # 创建空日志文件
        open(self.log_file, 'w').close()
        
        # 清理旧日志文件
        self._cleanup_old_logs()
        
        # 记录日志文件路径信息
        self.info(f"日志文件路径: {self.log_file}")
    
    def _cleanup_old_logs(self):
        """
        清理旧的日志文件，只保留最新的max_log_files个文件
        """
        try:
            # 获取日志目录中所有的.log文件
            log_files = []
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.log') and filename.startswith('app_'):
                    filepath = os.path.join(self.log_dir, filename)
                    # 获取文件的修改时间
                    mtime = os.path.getmtime(filepath)
                    log_files.append((filepath, mtime))
            
            # 按照修改时间排序（最新的在前）
            log_files.sort(key=lambda x: x[1], reverse=True)
            
            # 如果日志文件数量超过限制，删除旧的文件
            if len(log_files) > self.max_log_files:
                files_to_delete = log_files[self.max_log_files:]
                for filepath, _ in files_to_delete:
                    try:
                        os.remove(filepath)
                        print(f"[INFO] 已删除旧日志文件: {os.path.basename(filepath)}")
                    except Exception as e:
                        print(f"[WARNING] 删除日志文件失败: {filepath}, 错误: {e}")
        
        except Exception as e:
            print(f"[WARNING] 清理日志文件时出错: {e}")
    
    def get_caller_info(self):
        import traceback
        stack = traceback.extract_stack()
        # 找到调用logger的实际文件和行号
        # 跳过前几个帧，因为它们是logger内部的调用
        for i in range(len(stack) - 2, 0, -1):
            frame = stack[i]
            # 跳过logger自身的文件
            if frame.filename != __file__:
                # 确保我们找到了实际调用的文件，而不是中间模块
                # 检查是否是实际业务文件而不是标准库或其他依赖
                filename = os.path.basename(frame.filename)
                # 排除标准库路径和空文件名
                if filename and '.py' in filename:
                    line_number = frame.lineno
                    return filename, line_number
        return "unknown", 0
    
    def log(self, level, message):
        filename, line_number = self.get_caller_info()
        current_time = datetime.datetime.now().strftime("%M:%S")
        # 严格按照要求的格式：filename-line-Debug_Level-Min:Sec-内容
        log_entry = f"{filename}-{line_number}-{level}-{current_time}-{message}\n"
        
        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # 同时输出到控制台（保持原有功能）
        print(f"[{level}] {message}")
    
    def debug(self, message):
        self.log("DEBUG", message)
    
    def info(self, message):
        self.log("INFO", message)
    
    def warning(self, message):
        self.log("WARNING", message)
    
    def error(self, message):
        self.log("ERROR", message)
    
    def critical(self, message):
        self.log("CRITICAL", message)

# 创建全局logger实例
logger = Logger()

# 记录程序启动信息
logger.info("程序启动")

# 定义print_to_log函数，支持不同的日志级别
def print_to_log(message="", level="info"):
    """
    将print语句转换为logger调用
    
    Args:
        message: 要记录的消息
        level: 日志级别，默认为"info"
    """
    message_str = str(message)
    if level == "debug":
        logger.debug(message_str)
    elif level == "info":
        logger.info(message_str)
    elif level == "warning":
        logger.warning(message_str)
    elif level == "error":
        logger.error(message_str)
    elif level == "critical":
        logger.critical(message_str)
    else:
        logger.info(message_str)