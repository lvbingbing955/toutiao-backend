from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask import g, current_app
from sqlalchemy.exc import IntegrityError
import time

from utils.decorators import login_required, set_db_to_write
from utils import parser
from models import db
from models.news import Attitude, ArticleStatistic, CommentLiking, Comment
from cache import comment as cache_comment
from cache import article as cache_article
from cache import user as cache_user
from cache import statistic as cache_statistic


class ArticleLikingListResource(Resource):
    """
    文章点赞
    """
    method_decorators = [login_required]

    def post(self):
        """
        文章点赞
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.article_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target

        # 此次操作前，用户对文章可能是没有态度，也可能是不喜欢，需要先查询对文章的原始态度，然后对相应的统计数据进行累计或减少
        atti = Attitude.query.filter_by(user_id=g.user_id, article_id=target).first()
        if atti is None:
            attitude = Attitude(user_id=g.user_id, article_id=target, attitude=Attitude.ATTITUDE.LIKING)
            db.session.add(attitude)
            db.session.commit()
            cache_statistic.ArticleLikingCountStorage.incr(target)
        else:
            if atti.attitude == Attitude.ATTITUDE.DISLIKE:
                # 原先是不喜欢
                atti.attitude = Attitude.ATTITUDE.LIKING
                db.session.add(atti)
                db.session.commit()
                cache_statistic.ArticleLikingCountStorage.incr(target)
                cache_statistic.ArticleDislikeCountStorage.incr(target, -1)
                cache_statistic.UserLikedCountStorage.incr(g.user_id)
            elif atti.attitude is None:
                # 存在数据，但是无态度
                atti.attitude = Attitude.ATTITUDE.LIKING
                db.session.add(atti)
                db.session.commit()
                cache_statistic.ArticleLikingCountStorage.incr(target)
                cache_statistic.UserLikedCountStorage.incr(g.user_id)

        # cache_article.ArticleUserAttitudeCache(g.user_id, target).clear()
        cache_user.UserArticleAttitudeCache(g.user_id).clear()

        # 发送点赞通知
        _user = cache_user.UserProfileCache(g.user_id).get()
        _article = cache_article.ArticleInfoCache(target).get()
        _data = {
            'user_id': g.user_id,
            'user_name': _user['name'],
            'user_photo': _user['photo'],
            'art_id': target,
            'art_title': _article['title'],
            'timestamp': int(time.time())
        }
        # current_app.sio.emit('liking notify', data=_data, room=str(_article['aut_id']))

        return {'target': target}, 201


class ArticleLikingResource(Resource):
    """
    文章点赞
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消文章点赞
        """
        ret = Attitude.query.filter_by(user_id=g.user_id, article_id=target, attitude=Attitude.ATTITUDE.LIKING) \
            .update({'attitude': None})
        db.session.commit()

        if ret > 0:
            cache_statistic.ArticleLikingCountStorage.incr(target, -1)
            cache_statistic.UserLikedCountStorage.incr(g.user_id, -1)
            # cache_article.ArticleUserAttitudeCache(g.user_id, target).clear()
            cache_user.UserArticleAttitudeCache(g.user_id).clear()
        return {'message': 'OK'}, 204


class CommentLikingListResource(Resource):
    """
    评论点赞
    """
    method_decorators = [login_required]

    def post(self):
        """
        评论点赞
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.comment_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target
        ret = 1
        try:
            comment_liking = CommentLiking(user_id=g.user_id, comment_id=target)
            db.session.add(comment_liking)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            ret = CommentLiking.query.filter_by(user_id=g.user_id, comment_id=target, is_deleted=True) \
                .update({'is_deleted': False})
            db.session.commit()

        if ret > 0:
            cache_statistic.CommentLikingCountStorage.incr(target)
            cache_user.UserCommentLikingCache(g.user_id).clear()
        return {'target': target}, 201


class CommentLikingResource(Resource):
    """
    评论点赞
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消对评论点赞
        """
        ret = CommentLiking.query.filter_by(user_id=g.user_id, comment_id=target, is_deleted=False) \
            .update({'is_deleted': True})
        db.session.commit()
        if ret > 0:
            cache_statistic.CommentLikingCountStorage.incr(target, -1)
            cache_user.UserCommentLikingCache(g.user_id).clear()
        return {'message': 'OK'}, 204
