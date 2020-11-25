from server import sio, JWT_SECRET
from werkzeug.wrappers import Request
from utils.jwt_util import verify_jwt


def check_jwt_token(token):
    """
    检验jwt token
    :param token:
    :return:
    """
    payload = verify_jwt(token, JWT_SECRET)
    if payload is None:
        return None
    else:
        return payload.get('user_id')


@sio.on('connect')
def on_connect_notify(sid, environ):
    """
    当客户连接时被执行
    :param sid:
    :param environ: dict 解析客户端握手的http数据
    :return:
    """
    # 借助werkzeug提供的Request类，将environ字典转换为我们熟悉的request对象，从对象中读取属性的方式来获取客户端的请求信息
    request = Request(environ)  # 等价于flask 的request对象

    # 从查询字符串中取出jwt token
    token = request.args.get('token')

    # 验证jwt token
    # 如果有效 取出了user_id 将用户添加到user_id的房间
    user_id = check_jwt_token(token)
    if user_id is not None:
        sio.enter_room(sid, str(user_id))


@sio.on('disconnect')
def on_disconnect(sid):
    """
    当用户断开连接时被执行
    :param sid:
    :return:
    """
    # 将用户从专属vip包房剔除
    rooms = sio.rooms(sid)

    for room in rooms:
        sio.leave_room(sid, room)





