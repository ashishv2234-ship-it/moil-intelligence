from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
class ORM(BaseModel): model_config = ConfigDict(from_attributes=True)
class RegisterIn(BaseModel):
    email: EmailStr; name: str = Field(min_length=2); password: str = Field(min_length=8); role: str = "EXECUTIVE"
class LoginIn(BaseModel): email: EmailStr; password: str
class RefreshIn(BaseModel): refresh_token: str
class TokenOut(BaseModel): access_token: str; refresh_token: str; token_type: str = "bearer"
class UserOut(ORM): id: int; email: EmailStr; name: str; role: str
class MineIn(BaseModel): name: str; state: str; lat: float = Field(ge=-90, le=90); lng: float = Field(ge=-180, le=180); daily_target_t: float = Field(gt=0)
class MineOut(MineIn, ORM): id: int
class ProductionIn(BaseModel): mine_id: int; day: datetime; planned_t: float = Field(ge=0); actual_t: float = Field(ge=0)
class RiskOut(ORM):
    id: int; mine_id: int; level: str; probability: float; expected_shortfall_t: float; main_cause: str; confidence: float; status: str; action: str | None = None; owner: str | None = None
class RecOut(ORM):
    id: int; risk_id: int; action_type: str; explanation: str; recovery_t: float; cost_inr_lakh: float
    feasibility: float; confidence: float; owner: str | None; status: str; valid_until: datetime
    label: str = "AI-generated recommendation"
class StatusIn(BaseModel): status: str
class AssignIn(BaseModel): owner: str
class Page(BaseModel): items: list; total: int; page: int; size: int
