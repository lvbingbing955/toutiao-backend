from flask import current_app
import json
from sqlalchemy.orm import load_only
from redis.exceptions import RedisError

from models.notice import Announcement
from . import constants


class AnnouncementsCache(object):
    """
    系统公告列表缓存
    """
    key = 'announcement'

    @classmethod
    def get_page(cls, page, per_page):
        """
        获取系统公告列表
        :param page: 页数
        :param per_page: 每页数量
        :return: total_count, []
        """
        rc = current_app.redis_cluster

        try:
            pl = rc.pipeline()
            pl.zcard(cls.key)
            pl.zrevrange(cls.key, (page - 1) * per_page, page * per_page, withscores=True)
            total_count, ret = pl.execute()
        except RedisError as e:
            current_app.logger.error(e)
            total_count = 0
            ret = []

        if total_count > 0:
            # Cache exists.
            results = []
            for ann, ann_id in ret:
                _ann = json.loads(ann)
                _ann['id'] = int(ann_id)
                results.append(_ann)
            return total_count, results
        else:
            # No cache.
            ret = Announcement.query.options(load_only(Announcement.id, Announcement.pubtime, Announcement.title)) \
                .filter_by(status=Announcement.STATUS.PUBLISHED) \
                .order_by(Announcement.pubtime.desc()).all()

            results = []
            cache = []
            for ann in ret:
                _ann = dict(
                    pubdate=ann.pubtime.strftime('%Y-%m-%dT%H:%M:%S'),
                    title=ann.title
                )
                cache.append(ann.id)
                cache.append(json.dumps(_ann))
                _ann['id'] = ann.id
                results.append(_ann)

            if cache:
                try:
                    pl = rc.pipeline()
                    pl.zadd(cls.key, *cache)
                    pl.expire(cls.key, constants.ANNOUNCEMENTS_CACHE_TTL)
                    result = pl.execute()
                    if result[0] and not result[1]:
                        rc.delete(cls.key)
                except RedisError as e:
                    current_app.logger.error(e)

            total_count = len(results)
            page_results = results[(page - 1) * per_page:page * per_page]

            return total_count, page_results


class AnnouncementDetailCache(object):
    """
    系统公告详细内容缓存
    """
    def __init__(self, ann_id):
        self.key = 'announcement:{}'.format(ann_id)
        self.ann_id = ann_id

    def save(self):
        """
        保存
        """
        rc = current_app.redis_cluster

        ann = Announcement.query.options(
            load_only(Announcement.title, Announcement.content, Announcement.pubtime)) \
            .filter_by(id=self.ann_id, status=Announcement.STATUS.PUBLISHED).first()

        if ann is None:
            return None

        _ann = {
            'pubdate': ann.pubtime.strftime('%Y-%m-%dT%H:%M:%S'),
            'title': ann.title,
            'content': ann.content
        }
        try:
            rc.setex(self.key, constants.AnnouncementDetailCacheTTL.get_val(), json.dumps(_ann))
        except RedisError as e:
            current_app.logger.error(e)

        return _ann

    def get(self):
        """
        获取公告内容
        """
        rc = current_app.redis_cluster
        try:
            ret = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret is not None:
            ann = json.loads(ret)
            ann['id'] = self.ann_id
            return ann
        else:
            _ann = self.save()
            _ann['id'] = self.ann_id
            return _ann

    def exists(self):
        """
        判断公告是否存在
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
            ann = self.save()
            if ann is None:
                # 不存在, 设置缓存，防止击穿
                try:
                    rc.setex(self.key, constants.AnnouncementNotExistsCacheTTL.get_val(), '-1')
                except RedisError as e:
                    current_app.logger.error(e)

                return False
            else:
                return True

