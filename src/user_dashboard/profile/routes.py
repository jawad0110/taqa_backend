from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from src.auth.dependencies import get_current_user
from src.db.models import User
from . import schemas, service

profile_router = APIRouter()

@profile_router.get("/me", response_model=schemas.ProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    profile = await service.get_profile_by_user_id(db, current_user.uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@profile_router.put("/me", response_model=schemas.ProfileResponse)
async def update_my_profile(
    profile_update: schemas.ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    profile = await service.get_profile_by_user_id(db, current_user.uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return await service.update_profile(db=db, profile_id=profile.id, profile=profile_update)
