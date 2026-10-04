"""python -m scripts.seed_blasting -> demo blast plans. Safe to run once; does nothing if blasts already exist."""
import random
from datetime import date, timedelta
from sqlalchemy import select, func
from app.db.session import SessionLocal, Base, engine
from app.models import Mine, BlastPlan
random.seed(11); Base.metadata.create_all(engine)
with SessionLocal() as db:
    if db.scalar(select(func.count()).select_from(BlastPlan)):
        print("Blast plans already exist. Nothing to do.")
    else:
        for m in db.scalars(select(Mine)):
            for i in range(6):  # past blasts, completed
                p = round(m.daily_target_t * random.uniform(2.5, 4)); d = date.today() - timedelta(days=4 + i * 5)
                db.add(BlastPlan(mine_id=m.id, bench=f"Bench {random.randint(1, 6)}", blast_date=d, planned_t=p, actual_t=round(p * random.uniform(.85, 1.05)), status="Completed"))
            db.add(BlastPlan(mine_id=m.id, bench="Bench 2", blast_date=date.today() - timedelta(days=1), planned_t=round(m.daily_target_t * 3), status="Delayed", delay_reason="Heavy rain, blast area not safe"))
            for j in range(3):  # upcoming
                db.add(BlastPlan(mine_id=m.id, bench=f"Bench {random.randint(1, 6)}", blast_date=date.today() + timedelta(days=2 + j * 3), planned_t=round(m.daily_target_t * random.uniform(2.5, 4)), status="Scheduled"))
        db.commit(); print("Seeded blast plans.")
