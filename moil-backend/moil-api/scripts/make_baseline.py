"""python -m scripts.make_baseline
Writes alembic/versions/0001_baseline.py describing ALL current tables. It compares the models with a brand-new EMPTY temporary
database (your real moil.db is never touched), then deletes that temporary file. Run it once."""
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config
root = Path(__file__).resolve().parent.parent
if any((root / "alembic" / "versions").glob("*.py")): sys.exit("A migration already exists in alembic/versions. Nothing was done.")
tmp = root / "_empty_for_baseline.db"
if tmp.exists(): tmp.unlink()
cfg = Config(str(root / "alembic.ini")); cfg.set_main_option("script_location", str(root / "alembic")); cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp.as_posix()}")
try: command.revision(cfg, message="baseline", autogenerate=True, rev_id="0001")
finally:
    try: tmp.unlink(missing_ok=True)
    except PermissionError: print(f"Please delete {tmp} yourself.")
print("Done. Open alembic/versions/0001_baseline.py: it should contain op.create_table(...) for every table.")
