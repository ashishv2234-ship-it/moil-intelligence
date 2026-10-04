"""python -m scripts.seed_geology -> loads demo (synthetic) drill holes, then runs the prospectivity model.
Safe to run twice: skips if drill holes already exist. Run scripts.seed first (the model needs the mines)."""
from sqlalchemy import select, func
from app.db.session import SessionLocal, Base, engine
from app.models import DrillHole, Mine
from app.services.demo_geology import make_demo_holes
from app.services.prospectivity import run_model
Base.metadata.create_all(engine)
with SessionLocal() as db:
    if not db.scalar(select(func.count()).select_from(Mine)):
        print("No mines found. Run: python -m scripts.seed  first."); raise SystemExit(1)
    if db.scalar(select(func.count()).select_from(DrillHole)):
        print("Drill holes already exist. Nothing to do.")
    else:
        for code, la, ln, depth, mn in make_demo_holes():
            db.add(DrillHole(code=code, lat=la, lng=ln, depth_m=depth, mn_pct=mn))
        db.commit(); print("Seeded demo drill holes.")
    r = run_model(db); print(f"Model {r['model_version']}: {r['zones']} zones from {r['holes_used']} holes and {r['mines_used']} mines.")
