from sqlalchemy import func
from flask import current_app

from models.news import Article
from models import db
from cache import statistic as cache_statistic
from common import flask_app


def __fix_statistics(cls):
    # 进行数据库查询
    with flask_app.app_context():
        ret = cls.db_query()

        # 将数据库查询结果设置到redis中
        cls.reset(ret)


def fix_statistics():
    """
    修正redis中存储的统计数据 定时任务
    :return:
    """
    # 查询数据库得到统计数据
    # class UserArticlesCountStorage(CountStorageBase):
    #     """
    #     用户文章数量
    #     """
    #     key = 'count:user:arts'   zset  4,1

    # sql
    # select user_id, count(article_id)  from news_article_basic where status=2 group by user_id
    # ret = db.session.query(Article.user_id, func.count(Article.id))\
    #         .filter(Article.status == Article.STATUS.APPROVED)\
    #         .group_by(Article.user_id).all()

    # ret -> [
    # ( 1, 46141),
    # (2, 46357 ),
    # (3 ,46187)
    # ]

    # # 设置redis的存储记录
    # pl = current_app.redis_master.pipeline()
    # pl.delete('count:user:arts')
    #
    # # zadd(key, score1, val1, score2, val2, ...)
    # for user_id, count in ret:
    #     pl.zadd('count:user:arts', count, user_id)
    #
    # pl.execute()

    __fix_statistics(cache_statistic.UserArticlesCountStorage)

    __fix_statistics(cache_statistic.UserFollowingsCountStorage)

    __fix_statistics(cache_statistic.ArticleCollectingCountStorage)

    __fix_statistics(cache_statistic.UserArticleCollectingCountStorage)

