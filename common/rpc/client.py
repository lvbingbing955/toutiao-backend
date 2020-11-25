import grpc
import reco_pb2_grpc
import reco_pb2
import time


def feed_articles(stub):
    """
    rpc调用推荐接口
    :return:
    """
    user_request = reco_pb2.UserRequest()
    user_request.user_id = '1'
    user_request.channel_id = 1
    user_request.article_num = 10
    user_request.time_stamp = round(time.time()*1000)

    ret = stub.user_recommend(user_request)
    # ret -> ArticleResponse 对象
    print('ret={}'.format(ret))


def run():
    # 构建连接rpc服务器的对象
    with grpc.insecure_channel('127.0.0.1:8888') as channel:
        # 创建调用的辅助工具对象 stub
        stub = reco_pb2_grpc.UserRecommendStub(channel)

        # 可以通过stub进行rpc调用
        # ret = stub.user_recommend()
        feed_articles(stub)

    #
    # with open() as f:
    #     ....
    #     # f.clos()

if __name__ == '__main__':
    run()