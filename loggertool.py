import threading
import logging
import configparser

# 创建 ConfigParser 对象
config = configparser.ConfigParser()

# 读取配置文件
config.read('config.ini')

logger_grade = {
    'CRITICAL': 50,
    'FATAL': 50,
    'ERROR': 40,
    'WARNING': 30,
    'WARN': 30,
    'INFO': 20,
    'DEBUG': 10,
    'NOTSET': 0,
}

# 存储的日志文件名
handler_name = config['logger']['handler_file_name']

# 日志文件的输出级别
file_handler_level = logger_grade.get(config['logger']['file_handler_level'], 10)

# 控制台日志输出的级别
stream_handler_level = logger_grade.get(config['logger']['stream_handler_level'], 40)


class Logger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance.logger = logging.getLogger()
                cls._instance.logger.setLevel(logging.DEBUG)
                fh = logging.FileHandler(handler_name)
                # 设置日志文件输出级别
                fh.setLevel(file_handler_level)
                ch = logging.StreamHandler()
                # 设置控制台日志文件输出级别
                ch.setLevel(stream_handler_level)
                # 设置日志文件格式
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                fh.setFormatter(formatter)
                ch.setFormatter(formatter)
                cls._instance.logger.addHandler(fh)
                cls._instance.logger.addHandler(ch)

            return cls._instance
