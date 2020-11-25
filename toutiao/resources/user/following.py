from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from sqlalchemy.exc import IntegrityError
from flask import g, current_app
from flask_restful import inputs
import time

from utils.decorators import login_required, set_db_to_read, set_db_to_write
from models.user import Relation, User
from utils import parser
from models import db
from cache import user as cache_user
from cache import statistic as cache_statistic
from . import constants


class FollowingListResource(Resource):
    """
    关注用户
    """
    method_decorators = {
        'post': [login_required],
        'get': [login_required],
    }

    def post(self):
        """
        关注用户
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.user_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target
        if target == g.user_id:
            return {'message': 'User cannot follow self.'}, 400
        ret = 1
        try:
            follow = Relation(user_id=g.user_id, target_user_id=target, relation=Relation.RELATION.FOLLOW)
            db.session.add(follow)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            ret = Relation.query.filter(Relation.user_id == g.user_id,
                                        Relation.target_user_id == target,
                                        Relation.relation != Relation.RELATION.FOLLOW)\
                .update({'relation': Relation.RELATION.FOLLOW})
            db.session.commit()

        if ret > 0:
            timestamp = time.time()
            cache_user.UserFollowingCache(g.user_id).update(target, timestamp)
            cache_user.UserFollowersCache(target).update(g.user_id, timestamp)
            cache_statistic.UserFollowingsCountStorage.incr(g.user_id)
            cache_statistic.UserFollowersCountStorage.incr(target)
            cache_user.UserRelationshipCache(g.user_id).clear()

        # 发送关注通知
        _user = cache_user.UserProfileCache(g.user_id).get()
        _data = {
            'user_id': g.user_id,
            'user_name': _user['name'],
            'user_photo': _user['photo'],
            'timestamp': int(time.time())
        }
        # 通过socketio提供的kombu管理对象 向rabbitmq中写入数据，记录需要由socketio服务器向客户端推送消息的任务
        current_app.sio_mgr.emit('following notify', data=_data, room=str(target))

        return {'target': target}, 201

    def get(self):
        """
        获取关注的用户列表
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MIN,
                                                                 constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MIN

        results = []
        followings = cache_user.UserFollowingCache(g.user_id).get()
        followers = cache_user.UserFollowersCache(g.user_id).get()
        total_count = len(followings)
        req_followings = followings[(page-1)*per_page:page*per_page]
        for following_user_id in req_followings:
            user = cache_user.UserProfileCache(following_user_id).get()
            results.append(dict(
                id=following_user_id,
                name=user['name'],
                photo=user['photo'],
                fans_count=user['fans_count'],
                mutual_follow=following_user_id in followers
            ))

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class FollowingResource(Resource):
    """
    关注用户
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消关注用户
        """
        ret = Relation.query.filter(Relation.user_id == g.user_id,
                                    Relation.target_user_id == target,
                                    Relation.relation == Relation.RELATION.FOLLOW)\
            .update({'relation': Relation.RELATION.DELETE})
        db.session.commit()

        if ret > 0:
            timestamp = time.time()
            cache_user.UserFollowingCache(g.user_id).update(target, timestamp, -1)
            cache_user.UserFollowersCache(target).update(g.user_id, timestamp, -1)
            cache_statistic.UserFollowingsCountStorage.incr(g.user_id, -1)
            cache_statistic.UserFollowersCountStorage.incr(target, -1)
            cache_user.UserRelationshipCache(g.user_id).clear()
        return {'message': 'OK'}, 204


class FollowerListResource(Resource):
    """
    跟随用户列表（粉丝列表）
    """
    method_decorators = [login_required]

    def get(self):
        """
        获取粉丝列表
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MIN,
                                                                 constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MIN

        results = []
        followers = cache_user.UserFollowersCache(g.user_id).get()
        followings = cache_user.UserFollowingCache(g.user_id).get()
        total_count = len(followers)
        req_followers = followers[(page - 1) * per_page:page * per_page]
        for follower_user_id in req_followers:
            user = cache_user.UserProfileCache(follower_user_id).get()
            results.append(dict(
                id=follower_user_id,
                name=user['name'],
                photo=user['photo'],
                fans_count=user['fans_count'],
                mutual_follow=follower_user_id in followings
            ))

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}

