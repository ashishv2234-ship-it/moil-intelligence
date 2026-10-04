from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text, Index, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
now = datetime.utcnow
ROLES = ["ADMIN","MINE_MANAGER","GEOLOGIST","PLANNING_ENGINEER","MAINTENANCE_ENGINEER","EXECUTIVE","DATA_ENGINEER"]
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="EXECUTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)  # MFA-ready
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
class Mine(Base):
    __tablename__ = "mines"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    state: Mapped[str] = mapped_column(String(40))
    lat: Mapped[float] = mapped_column(Float); lng: Mapped[float] = mapped_column(Float)
    daily_target_t: Mapped[float] = mapped_column(Float)
class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    type: Mapped[str] = mapped_column(String(30))
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="Running")
    availability_pct: Mapped[float] = mapped_column(Float, default=90)
    health_score: Mapped[float] = mapped_column(Float, default=90)
    downtime_hrs: Mapped[float] = mapped_column(Float, default=0)
class ProductionRecord(Base):
    __tablename__ = "production_records"
    __table_args__ = (Index("ix_prod_mine_date", "mine_id", "day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"))
    day: Mapped[date] = mapped_column(Date)
    planned_t: Mapped[float] = mapped_column(Float); actual_t: Mapped[float] = mapped_column(Float)
class ShortfallRisk(Base):
    __tablename__ = "shortfall_risks"
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), index=True)
    level: Mapped[str] = mapped_column(String(10))
    probability: Mapped[float] = mapped_column(Float)
    expected_shortfall_t: Mapped[float] = mapped_column(Float)
    main_cause: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class ActionRecommendation(Base):
    __tablename__ = "action_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("shortfall_risks.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(60))
    explanation: Mapped[str] = mapped_column(Text)
    recovery_t: Mapped[float] = mapped_column(Float); cost_inr_lakh: Mapped[float] = mapped_column(Float)
    feasibility: Mapped[float] = mapped_column(Float); confidence: Mapped[float] = mapped_column(Float)
    owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Proposed")
    valid_until: Mapped[datetime] = mapped_column(DateTime)
class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(10), default="Success")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records: Mapped[int] = mapped_column(Integer, default=0)
class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="Failed")  # Imported | Validated | Failed
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_ok: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    rows_warning: Mapped[int] = mapped_column(Integer, default=0)
    issues_total: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)  # line number in the file (header = line 1)
    field: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))  # Error | Warning
    message: Mapped[str] = mapped_column(String(300))
class BlastPlan(Base):
    __tablename__ = "blast_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), index=True)
    bench: Mapped[str] = mapped_column(String(40))
    blast_date: Mapped[date] = mapped_column(Date, index=True)
    planned_t: Mapped[float] = mapped_column(Float)
    actual_t: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="Scheduled")  # Scheduled | Completed | Delayed
    delay_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
class DrillHole(Base):
    __tablename__ = "drill_holes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    lat: Mapped[float] = mapped_column(Float); lng: Mapped[float] = mapped_column(Float)
    depth_m: Mapped[float] = mapped_column(Float); mn_pct: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40), default="Demo (synthetic)")
class ReserveZone(Base):
    __tablename__ = "reserve_zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    cell_key: Mapped[str] = mapped_column(String(12), unique=True, index=True)  # grid cell, stable between model runs
    lat: Mapped[float] = mapped_column(Float); lng: Mapped[float] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float); tonnage_t: Mapped[float] = mapped_column(Float)
    grade_mn_pct: Mapped[float] = mapped_column(Float); confidence_pct: Mapped[float] = mapped_column(Float)
    holes_nearby: Mapped[int] = mapped_column(Integer, default=0); nearest_mine_km: Mapped[float] = mapped_column(Float, default=0)
    drill_suggested: Mapped[bool] = mapped_column(Boolean, default=False)   # set by the model
    drill_recommended: Mapped[bool] = mapped_column(Boolean, default=False)  # set by a geologist
    model_version: Mapped[str] = mapped_column(String(30)); run_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    temp_c: Mapped[float] = mapped_column(Float); humidity_pct: Mapped[float] = mapped_column(Float)
    wind_kmh: Mapped[float] = mapped_column(Float); rain_now_mm: Mapped[float] = mapped_column(Float); rain_today_mm: Mapped[float] = mapped_column(Float)
    blasting: Mapped[str] = mapped_column(String(12))  # Suitable, Caution or Unsuitable
    source: Mapped[str] = mapped_column(String(20), default="open-meteo")
class SatelliteCell(Base):
    __tablename__ = "satellite_cells"
    id: Mapped[int] = mapped_column(primary_key=True)
    indicator: Mapped[str] = mapped_column(String(8), index=True)  # ndvi, soil, lst or rain
    lat: Mapped[float] = mapped_column(Float); lng: Mapped[float] = mapped_column(Float)  # cell centre
    value: Mapped[float] = mapped_column(Float)
    observed_on: Mapped[date] = mapped_column(Date)
    cell_deg: Mapped[float] = mapped_column(Float, default=0.25)
    source: Mapped[str] = mapped_column(String(60))
class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    rain_mm: Mapped[float] = mapped_column(Float); wind_kmh: Mapped[float] = mapped_column(Float)  # daily rain total, daily maximum wind
    blasting: Mapped[str] = mapped_column(String(12))  # Suitable, Caution or Unsuitable
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class RiskOwner(Base):
    """Who owns the shortfall risk of a mine. Kept per mine (not per risk row) because every risk run creates new risk rows."""
    __tablename__ = "risk_owners"
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class ActionComment(Base):
    __tablename__ = "action_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("action_recommendations.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class RiskFactor(Base):
    """One piece of a risk's probability: a label and the points it added (can be negative). Stored per risk run so the screen can say WHY."""
    __tablename__ = "risk_factors"
    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("shortfall_risks.id"), index=True)
    label: Mapped[str] = mapped_column(String(60))
    points: Mapped[int] = mapped_column(Integer)
class EquipmentSnapshot(Base):
    """One machine's values as they stood right after a real (not check-only) telematics import. History starts at the first import after this table existed."""
    __tablename__ = "equipment_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("uploads.id"), index=True, nullable=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    status: Mapped[str] = mapped_column(String(20))
    availability_pct: Mapped[float] = mapped_column(Float); health_score: Mapped[float] = mapped_column(Float); downtime_hrs: Mapped[float] = mapped_column(Float)
class StockReading(Base):
    """Closing stockpile (tonnes) at one mine on one day, from an uploaded CSV. One row per mine and day; a later upload for the same day replaces it."""
    __tablename__ = "stockpile_readings"
    __table_args__ = (UniqueConstraint("mine_id", "day", name="uq_stockpile_mine_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    mine_id: Mapped[int] = mapped_column(ForeignKey("mines.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    closing_t: Mapped[float] = mapped_column(Float)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

