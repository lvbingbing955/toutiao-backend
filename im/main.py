import eventlet
# 将所有用到的系统标准io函数替换成eventlet提供的同名函数，方便eventlet可以自动切换协程
eventlet.monkey_patch()

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))

import socketio
import eventlet.wsgi
from server import app

# 通过sys模块 获取启动命令中的参数  sys.argv
# # python main.py 8001 ...
# sys.argv -> ['main.py', '8001', ...]
if len(sys.argv) < 2:
    # 表示启动时忘了传递端口号参数
    print('Usage: python main.py [port]')
    exit(1)  # 表示程序异常退出


port = int(sys.argv[1])

# 通过导入事件处理模块的方法，让主程序知道事件处理方法的存在
import chat
import notify

# 创建协程服务器 并启动
# SERVER_ADDRESS = ('', 8000)

# 需求 想要将端口不写死在程序代码中，想要在启动的时候执行端口号
# python server.py [port]
# python server.py 8001
SERVER_ADDRESS = ('', port)
sock = eventlet.listen(SERVER_ADDRESS)
eventlet.wsgi.server(sock, app)

