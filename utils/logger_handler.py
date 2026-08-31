import logging
import os
from datetime import datetime

from utils.path_tool import get_abs_path

#日志的根目录
LOG_PATH = get_abs_path("logs")
# LOG_PATH = ("logs")
#确保目录存在
os.makedirs(LOG_PATH, exist_ok=True)

#日志格式
DEFAULT_LOG_FORMAT = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)

def get_logger(
        name: str = "agent",
        log_file: str = None,
        file_level: int = logging.DEBUG,
        console_level: int = logging.INFO,
        log_format: logging.Formatter = DEFAULT_LOG_FORMAT,
        ) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    #避免重复创建日志记录器
    if logger.handlers:
        return logger

    #控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)


    #文件handler
    if not log_file:
        log_file  = os.path.join(LOG_PATH, f"{name} {datetime.now().strftime('%Y-%m-%d')}.log")

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger

logger = get_logger()


if __name__ == "__main__":
    logger = get_logger()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
