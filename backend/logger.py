import logging
import sys
from logging import Logger

# 定义日志格式
# 时间戳 | 日志级别 | logger名称 | 模块:行号 | 消息
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def _setup_logger(name: str, level: int = logging.INFO) -> Logger:
    """
    创建一个配置好的 logger
    """
    logger = logging.getLogger(name)
    
    # 如果 logger 已经有 handler，说明已经被配置过，直接返回
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # 创建控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 设置 formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(formatter)
    
    # 添加 handler
    logger.addHandler(console_handler)
    
    # 防止日志向上冒泡导致重复打印
    logger.propagate = False
    
    return logger

# project_logger: 用于项目其他部分的日志
project_logger = _setup_logger("GRAPH", logging.INFO)

if __name__ == "__main__":
    project_logger.debug("这是 project 的 debug 日志")
    project_logger.info("这是 project 的 info 日志")
    project_logger.warning("这是 project 的 warning 日志")
    project_logger.error("这是 project 的 error 日志")
