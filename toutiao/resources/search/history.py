from flask_restful import Resource
from flask import g
from sqlalchemy.orm import load_only

from utils.decorators import login_required
from models.user import Search
from . import constants
from models import db
from cache import user as cache_user


class HistoryListResource(Resource):
    """
    搜索历史
    """
    method_decorators = [login_required]

    def get(self):
        """
        获取用户搜索历史
        """
        ret = cache_user.UserSearchingHistoryStorage(g.user_id).get()
        return {'keywords': ret}

    def delete(self):
        """
        删除搜索历史
        """
        cache_user.UserSearchingHistoryStorage(g.user_id).clear()
        return {'message': 'OK'}, 204
