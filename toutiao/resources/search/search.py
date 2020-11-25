from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from flask import g, current_app
from redis.exceptions import RedisError

from . import constants
from cache import article as cache_article
from cache import user as cache_user
from models.user import Search
from models import db


class SearchResource(Resource):
    """
    搜索结果
    """
    def get(self):
        """
        获取搜索结果
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('q', type=inputs.regex(r'^.{1,50}$'), required=True, location='args')
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_SEARCH_PER_PAGE_MIN, constants.DEFAULT_SEARCH_PER_PAGE_MAX, 'per_page'), required=False, location='args')
        args = qs_parser.parse_args()
        q = args.q
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_SEARCH_PER_PAGE_MIN

        # Search from Elasticsearch
        query = {
            'from': (page-1)*per_page,
            'size': per_page,
            '_source': False,
            'query': {
                'bool': {
                    'must': [
                        {'match': {'_all': q}}
                    ],
                    'filter': [
                        {'term': {'status': 2}}
                    ]
                }
            }
        }
        ret = current_app.es.search(index='articles', doc_type='article', body=query)

        total_count = ret['hits']['total']

        results = []

        hits = ret['hits']['hits']
        for result in hits:
            article_id = int(result['_id'])
            article = cache_article.ArticleInfoCache(article_id).get()
            if article:
                results.append(article)

        # Record user search history
        if g.user_id and page == 1:
            try:
                cache_user.UserSearchingHistoryStorage(g.user_id).save(q)
            except RedisError as e:
                current_app.logger.error(e)

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class SuggestionResource(Resource):
    """
    联想建议
    """
    def get(self):
        """
        获取联想建议
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('q', type=inputs.regex(r'^.{1,50}$'), required=True, location='args')
        args = qs_parser.parse_args()
        q = args.q

        # 先尝试自动补全建议查询
        query = {
            'from': 0,
            'size': 10,
            '_source': False,
            'suggest': {
                'word-completion': {
                    'prefix': q,
                    'completion': {
                        'field': 'suggest'
                    }
                }
            }
        }
        ret = current_app.es.search(index='completions', body=query)
        options = ret['suggest']['word-completion'][0]['options']

        # 如果没得到查询结果，进行纠错建议查询
        if not options:
            query = {
                'from': 0,
                'size': 10,
                '_source': False,
                'suggest': {
                    'text': q,
                    'word-phrase': {
                        'phrase': {
                            'field': '_all',
                            'size': 1
                        }
                    }
                }
            }
            ret = current_app.es.search(index='articles', doc_type='article', body=query)
            options = ret['suggest']['word-phrase'][0]['options']

        results = []
        for option in options:
            if option['text'] not in results:
                results.append(option['text'])

        return {'options': results}