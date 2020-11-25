from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs

from cache import notice as cache_notice
from . import constants
from utils.decorators import set_db_to_read


class AnnouncementListResource(Resource):
    """
    系统公告
    """

    def get(self):
        """
        获取系统公告列表
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_ANNOUNCEMENT_PER_PAGE_MIN,
                                                                 constants.DEFAULT_ANNOUNCEMENT_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_ANNOUNCEMENT_PER_PAGE_MIN

        total_count, results = cache_notice.AnnouncementsCache.get_page(page, per_page)

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class AnnouncementResource(Resource):
    """
    系统公告
    """

    def get(self, target):
        """
        获取系统公告
        """
        exist = cache_notice.AnnouncementDetailCache(target).exists()
        if not exist:
            return {'message': 'Invalid announcement.'}, 400

        announcement = cache_notice.AnnouncementDetailCache(target).get()
        return announcement

