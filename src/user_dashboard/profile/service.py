from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from src.db.models import Profile
from . import schemas

async def get_profile(db: AsyncSession, profile_id: int):
    stmt = select(Profile).where(Profile.id == profile_id)
    result = await db.exec(stmt)
    return result.first()

async def get_profile_by_user_id(db: AsyncSession, user_id: str):
    stmt = select(Profile).where(Profile.user_id == user_id)
    result = await db.exec(stmt)
    return result.first()

async def get_profile_by_email(db: AsyncSession, email: str):
    stmt = select(Profile).where(Profile.email == email)
    result = await db.exec(stmt)
    return result.first()

async def create_profile(db: AsyncSession, profile: schemas.ProfileCreate):
    db_profile = Profile(**profile.dict())
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

async def update_profile(db: AsyncSession, profile_id: int, profile: schemas.ProfileUpdate):
    db_profile = await get_profile(db, profile_id)
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)
    
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

async def delete_profile(db: AsyncSession, profile_id: int):
    db_profile = await get_profile(db, profile_id)
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    await db.delete(db_profile)
    await db.commit()
    return {"message": "Profile deleted successfully"}
