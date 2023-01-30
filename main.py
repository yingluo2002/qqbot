import os
import json
import socket
from queue import Queue
import qqapi
import threading
from loggertool import Logger
import configparser

# 创建 ConfigParser 对象
config = configparser.ConfigParser()

# 读取配置文件
config.read('config.ini')
local_ip = config['server']['local_ip']
send_server_port = int(config['server']['send_server_port'])
once_max_recv = int(config['server']['once_max_recv'])

logger = Logger().logger

ListenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ListenSocket.bind((local_ip, send_server_port))
ListenSocket.listen(100)
HttpResponseHeader = '''HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'''


def request_to_json(msg):
    for i in range(len(msg)):
        if msg[i] == "{" and msg[-1] == "\n":
            return json.loads(msg[i:])
    return None


def rev_msg(q):
    Client, Address = ListenSocket.accept()
    Request = Client.recv(once_max_recv).decode(encoding='utf-8', errors='ignore')
    rev_json = request_to_json(Request)
    Client.sendall(HttpResponseHeader.encode(encoding='utf-8'))
    Client.close()
    q.put(rev_json)


if __name__ == '__main__':

    if not os.path.exists('files'):
        os.mkdir('files')

    logger.info("监控服务已开启......")

    while True:

        # 创建并启动新线程
        q = Queue()
        t = threading.Thread(target=rev_msg, args=(q,))
        t.start()
        t.join()
        result = q.get()

        qqapi.parse_message(result)

