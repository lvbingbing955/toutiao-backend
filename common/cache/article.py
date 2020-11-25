from sqlalchemy.orm import joinedload, load_only
from flask_restful import fields, marshal
import json
import time
from sqlalchemy import func
from flask import current_app
from redis.exceptions import RedisError, ConnectionError
from sqlalchemy.exc import SQLAlchemyError

from models.news import Article, ArticleStatistic, Attitude
from models.user import User
from models import db
from cache import user as cache_user
from . import constants
from cache import statistic as cache_statistic


# # 无用
# article_info_fields_redis = {
#     'title': fields.String(attribute=b'title'),
#     'aut_id': fields.Integer(attribute=b'aut_id'),
#     # 'aut_name': fields.String(attribute=b'aut_name'),
#     'comm_count': fields.Integer(attribute=b'comm_count'),
#     'pubdate': fields.String(attribute=b'pubdate'),
#     'is_top': fields.Integer(attribute=b'is_top'),
#     'ch_id': fields.Integer(attribute=b'ch_id')
# }


# # 无用
# def get_channel_top_articles_count(channel_id):
#     """
#     获取指定频道的置顶文章的数量
#     :param channel_id: 频道id
#     :return: int
#     """
#     r = current_app.redis_cli['art_cache']
#
#     ret = r.zcard('ch:{}:art:top'.format(channel_id))
#     return ret


class ArticleInfoCache(object):
    """
    文章基本信息缓存
    """
    article_info_fields_db = {
        'title': fields.String(attribute='title'),
        'aut_id': fields.Integer(attribute='user_id'),
        'pubdate': fields.DateTime(attribute='ctime', dt_format='iso8601'),
        'ch_id': fields.Integer(attribute='channel_id'),
        'allow_comm': fields.Integer(attribute='allow_comment'),
    }

    def __init__(self, article_id):
        self.key = 'art:{}:info'.format(article_id)
        self.article_id = article_id

    def save(self):
        """
        保存文章缓存
        """
        rc = current_app.redis_cluster

        article = Article.query.options(load_only(Article.id, Article.title, Article.user_id, Article.channel_id,
                                                  Article.cover, Article.ctime, Article.allow_comment))\
            .filter_by(id=self.article_id, status=Article.STATUS.APPROVED).first()
        if article is None:
            return

        article_formatted = marshal(article, self.article_info_fields_db)
        article_formatted['cover'] = article.cover

        # 判断是否置顶
        try:
            article_formatted['is_top'] = ChannelTopArticlesStorage(article.channel_id).exists(self.article_id)
        except RedisError as e:
            current_app.logger.error(e)
            article_formatted['is_top'] = 0

        try:
            rc.setex(self.key, constants.ArticleInfoCacheTTL.get_val(), json.dumps(article_formatted))
        except RedisError as e:
            current_app.logger.error(e)

        return article_formatted

    def _fill_fields(self, article_formatted):
        """
        补充字段
        """
        article_formatted['art_id'] = self.article_id
        # 获取作者名
        author = cache_user.UserProfileCache(article_formatted['aut_id']).get()
        article_formatted['aut_name'] = author['name']
        article_formatted['comm_count'] = cache_statistic.ArticleCommentCountStorage.get(self.article_id)
        article_formatted['like_count'] = cache_statistic.ArticleLikingCountStorage.get(self.article_id)
        article_formatted['collect_count'] = cache_statistic.ArticleCollectingCountStorage.get(self.article_id)
        return article_formatted

    def get(self):
        """
        获取文章
        :return: {}
        """
        rc = current_app.redis_cluster

        # 从缓存中查询
        try:
            article = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            article = None

        if article:
            article_formatted = json.loads(article)
        else:
            article_formatted = self.save()

        if not article_formatted:
            return None

        article_formatted = self._fill_fields(article_formatted)
        del article_formatted['allow_comm']

        return article_formatted

    def exists(self):
        """
        判断文章是否存在
        :return: bool
        """
        rc = current_app.redis_cluster

        # 此处可使用的键有三种选择 user:{}:profile 或 user:{}:status 或 新建
        # status主要为当前登录用户，而profile不仅仅是登录用户，覆盖范围更大，所以使用profile
        try:
            ret = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret is not None:
            return False if ret == b'-1' else True
        else:
            # 缓存中未查到
            article = self.save()
            if article is None:
                return False
            else:
                return True

    def determine_allow_comment(self):
        """
        判断是否允许评论
        """
        rc = current_app.redis_cluster
        try:
            ret = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret is None:
            article_formatted = self.save()
        else:
            article_formatted = json.loads(ret)

        return article_formatted['allow_comm']

    def clear(self):
        rc = current_app.redis_cluster
        rc.delete(self.key)


