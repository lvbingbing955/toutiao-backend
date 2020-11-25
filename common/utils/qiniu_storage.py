from qiniu import Auth, put_file, etag, put_data
from flask import current_app

import qiniu.config


def upload(file_data):
    """
    上传到七牛云服务
    :param file_data: 视图接收到的图片二进制数据
    :return:
    """
    # 需要填写你的 Access Key 和 Secret Key
    access_key = current_app.config['QINIU_ACCESS_KEY']
    secret_key = current_app.config['QINIU_SECRET_KEY']

    # 构建鉴权对象
    q = Auth(access_key, secret_key)

    # 要上传的空间
    bucket_name = current_app.config['QINIU_BUCKET_NAME']
    print('ak={}'.format(access_key))
    print('sk={}'.format(secret_key))
    print('bn={}'.format(bucket_name))

    # 上传后保存的文件名
    # key = 'my-python-logo.png'
    key = None

    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 360000)
    print('token={}'.format(token))

    # 要上传文件的本地路径
    # localfile = './sync/bbb.jpg'
    # ret, info = put_file(token, key, localfile)

    # 指明要上传的图片的二进制内容
    ret, info = put_data(token, key, file_data)

    print('ret={}'.format(ret))
    print('info={}'.format(info))
    # ret={'hash': 'Fv9NW-O8Ysg0ytgK6uggLaJjfk6z', 'key': 'Fv9NW-O8Ysg0ytgK6uggLaJjfk6z'}
    # info=_ResponseInfo__response:<Response [200]>,

    # 返回文件名
    return ret['key']