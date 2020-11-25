import reco_pb2_grpc
import reco_pb2
import time
import grpc
from concurrent.futures import ThreadPoolExecutor


# 首先补全被调用的函数代码
class UserRecommendServicer(reco_pb2_grpc.UserRecommendServicer):
    """
    通过子类继承重写的方式
    """
    def user_recommend(self, request, context):
        """
        在接口中定义的用户推荐方法
        :param request:  调用时的请求参数对象  UserRequest
        :param context:  通过此对象可以设置调用返回的异常信息
        :return:
        """
        # 获取调用的参数
        user_id = request.user_id
        channel_id = request.channel_id
        article_num = request.article_num
        time_stamp = request.time_stamp

        # 决定调用返回数据
        resp = reco_pb2.ArticleResponse()
        resp.exposure = 'exposure param'
        resp.time_stamp = round(time.time() * 1000)

        _recommends = []
        for i in range(article_num):
            article = reco_pb2.Article()
            article.article_id = i+1
            article.track.click = 'click param'
            article.track.collect = 'collect param'
            article.track.share = 'share param'
            article.track.read = 'read param'
            _recommends.append(article)

        # 注意 对于列表类型的赋值使用extend
        resp.recommends.extend(_recommends)

        return resp


# 创建rpc的服务器
def serve():
    """
    rpc服务端启动方法
    """
    # 创建一个rpc服务器
    server = grpc.server(ThreadPoolExecutor(max_workers=10))

    # 将自己实现的被调用方法与服务器绑定
    reco_pb2_grpc.add_UserRecommendServicer_to_server(UserRecommendServicer(), server)

    # 绑定ip地址和端口
    server.add_insecure_port('127.0.0.1:8888')

    # 开启服务器运行, start()方法是非阻塞方法
    server.start()

    while True:
        time.sleep(100)


if __name__ == '__main__':
    serve()
