# utils/logger.py
import sys
import os
import time
from functools import wraps

from loguru import logger


def log_execution_time(func):
    """一个好用的耗时记录装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        cost = time.time() - start
        logger.debug(f"[{func.__name__}] 耗时: {cost:.3f} 秒")
        return result
    return wrapper


def setup_logger():
    """
    初始化 Loguru 日志系统
    """
    # 1. 清除 Loguru 默认的控制台输出配置（防止重复打印）
    logger.remove()

    # 2. 控制台输出 ( INFO 级别，带颜色 )
    # 格式：时间 | 级别 | 文件:函数:行号 - 消息
    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:"
               "<cyan>{function}</cyan>:"
               "<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 3. 配置文件输出 ( DEBUG 级别，全量记录备查 )
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    log_file_path = os.path.join(logs_dir, "a_scholar_{time:YYYY-MM-DD}.log")

    logger.add(
        log_file_path,
        level="DEBUG",
        rotation="5 MB",  # 日志文件达到 5MB 时自动滚动(新建文件)
        retention="10 days",  # 自动清理 10 天前的旧日志
        compression="zip",  # 旧日志自动压缩存储，节省空间
        enqueue=True,  # 开启异步写入，多线程/Streamlit环境下保证线程安全不阻塞！
        encoding="utf-8"
    )

    logger.info("🚀 A-Scholar Loguru System Initialized Successfully!")


# 模块被导入时自动执行初始化
setup_logger()

# 导出这个配置好的 logger 供其他文件使用
__all__ = ["logger", "log_execution_time"]
