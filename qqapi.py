import math
import re
import time
import requests
from threading import Thread
from loggertool import Logger

import configparser

# 创建 ConfigParser 对象
config = configparser.ConfigParser()

# 读取配置文件
config.read('config.ini')

myqq = config['server']['my_qq']
local_ip = config['server']['local_ip']
server_ip = config['server']['server_ip']
receive_server_port = config['server']['receive_server_port']
nginx_port = config['nginx']['nginx_port']

logger = Logger().logger


# 定义方法发送QQ消息的线程
def send_private_msg(number, message):
    try:
        requests.get(url=f'http://{local_ip}:{receive_server_port}/send_private_msg?user_id={number}&message={message}')
    except Exception as e:
        logger.error(f'Error occurred: {e}')


# 将字节数转化为合适的大小单位
def bytes2human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    if n < 1000:
        return f"{n}B"
    else:
        order = int(math.log2(n) / 10)
        human_readable = n / (1 << (order * 10))
        return f"{human_readable:.1f}{symbols[order - 1]}"


# 下载图片的线程
def download_image(name, url):
    try:
        with open(f'./images/{name}.jpg', 'wb') as f:
            img = requests.get(url).content
            f.write(img)
    except Exception as e:
        logger.error(f'Error occurred: {e}')


# 下载文件的线程
def download_file(filename, url):
    try:
        with open(f'./files/{filename}', 'wb') as f:
            img = requests.get(url).content
            f.write(img)
    except Exception as e:
        logger.error(f'Error occurred: {e}')


# 记录图片和文件数据的线程
def list_msg(currenttime, nickname, name):
    try:
        with open('./allfiles', 'a') as f:
            f.write(
                f'\n【{currenttime}】----{nickname}----{name}----【http://{server_ip}:{nginx_port}/qqsource/images/{name}.jpg】')
    except Exception as e:
        logger.error(f'Error occurred: {e}')


def parse_message(rev):
    if rev["post_type"] == "message":
        # QQ文字及表情符号，和收藏的表情包
        if rev["message_type"] == "private":

            qq = rev['sender']['user_id']
            nickname = rev['sender']['nickname']
            message = rev['raw_message']
            currenttime = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(rev['time']))

            match = re.search(r'file=(\w+).*?url=(\S+)', message)

            if not match:  # 如果不匹配，说明是普通消息
                msg = f'【{currenttime}】\n收到来自{qq}的消息：\n【{message}】。'
                Thread(target=send_private_msg, args=(myqq, msg)).start()
                logger.info(f'收到来自【{qq}】的消息：----【{message}】。')

            else:  # 如果匹配，说明是一张图片
                name = match.group(1)
                url = match.group(2)

                # 启动下载图片的线程
                Thread(target=download_image, args=(name, url)).start()

                msg = f'【{currenttime}】\n收到来自【{qq}】的图片URL地址：'

                # 启动发送消息的线程
                Thread(target=send_private_msg, args=(myqq, msg)).start()
                Thread(target=send_private_msg,
                       args=(myqq, f'http://{local_ip}:{nginx_port}/qqsource/images/{name}.jpg')).start()

                # 启动记录数据的线程
                Thread(target=list_msg, args=(currenttime, nickname, name)).start()

                logger.info(f'收到来自【{qq}】的图片URL地址----【http://{server_ip}:{nginx_port}/qqsource/images/{name}.jpg】')

    if rev["post_type"] == 'notice' and rev['notice_type'] == 'offline_file':
        qq = rev['user_id']
        filename = rev['file']['name']
        size = bytes2human(int(rev['file']['size']))
        url = rev['file']['url']

        # 启动下载文件的线程
        Thread(target=download_file, args=(filename, url)).start()

        currenttime = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(rev['time']))

        msg = f'【{currenttime}】\n收到来自【{qq}】的文件：\n1.名称：{filename}\n2.大小：{size}\n3.URL：'

        # 启动记录数据的线程
        Thread(target=list_msg, args=(currenttime, qq, filename)).start()

        # 启动发送消息的线程
        Thread(target=send_private_msg, args=(myqq, msg)).start()
        Thread(target=send_private_msg, args=(myqq, f'http://{server_ip}:{nginx_port}/qqsource/files/{filename}')).start()

        logger.info(f'收到来自【{qq}】的文件----【名称：{filename}】----【大小：{size}】----【URL：http://{server_ip}:{nginx_port}/qqsource/files/{filename}】')
