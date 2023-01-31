import configparser
import math
import os
import time
from threading import Thread

import requests

from loggertool import Logger

# 创建 ConfigParser 对象
config = configparser.ConfigParser()

# 读取配置文件
config.read('config.ini')

myqq = config['server']['my_qq']
local_ip = config['server']['local_ip']
server_ip = config['server']['server_ip']
receive_server_port = config['server']['receive_server_port']
file_middle_path = config['server']['file_middle_path']
delete_middle_file = config['server']['delete_middle_file']

logger = Logger().logger


# 定义方法发送QQ消息的线程
def send_private_msg(user_id, message):
    try:
        data = {
            'user_id': user_id,
            'message': message
        }
        requests.get(url=f'http://{local_ip}:{receive_server_port}/send_private_msg', params=data)
    except Exception as e:
        logger.error(f'Error occurred: {e}')


# 获取撤回的消息
def get_recall_msg(message_id):
    try:
        msg = requests.get(url=f'http://{local_ip}:{receive_server_port}/get_msg?message_id={message_id}').json()
        return msg
    except Exception as e:
        logger.error(f'Error occurred: {e}')
        return None


# 根据user_id获取其备注
def get_remark(user_id):
    try:
        data = requests.get(url=f'http://{local_ip}:{receive_server_port}/get_friend_list').json()
        result = next((item['remark'] for item in data['data'] if item['user_id'] == user_id), user_id)
        return result
    except Exception as e:
        logger.error(f'Error occurred: {e}')
        return None


# 根据group_id获取群名
def get_group_name_by_id(id):
    try:
        msg = requests.get(url=f'http://{local_ip}:{receive_server_port}/get_group_info?group_id={id}').json()
        return msg['data']['group_memo'] if 'group_memo' in msg['data'] else msg['data']['group_name']
    except Exception as e:
        logger.error(f'Error occurred: {e}')
        return None


# 将字节数转化为合适的大小单位
def bytes2human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    if n < 1000:
        return f"{n}B"
    else:
        order = int(math.log2(n) / 10)
        human_readable = n / (1 << (order * 10))
        return f"{human_readable:.1f}{symbols[order - 1]}"


# 发送文件的线程
def send_file(filename, url, user_id):
    try:
        file = os.path.join(file_middle_path, filename)
        with open(file, 'wb') as f:
            stream = requests.get(url).content
            f.write(stream)
        data = {
            'user_id': user_id,
            'file': file,
            'name': filename
        }
        requests.get(url=f'http://{local_ip}:{receive_server_port}/upload_private_file', params=data)

        if delete_middle_file == 'true':
            os.remove(file)

    except Exception as e:
        logger.error(f'Error occurred: {e}')


def parse_message(rev):
    if 'notice_type' in rev and rev['notice_type'] in ['friend_recall', 'group_recall']:
        message = get_recall_msg(rev['message_id'])
        recall_time = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime())
        remark = get_remark(rev['user_id'])
        remark = f"{remark}(来自群：{get_group_name_by_id(rev['group_id'])})" if 'group_id' in rev else remark

        # 可能的bug
        if 'data' in message and message['data'] is None:
            return

        if 'data' in message and 'message' in message['data']:
            raw_message = message['data']['message']
            send_time = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(message['data']['time']))

            if raw_message == '&#91;&#91;QQ小程序&#93;收集表&#93;请使用最新版本手机QQ查看':
                raw_message = 'QQ收集表（暂不支持查看）'

            msg = f'收到【{remark}】撤回的消息：\n-------------------------\n{raw_message}\n-------------------------\n发送于【{send_time}】\n撤回于【{recall_time}】'

            Thread(target=send_private_msg, args=(myqq, msg)).start()
            logger.info(f'【{remark}】撤回一条消息：----【{raw_message}】。')

            return

    if 'post_type' in rev and 'notice_type' in rev and rev["post_type"] == 'notice' and rev['notice_type'] in ['offline_file', 'group_upload']:

        remark = get_remark(rev['user_id'])
        remark = f"{remark}(来自群：{get_group_name_by_id(rev['group_id'])})" if 'group_id' in rev else remark
        filename = rev['file']['name']
        size = bytes2human(int(rev['file']['size']))
        url = rev['file']['url']

        # 启动发送文件的线程
        Thread(target=send_file, args=(filename, url, myqq)).start()

        currenttime = time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(rev['time']))

        msg = f'【{currenttime}】\n收到来自【{remark}】的文件：\n1.名称：{filename}\n2.大小：{size}。'

        # 启动发送消息的线程
        Thread(target=send_private_msg, args=(myqq, msg)).start()

        logger.info(
            f'收到来自【{remark}】的文件----【名称：{filename}】----【大小：{size}】。')
        return
