from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask import g
from sqlalchemy.exc import IntegrityError

from utils.decorators import login_required
from utils import parser
from models import db
from models.news import Report


class ReportListResource(Resource):
    """
    用户点赞
    """
    method_decorators = [login_required]

    def _report_type(self, value):
        if value not in Report.TYPE_LIST:
            raise ValueError('Invalid report type.')
        else:
            return value

    def post(self):
        """
        用户点赞
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.article_id, required=True, location='json')
        json_parser.add_argument('type', type=self._report_type, required=True, location='json')
        json_parser.add_argument('remark', type=str, required=False, location='json')
        args = json_parser.parse_args()

        try:
            report = Report(user_id=g.user_id, article_id=args.target, type=args.type)
            if args.type == Report.TYPE.OTHER and args.remark:
                report.remark = args.remark
            db.session.add(report)
            db.session.commit()
        except IntegrityError:
            return {'message': 'User has reported this article.'}, 409

        return {'target': args.target, 'type': args.type}, 201




