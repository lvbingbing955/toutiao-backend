import socketio

# rabbitmq地址
RABBITMQ = 'amqp://python:rabbitmqpwd@localhost:5672/toutiao'
JWT_SECRET = 'TPmi4aLWRbyVq8zu9v82dWYW17/z+UvRnYTt4P6fAXA'

# 创建读取rabbitmq消息队列的管理对象
mgr = socketio.KombuManager(RABBITMQ)

# 创建socketio服务器对象
sio = socketio.Server(async_mode='eventlet', client_manager=mgr)


# app对象是交给eventlet协程服务器使用对接的向
app = socketio.Middleware(sio)


