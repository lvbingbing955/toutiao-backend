import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE_DIR))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))

import unittest
import json

from toutiao import create_app
from settings.testing import TestingConfig


class SuggestionTestCase(unittest.TestCase):
    """
    用于测试搜索联想建议接口的测试案例
    """
    def setUp(self):
        """
        在其他测试方法执行前先被执行
        :return:
        """
        flask_app = create_app(TestingConfig)
        self.test_client = flask_app.test_client()

    def test_normal_request(self):
        """
        测试接口发送正常请求的场景
        :return:
        """
        # 构造一个http的请求
        # 方式1. 使用其他http模块（urllib2 requests)，要求被测试的框架程序要处于运行状态
        # 方式2， 使用框架程序提供的单元测试客户端（flask app.test_client)
        # 请求GET /v1_0/suggestion
        resp = self.test_client.get('/v1_0/suggestion?q=python%20web')

        # 接收视图处理的响应信息
        # 判断响应信息的数据是否符合预期
        # 添加一个预期断言，如果视图编写没有bug，此处收到的状态码应该为200
        self.assertEqual(resp.status_code, 200)  # 响应状态码

        # resp.data 原始响应体数据 （json 字符串）
        # {
        #     "message": "OK",
        #     "data": {
        #         "options": [
        #             "python web框架的介绍"
        #         ]
        #     }
        # }
        resp_json = resp.data
        resp_dict = json.loads(resp_json)

        self.assertIn('message', resp_dict)
        self.assertIn('data', resp_dict)
        data = resp_dict['data']
        self.assertIn('options', data)

    def test_missing_request_param_q(self):
        """
        测试接口请求时缺少参数q的场景
        :return:
        """
        resp = self.test_client.get('/v1_0/suggestion')
        self.assertEqual(resp.status_code, 400)  # 响应状态码

    def test_request_param_q_length_error(self):
        """
        测试接口请求时q参数超过长度限制
        :return:
        """
        resp = self.test_client.get('/v1_0/suggestion?q='+'e'*51)
        self.assertEqual(resp.status_code, 400)  # 响应状态码


if __name__ == '__main__':
    unittest.main()
