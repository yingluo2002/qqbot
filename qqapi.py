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


# 获取撤回的消息
def get_recall_msg(id):
    try:
        msg = requests.get(url=f'http://{local_ip}:{receive_server_port}/get_msg?message_id={id}').json()
        return msg
    except Exception as e:
        logger.error(f'Error occurred: {e}')


# 根据group_id获取群名
def get_group_name_by_id(id):
    try:
        msg = requests.get(url=f'http://{local_ip}:{receive_server_port}/get_group_info?group_id={id}').json()
        return msg['data']['group_memo'] if 'group_memo' in msg['data'] else msg['data']['group_name']
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


# 下载文件的线程
def download_file(filename, url):
    try:
        with open(f'./files/{filename}', 'wb') as f:
            img = requests.get(url).content
            f.write(img)
    except Exception as e:
        logger.error(f'Error occurred: {e}')


def parse_message(rev):
    if 'notice_type' in rev and rev['notice_type'] in ['friend_recall', 'group_recall']:
        message = get_recall_msg(rev['message_id'])
        recall_time = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(rev['time']))
        recall_qq = f"{rev['user_id']}(来自群：{get_group_name_by_id(rev['group_id'])})" if 'group_id' in rev else rev['user_id']

        # 可能的bug
        if 'data' in message and message['data'] is None:
            return

        if 'data' in message and 'message' in message['data']:

            raw_message = message['data']['message']
            send_time = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(message['data']['time']))

            match = re.search(r'file=(\w+).*?url=(\S+)', raw_message)

            if not match:  # 如果不匹配，说明是普通消息
                msg = f'收到{recall_qq}撤回的消息：\n【{raw_message}】\n发送时间：【{send_time}】\n撤回时间：【{recall_time}】。'
                Thread(target=send_private_msg, args=(myqq, msg)).start()
                logger.info(f'【{recall_qq}】撤回一条消息：----【{raw_message}】。')

            else:  # 如果匹配，说明是一张图片
                url = match.group(2)

                msg = f'收到{recall_qq}撤回的图片：\n-------------------------\n{raw_message}-------------------------\n发送时间：【{send_time}】\n撤回时间：【{recall_time}】。'

                # 启动发送消息的线程
                Thread(target=send_private_msg, args=(myqq, msg)).start()

                logger.info(f'【{recall_qq}】撤回一张图片：----【{url}】。')

    if 'post_type' in rev and 'notice_type' in rev and rev["post_type"] == 'notice' and rev['notice_type'] in ['offline_file', 'group_upload']:

        qq = f"{rev['user_id']}(来自群：{get_group_name_by_id(rev['group_id'])})" if 'group_id' in rev else rev['user_id']
        filename = rev['file']['name']
        size = bytes2human(int(rev['file']['size']))
        url = rev['file']['url']

        # 启动下载文件的线程
        Thread(target=download_file, args=(filename, url)).start()

        currenttime = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(rev['time']))

        msg = f'【{currenttime}】\n收到来自【{qq}】的文件：\n1.名称：{filename}\n2.大小：{size}。'

        # 启动发送消息的线程
        Thread(target=send_private_msg, args=(myqq, msg)).start()
        Thread(target=send_private_msg,
               args=(myqq, f'http://{server_ip}:{nginx_port}/qqsource/files/{filename}')).start()

        logger.info(
            f'收到来自【{qq}】的文件----【名称：{filename}】----【大小：{size}】----【URL：http://{server_ip}:{nginx_port}/qqsource/files/{filename}】')
