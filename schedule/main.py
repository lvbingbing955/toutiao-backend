import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))
sys.path.insert(0, os.path.join(BASE_DIR))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ProcessPoolExecutor

# 创建一个apscheduler调度器对象

# 配置调度器对象使用的 任务存储后端  执行器（进程、线程）

executors = {
    # 表示默认到了时间，该执行的定时任务都是放到进程池中的一个子进程执行
    # 3表示进程池中最多有3个进程，也就说 在同一时刻，最多 有3个进程同时执行
    'default': ProcessPoolExecutor(3)
}

# Blocking 阻塞的调度
scheduler = BlockingScheduler(executors=executors)

import common

# 添加定时任务

# 在每天的凌晨3点执行
from statistic import fix_statistics
scheduler.add_job(fix_statistics, 'cron', hour=3)

# 测试使用这个触发时间，在scheduler启动的使用执行一次定时任务
# scheduler.add_job(fix_statistics, 'date')


# 启动scheduler
if __name__ == '__main__':
    # start()会阻塞当前文件退出
    scheduler.start()
