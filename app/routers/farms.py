from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user

router = APIRouter(prefix="/farms", tags=["farms"])


@router.get("/me", response_model=schemas.FarmBase | None)
def get_my_farm(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    farm = db.query(models.Farm).filter(models.Farm.user_id == current_user.id).first()
    return farm


@router.put("/me", response_model=schemas.FarmBase)
def update_my_farm(
    update: schemas.FarmUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    farm = db.query(models.Farm).filter(models.Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    for field, value in update.dict(exclude_unset=True).items():
        setattr(farm, field, value)
    db.commit()
    db.refresh(farm)
    return farm
