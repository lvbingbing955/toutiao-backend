from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask import g
from sqlalchemy.exc import IntegrityError
import time


from utils.decorators import login_required, set_db_to_write
from models.user import Relation, User
from utils import parser
from models import db
from cache import user as cache_user
from cache import statistic as cache_statistic


class BlacklistListResource(Resource):
    """
    用户拉黑
    """
    method_decorators = [login_required]

    def post(self):
        """
        拉黑用户
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.user_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target
        if target == g.user_id:
            return {'message': 'User cannot blacklist self.'}, 400
        try:
            blacklist = Relation(user_id=g.user_id, target_user_id=target, relation=Relation.RELATION.BLACKLIST)
            db.session.add(blacklist)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            fol_ret = 0
            # Change relation from DELETE to BLACKLIST
            del_ret = Relation.query.filter(Relation.user_id == g.user_id,
                                        Relation.target_user_id == target,
                                        Relation.relation == Relation.RELATION.DELETE) \
                .update({'relation': Relation.RELATION.BLACKLIST})
            if del_ret == 0:
                # Change relation from FOLLOW to BLACKLIST
                fol_ret = Relation.query.filter(Relation.user_id == g.user_id,
                                            Relation.target_user_id == target,
                                            Relation.relation == Relation.RELATION.FOLLOW) \
                    .update({'relation': Relation.RELATION.BLACKLIST})

            db.session.commit()

            if fol_ret > 0:
                timestamp = time.time()
                cache_user.UserFollowingCache(g.user_id).update(target, timestamp, -1)
                cache_user.UserFollowersCache(target).update(g.user_id, timestamp, -1)
                cache_statistic.UserFollowingsCountStorage.incr(g.user_id, -1)
                cache_statistic.UserFollowersCountStorage.incr(target, -1)

        cache_user.UserRelationshipCache(g.user_id).clear()

        return {'target': target}, 201


class BlacklistResource(Resource):
    """
    用户拉黑
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消拉黑用户
        """
        ret = Relation.query.filter_by(user_id=g.user_id, target_user_id=target, relation=Relation.RELATION.BLACKLIST)\
            .update({'relation': Relation.RELATION.DELETE})
        db.session.commit()
        if ret > 0:
            cache_user.UserRelationshipCache(g.user_id).clear()
        return {'message': 'OK'}, 204

