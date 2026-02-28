import os
from celery import Celery

_redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

celery = Celery(
    'eco399',
    broker=_redis_url,
    backend=_redis_url,
    include=['tasks'],
)

celery.conf.update(
    task_track_started=True,
    result_expires=3600,
)
