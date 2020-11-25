from flask import request, g
from utils.jwt_util import verify_jwt

# @app.before_request
# def jwt_authentication():
#     pass


# app.before_request(jwt_authentication)


def jwt_authentication():
    # 获取请求头中的token
    # Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzb21lIjoicGF5bG9hZCJ9.4twF
    # t5NiznN84AWoo1d7KO1T_yoc0Z6XOpOVswacPZg

    g.user_id = None
    g.is_refresh = False

    token = request.headers.get('Authorization')
    if token is not None and token.startswith('Bearer '):
        token = token[7:]

        # 验证token
        payload = verify_jwt(token)

        if payload is not None:
            # 保存到g对象中
            g.user_id = payload.get('user_id')
            g.is_refresh = payload.get('is_refresh', False)