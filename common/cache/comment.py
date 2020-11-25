from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import func
from flask_restful import marshal, fields
import time
from flask import current_app
from redis.exceptions import RedisError
import json

from models import db
from models.user import User
from models.news import Comment
from cache import user as cache_user
from . import constants
from cache import statistic as cache_statistic


class CommentCache(object):
    """
    评论信息缓存
    """
    comment_fields = {
        'com_id': fields.Integer(attribute='id'),
        'aut_id': fields.Integer(attribute='user_id'),
        'pubdate': fields.DateTime(attribute='ctime', dt_format='iso8601'),
        'content': fields.String(attribute='content'),
        'is_top': fields.Integer(attribute='is_top')
    }

    def __init__(self, comment_id):
        self.key = 'comm:{}'.format(comment_id)
        self.comment_id = comment_id

    def get(self):
        """
        获取
        """
        rc = current_app.redis_cluster
        try:
            comment = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            return None
        else:
            if comment is None:
                return None
            comment = json.loads(comment)
            comment = CommentCache.fill_fields(comment)
            return comment

    @classmethod
    def fill_fields(cls, comment):
        """
        补充字段
        :param comment:
        :return:
        """
        _user = cache_user.UserProfileCache(comment['aut_id']).get()
        comment['aut_name'] = _user['name']
        comment['aut_photo'] = _user['photo']
        comment['like_count'] = cache_statistic.CommentLikingCountStorage.get(comment['com_id'])
        comment['reply_count'] = cache_statistic.CommentReplyCountStorage.get(comment['com_id'])
        return comment

    @classmethod
    def get_list(cls, comment_ids):
        """
        批量获取
        """
        rc = current_app.redis_cluster

        comments = {}
        need_db_query = []
        sorted_comments = []

        # 从缓存查询，没有就记录
        for comment_id in comment_ids:
            comment = CommentCache(comment_id).get()
            if comment is None:
                need_db_query.append(comment_id)
            else:
                comments[comment_id] = comment
                sorted_comments.append(comment)

        # 数据库查询缓存缺失的
        if not need_db_query:
            return sorted_comments
        else:
            ret = Comment.query.filter(Comment.id.in_(need_db_query),
                                       Comment.status == Comment.STATUS.APPROVED).all()
            pl = rc.pipeline()
            for comment in ret:
                # 处理序列化
                formatted_comment = marshal(comment, cls.comment_fields)

                # 保存缓存
                pl.setex(CommentCache(comment.id).key, constants.CommentCacheTTL.get_val(), json.dumps(formatted_comment))

                # 处理字段
                formatted_comment = cls.fill_fields(formatted_comment)
                comments[comment.id] = formatted_comment

            try:
                pl.execute()
            except RedisError as e:
                current_app.logger.error(e)

            # 排序
            sorted_comments = []
            for comment_id in comment_ids:
                sorted_comments.append(comments[comment_id])
            return sorted_comments

    def exists(self):
        """
        判断缓存是否存在
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            return False if ret == b'-1' else True
        else:
            # 数据库查询
            comment = self.save()
            if comment is None:
                # 不存在, 设置缓存，防止击穿
                try:
                    rc.setex(self.key, constants.CommentNotExistsCacheTTL.get_val(), '-1')
                except RedisError as e:
                    current_app.logger.error(e)

                return False
            else:
                return True

    def save(self, comment=None):
        """
        保存
        """
        if comment is None:
            # 数据库查询
            comment = Comment.query.filter(Comment.id == self.comment_id,
                                           Comment.status == Comment.STATUS.APPROVED).all()

        if comment is None:
            return None
        else:
            # 设置缓存
            formatted_comment = marshal(comment, self.comment_fields)
            try:
                current_app.redis_cluster.setex(self.key, constants.CommentCacheTTL.get_val(),
                                                json.dumps(formatted_comment))
            except RedisError as e:
                current_app.logger.error(e)

            return formatted_comment

    def clear(self):
        current_app.redis_cluster.delete(self.key)


class CommentsAndRepliesCacheBase(object):
    """
    评论或回复的缓存父类
    """
    def __init__(self, id_value):
        self.id_value = id_value
        self.key = self._set_key()

    def _set_key(self):
        """
        设置缓存键
        """
        return ''

    def _get_total_count(self):
        """
        获取总量
        :return:
        """
        return 0

    def _db_query_filter(self, query):
        """
        数据库查询条件
        :return:
        """
        return query

    def _get_cache_ttl(self):
        """
        获取缓存有效期
        :return:
        """
        return 0

    def get_page(self, offset, limit):
        """
        分页获取
        :param offset:
        :param limit:
        :return: total_count, end_id, last_id, []
        """
        rc = current_app.redis_cluster

        # 查询缓存
        try:
            pl = rc.pipeline()
            pl.zcard(self.key)
            pl.zrange(self.key, 0, 0, withscores=True)
            if offset is None:
                # 从头开始取
                pl.zrevrange(self.key, 0, limit - 1, withscores=True)
            else:
                pl.zrevrangebyscore(self.key, offset - 1, 0, 0, limit - 1, withscores=True)
            total_count, end_id, ret = pl.execute()
        except RedisError as e:
            current_app.logger.error(e)
            total_count = 0
            end_id = None
            last_id = None
            ret = []

        if total_count > 0:
            # Cache exists.
            end_id = int(end_id[0][1])
            # ret -> [(value, score)...]
            last_id = int(ret[-1][1]) if ret else None
            return total_count, end_id, last_id, [int(cid[0]) for cid in ret]
        else:
            # No cache.
            # 查询总数
            total_count = self._get_total_count()
            if total_count == 0:
                return 0, None, None, []

            # 查询数据库
            # 通过双字段排序将置顶放在结果前列
            query = Comment.query.options(load_only(Comment.id, Comment.ctime, Comment.is_top))
            query = self._db_query_filter(query)
            ret = query.order_by(Comment.is_top.desc(), Comment.id.desc()).all()

            cache = []
            page_comments = []
            page_count = 0
            total_count = len(ret)
            page_last_comment = None

            for comment in ret:
                score = comment.ctime.timestamp()
                if comment.is_top:
                    score += constants.COMMENTS_CACHE_MAX_SCORE

                # 构造返回数据
                if ((offset is not None and score < offset) or offset is None) and page_count <= limit:
                    page_comments.append(comment.id)
                    page_count += 1
                    page_last_comment = comment

                # 构造缓存数据
                cache.append(score)
                cache.append(comment.id)

            end_id = ret[-1].ctime.timestamp()
            last_id = page_last_comment.ctime.timestamp() if page_last_comment else None

            # 设置缓存
            if cache:
                try:
                    pl = rc.pipeline()
                    pl.zadd(self.key, *cache)
                    pl.expire(self.key, self._get_cache_ttl())
                    results = pl.execute()
                    if results[0] and not results[1]:
                        rc.delete(self.key)
                except RedisError as e:
                    current_app.logger.error(e)

            return total_count, end_id, last_id, page_comments

    def add(self, comment):
        """
        增加
        """
        rc = current_app.redis_cluster
        try:
            ttl = rc.ttl(self.key)
            if ttl > constants.ALLOW_UPDATE_ARTICLE_COMMENTS_CACHE_TTL_LIMIT:
                score = comment.ctime.timestamp()
                rc.zadd(self.key, score, comment.id)
        except RedisError as e:
            current_app.logger.error(e)

    def clear(self):
        """
        清除
        """
        current_app.redis_cluster.delete(self.key)


class ArticleCommentsCache(CommentsAndRepliesCacheBase):
    """
    文章评论缓存
    """
    def _set_key(self):
        return 'art:{}:comm'.format(self.id_value)

    def _get_total_count(self):
        return cache_statistic.ArticleCommentCountStorage.get(self.id_value)

    def _db_query_filter(self, query):
        return query.filter(Comment.article_id == self.id_value,
                            Comment.parent_id == None,
                            Comment.status == Comment.STATUS.APPROVED)

    def _get_cache_ttl(self):
        return constants.ArticleCommentsCacheTTL.get_val()


class CommentRepliesCache(CommentsAndRepliesCacheBase):
    """
    评论回复缓存
    """
    def _set_key(self):
        return 'comm:{}:reply'.format(self.id_value)

    def _get_total_count(self):
        return cache_statistic.CommentReplyCountStorage.get(self.id_value)

    def _db_query_filter(self, query):
        return query.filter(Comment.parent_id == self.id_value,
                            Comment.status == Comment.STATUS.APPROVED)

    def _get_cache_ttl(self):
        return constants.CommentRepliesCacheTTL.get_val()
