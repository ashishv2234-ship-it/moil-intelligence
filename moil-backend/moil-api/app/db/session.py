from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)
# Named constraints: SQLite migrations (batch mode) need names to rebuild a table safely.
NAMING = {"ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"}
class Base(DeclarativeBase): metadata = MetaData(naming_convention=NAMING)
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
