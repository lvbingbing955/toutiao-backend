from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from sqlalchemy.exc import IntegrityError
from flask import g
from sqlalchemy.orm import load_only
from flask_restful import inputs
from sqlalchemy import func

from utils.decorators import login_required
from utils import parser
from models import db
from models.news import Collection
from . import constants
from cache import article as cache_article
from utils.logging import write_trace_log
from utils.decorators import set_db_to_read, set_db_to_write
from cache import statistic as cache_statistic
from cache import user as cache_user


class CollectionListResource(Resource):
    """
    文章收藏
    """
    method_decorators = {
        'post': [login_required],
        'get': [login_required]
    }

    def post(self):
        """
        用户收藏文章
        """
        req_parser = RequestParser()
        req_parser.add_argument('target', type=parser.article_id, required=True, location='json')
        req_parser.add_argument('Trace', type=inputs.regex(r'^.+$'), required=False, location='headers')
        args = req_parser.parse_args()

        target = args.target

        # 记录埋点日志
        if args.Trace:
            article = cache_article.ArticleInfoCache(target).get()
            write_trace_log(args.Trace, channel_id=article['ch_id'])

        ret = 1
        try:
            collection = Collection(user_id=g.user_id, article_id=target)
            db.session.add(collection)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            ret = Collection.query.filter_by(user_id=g.user_id, article_id=target, is_deleted=True) \
                .update({'is_deleted': False})
            db.session.commit()

        if ret > 0:
            cache_user.UserArticleCollectionsCache(g.user_id).clear()
            cache_statistic.ArticleCollectingCountStorage.incr(target)
            cache_statistic.UserArticleCollectingCountStorage.incr(g.user_id)

        return {'target': target}, 201

    def get(self):
        """
        获取用户的收藏历史
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_ARTICLE_PER_PAGE_MIN,
                                                                 constants.DEFAULT_ARTICLE_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_ARTICLE_PER_PAGE_MIN

        total_count, collections = cache_user.UserArticleCollectionsCache(g.user_id).get_page(page, per_page)

        results = []
        user_article_attitude_cache = cache_user.UserArticleAttitudeCache(g.user_id)
        for article_id in collections:
            article = cache_article.ArticleInfoCache(article_id).get()
            article['is_liking'] = user_article_attitude_cache.determine_liking_article(article_id)
            results.append(article)

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class CollectionResource(Resource):
    """
    文章收藏
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        用户取消收藏
        """
        ret = Collection.query.filter_by(user_id=g.user_id, article_id=target, is_deleted=False) \
            .update({'is_deleted': True})
        db.session.commit()

        if ret > 0:
            cache_user.UserArticleCollectionsCache(g.user_id).clear()
            cache_statistic.ArticleCollectingCountStorage.incr(target, -1)
            cache_statistic.UserArticleCollectingCountStorage.incr(g.user_id, -1)
        return {'message': 'OK'}, 204


