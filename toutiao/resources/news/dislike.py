from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask import g

from utils.decorators import login_required, set_db_to_write
from utils import parser
from models import db
from models.news import Attitude, ArticleStatistic
from cache import statistic as cache_statistic
from cache import user as cache_user

class DislikeListResource(Resource):
    """
    用户不喜欢
    """
    method_decorators = [login_required]

    def post(self):
        """
        不喜欢
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.article_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target

        # 此次操作前，用户对文章可能是没有态度，也可能是不喜欢，需要先查询对文章的原始态度，然后对相应的统计数据进行累计或减少
        atti = Attitude.query.filter_by(user_id=g.user_id, article_id=target).first()
        if atti is None:
            attitude = Attitude(user_id=g.user_id, article_id=target, attitude=Attitude.ATTITUDE.DISLIKE)
            db.session.add(attitude)
            db.session.commit()
            cache_statistic.ArticleDislikeCountStorage.incr(target)
        else:
            if atti.attitude == Attitude.ATTITUDE.LIKING:
                # 原先是喜欢
                atti.attitude = Attitude.ATTITUDE.DISLIKE
                db.session.add(atti)
                db.session.commit()
                cache_statistic.ArticleDislikeCountStorage.incr(target)
                cache_statistic.ArticleLikingCountStorage.incr(target, -1)
                cache_statistic.UserLikedCountStorage.incr(g.user_id, -1)
            elif atti.attitude is None:
                # 存在数据，但是无态度(态度被删除）
                atti.attitude = Attitude.ATTITUDE.DISLIKE
                db.session.add(atti)
                db.session.commit()
                cache_statistic.ArticleDislikeCountStorage.incr(target)

        cache_user.UserArticleAttitudeCache(g.user_id).clear()

        return {'target': target}, 201


class DislikeResource(Resource):
    """
    不喜欢
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消不喜欢
        """
        ret = Attitude.query.filter_by(user_id=g.user_id, article_id=target, attitude=Attitude.ATTITUDE.DISLIKE) \
            .update({'attitude': None})
        db.session.commit()
        if ret > 0:
            cache_statistic.ArticleDislikeCountStorage.incr(target, -1)
            cache_user.UserArticleAttitudeCache(g.user_id).clear()
        return {'message': 'OK'}, 204


