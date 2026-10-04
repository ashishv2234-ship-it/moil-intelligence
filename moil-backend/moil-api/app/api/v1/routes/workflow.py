"""Workflow: who owns a mine's shortfall risk, and comments on corrective actions. Plain notes, no notifications are sent."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import current_user, require_roles, audit
from app.db.session import get_db
from app.models import User, Mine, RiskOwner, ActionRecommendation, ActionComment
router = APIRouter(tags=["workflow"])
OWNER_ROLES = ("MINE_MANAGER", "PLANNING_ENGINEER", "MAINTENANCE_ENGINEER")  # roles that can own a risk
COMMENT_ROLES = ("MINE_MANAGER", "PLANNING_ENGINEER", "MAINTENANCE_ENGINEER")  # roles that can write comments (admin always can); everyone signed in can read
class OwnerIn(BaseModel): mine_id: int; user_id: int | None = None  # user_id null clears the owner
class CommentIn(BaseModel): text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
@router.get("/workflow/assignable-users")
def assignable(db: Session = Depends(get_db), _=Depends(current_user)):
    q = select(User).where(User.is_active.is_(True), User.role.in_(OWNER_ROLES)).order_by(User.name, User.id)
    return [{"id": u.id, "name": u.name, "role": u.role} for u in db.scalars(q)]
@router.put("/risks/owner")
def set_owner(b: OwnerIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))):
    if not db.get(Mine, b.mine_id): raise HTTPException(404, "Mine not found")
    row = db.scalar(select(RiskOwner).where(RiskOwner.mine_id == b.mine_id))
    if b.user_id is None:
        if row: db.delete(row); db.commit()
        audit(db, u.id, "risk.owner.clear", mine_id=b.mine_id); return {"mine_id": b.mine_id, "user_id": None, "name": None}
    owner = db.get(User, b.user_id)
    if not owner or not owner.is_active: raise HTTPException(404, "User not found")
    if owner.role not in OWNER_ROLES: raise HTTPException(422, "This user's role cannot own a risk")
    if row: row.user_id = owner.id; row.assigned_by = u.id
    else: db.add(RiskOwner(mine_id=b.mine_id, user_id=owner.id, assigned_by=u.id))
    db.commit(); audit(db, u.id, "risk.owner.set", mine_id=b.mine_id, target_user_id=owner.id)  # never pass user_id= in the detail
    return {"mine_id": b.mine_id, "user_id": owner.id, "name": owner.name}
def _action(db: Session, id: int) -> ActionRecommendation:
    a = db.get(ActionRecommendation, id)
    if not a: raise HTTPException(404, "Action not found")
    return a
def _out(c: ActionComment, author: User | None) -> dict:
    return {"id": c.id, "text": c.text, "created_at": c.created_at, "author": author.name if author else "Unknown user", "role": author.role if author else None}
@router.get("/actions/recommendations/{id}/comments")
def comments(id: int, db: Session = Depends(get_db), _=Depends(current_user)):
    _action(db, id)
    rows = db.execute(select(ActionComment, User).join(User, User.id == ActionComment.user_id, isouter=True).where(ActionComment.action_id == id).order_by(ActionComment.id)).all()
    return [_out(c, a) for c, a in rows]
@router.post("/actions/recommendations/{id}/comments", status_code=201)
def add_comment(id: int, b: CommentIn, db: Session = Depends(get_db), u=Depends(require_roles(*COMMENT_ROLES))):
    _action(db, id)
    c = ActionComment(action_id=id, user_id=u.id, text=b.text); db.add(c); db.commit()
    audit(db, u.id, "action.comment", id=id, comment_id=c.id)
    return _out(c, u)
