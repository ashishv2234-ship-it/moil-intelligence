from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
celery = Celery("moil", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery.conf.beat_schedule = {"daily-shortfall-run": {"task": "app.workers.celery_app.run_shortfall_task", "schedule": crontab(hour=1, minute=0)}, "hourly-weather": {"task": "app.workers.celery_app.sync_weather_task", "schedule": crontab(minute=5)}}
@celery.task
def run_shortfall_task():
    from app.db.session import SessionLocal
    from app.services.risk import run_shortfall
    with SessionLocal() as db: return len(run_shortfall(db))
@celery.task
def sync_weather_task():
    from app.db.session import SessionLocal
    from app.services.weather import sync_weather
    with SessionLocal() as db: return sync_weather(db)
