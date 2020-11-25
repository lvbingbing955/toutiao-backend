from server import sio
import time


# 跟客户端的约定，
# 对于聊天场景，通讯时使用message事件
# 在聊天的通讯中，传输的聊天数据约定格式
# {
#     "msg": "",
#     "timestamp": 发送或接受消息的时间戳
# }


@sio.on('connect')
def on_connect(sid, environ):
    """
    在客户端连接之后被执行
    :return:
    """
    print('sid={}'.format(sid))
    print('environ={}'.format(environ))

    # 向客户端发送事件消息
    msg_data = {
        'msg': 'hello',
        'timestamp': round(time.time()*1000)
    }
    sio.emit('message', msg_data, room=sid)
    # sio.send(msg_data, room=sid)


@sio.on('message')
def on_message(sid, data):
    """
    客户端向服务器发送聊天的事件消息时 被调用
    :param sid:
    :param data:
    :return:
    """
    # 获取用户说的信息 data

    # TODO 使用rpc 调用聊天机器人子系统 获取回复内容

    msg_data = {
        'msg': 'I have received your msg: {}'.format(data),
        'timestamp': round(time.time()*1000)
    }
    sio.send(msg_data, room=sid)


