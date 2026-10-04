"""python -m scripts.seed  -> demo mines, 12 months of production, equipment, users (password: Moil@12345)."""
import random
from datetime import date, timedelta
from app.db.session import SessionLocal, Base, engine
from app.models import *
from app.core.security import hash_password
random.seed(7); Base.metadata.create_all(engine)
MINES = [("Balaghat","MP",21.8,80.2,2200),("Dongri Buzurg","MH",21.2,79.6,1800),("Gumgaon","MH",21.3,79.1,1500),("Kandri","MH",21.3,79.3,1300),("Mansar","MH",21.4,79.3,1100)]
with SessionLocal() as db:
    for i, r in enumerate(ROLES): db.add(User(email=f"{r.lower()}@moil.in", name=r.title(), password_hash=hash_password("Moil@12345"), role=r))
    for n, s, la, ln, t in MINES:
        m = Mine(name=n, state=s, lat=la, lng=ln, daily_target_t=t); db.add(m); db.flush()
        for k, ty in enumerate(["Excavator","Dumper","Drill","Loader","Crusher"]): db.add(Equipment(code=f"{ty[:3].upper()}-{m.id}-{k+1}", type=ty, mine_id=m.id, availability_pct=random.randint(68, 97), health_score=random.randint(55, 98)))
        for d in range(365):
            day = date.today() - timedelta(days=365 - d); monsoon = 6 <= day.month <= 9
            db.add(ProductionRecord(mine_id=m.id, day=day, planned_t=t, actual_t=round(t * random.uniform(.82, 1.08) * (.88 if monsoon else 1))))
    for n in ["Production MIS","Fleet telematics","IMD weather feed","Sentinel-2"]: db.add(DataSource(name=n))
    db.commit(); print("Seeded.")
