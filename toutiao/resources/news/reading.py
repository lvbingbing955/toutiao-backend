from flask_restful import Resource
from flask import g, current_app
from flask_restful import inputs
from flask_restful.reqparse import RequestParser
from sqlalchemy import func
from sqlalchemy.orm import load_only
from redis.exceptions import ConnectionError

from utils.decorators import login_required
from . import constants
from cache import user as cache_user
from cache import article as cache_article
from models.news import Read
from models import db
from utils.logging import write_trace_log
from utils import parser


class ReadingHistoryListResource(Resource):
    """
    用户阅读历史
    """
    method_decorators = [login_required]

    def get(self):
        """
        获取用户阅读历史
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

        user_id = g.user_id

        results = []
        total_count, article_ids = cache_user.UserReadingHistoryStorage(user_id).get(page, per_page)

        user_article_attitude_cache = cache_user.UserArticleAttitudeCache(user_id)
        for article_id in article_ids:
            article = cache_article.ArticleInfoCache(int(article_id)).get()
            article['is_liking'] = user_article_attitude_cache.determine_liking_article(int(article_id))
            results.append(article)

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class ReadingDurationResource(Resource):
    """
    阅读时长
    """
    def post(self):
        req_parser = RequestParser()
        req_parser.add_argument('Trace', type=inputs.regex(r'^.+$'), required=True, location='headers')
        req_parser.add_argument('duration', type=inputs.natural, required=True, location='json')
        req_parser.add_argument('art_id', type=parser.article_id, required=True, location='json')
        args = req_parser.parse_args()

        article = cache_article.ArticleInfoCache(args.art_id).get()
        write_trace_log(args.Trace, args.duration, channel_id=article['ch_id'])

        return {'message': 'OK'}, 201