class ChannelTopArticlesStorage(object):
    """
    频道置顶文章缓存
    使用redis持久保存
    """
    def __init__(self, channel_id):
        self.key = 'ch:{}:art:top'.format(channel_id)
        self.channel_id = channel_id

    def get(self):
        """
        获取指定频道的置顶文章id
        :return: [article_id, ...]
        """
        try:
            ret = current_app.redis_master.zrevrange(self.key, 0, -1)
        except ConnectionError as e:
            current_app.logger.error(e)
            ret = current_app.redis_slave.zrevrange(self.key, 0, -1)

        if not ret:
            return []
        else:
            return [int(article_id) for article_id in ret]

    def exists(self, article_id):
        """
        判断文章是否置顶
        :param article_id:
        :return:
        """
        try:
            rank = current_app.redis_master.zrank(self.key, article_id)
        except ConnectionError as e:
            current_app.logger.error(e)
            rank = current_app.redis_slave.zrank(self.key, article_id)

        return 0 if rank is None else 1


class ArticleDetailCache(object):
    """
    文章详细内容缓存
    """
    article_fields = {
        'art_id': fields.Integer(attribute='id'),
        'title': fields.String(attribute='title'),
        'pubdate': fields.DateTime(attribute='ctime', dt_format='iso8601'),
        'content': fields.String(attribute='content.content'),
        'aut_id': fields.Integer(attribute='user_id'),
        'ch_id': fields.Integer(attribute='channel_id'),
    }

    def __init__(self, article_id):
        self.key = 'art:{}:detail'.format(article_id)
        self.article_id = article_id

    def get(self):
        """
        获取文章详情信息
        :return:
        """
        # 查询文章数据
        rc = current_app.redis_cluster
        try:
            article_bytes = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            article_bytes = None

        if article_bytes:
            # 使用缓存
            article_dict = json.loads(article_bytes)
        else:
            # 查询数据库
            article = Article.query.options(load_only(
                Article.id,
                Article.user_id,
                Article.title,
                Article.is_advertising,
                Article.ctime,
                Article.channel_id
            )).filter_by(id=self.article_id, status=Article.STATUS.APPROVED).first()

            article_dict = marshal(article, self.article_fields)

            # 缓存
            article_cache = json.dumps(article_dict)
            try:
                rc.setex(self.key, constants.ArticleDetailCacheTTL.get_val(), article_cache)
            except RedisError:
                pass

        user = cache_user.UserProfileCache(article_dict['aut_id']).get()

        article_dict['aut_name'] = user['name']
        article_dict['aut_photo'] = user['photo']

        return article_dict

    def clear(self):
        current_app.redis_cluster.delete(self.key)


class ArticleUserAttitudeCache(object):
    """
    用户对文章态度的缓存，点赞或不喜欢
    """
    def __init__(self, user_id, article_id):
        self.user_id = user_id
        self.article_id = article_id
        self.key = 'user:{}:art:{}:liking'.format(user_id, article_id)

    def get(self):
        """
        获取
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret is not None:
            ret = int(ret)
            return ret

        att = Attitude.query.options(load_only(Attitude.attitude)) \
            .filter_by(user_id=self.user_id, article_id=self.article_id).first()
        ret = att.attitude if att and att.attitude else -1

        try:
            rc.setex(self.key, constants.ArticleUserNoAttitudeCacheTTL.get_val(), int(ret))
        except RedisError as e:
            current_app.logger.error(e)

        return ret

    def clear(self):
        """
        清除
        :return:
        """
        rc = current_app.redis_cluster
        try:
            rc.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)


