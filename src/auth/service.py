from src.db.models import User, Profile
from .schemas import UserCreateModel
from .utils import generate_passwd_hash
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select


class UserService:
    async def get_user_by_email(self, email : str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)       
        user = result.first()
        
        return user

    async def user_exists(self, email, session: AsyncSession):
        user = await self.get_user_by_email(email, session)
        
        return True if user is not None else False
    
    async def create_user(self, user_data: UserCreateModel, session: AsyncSession):
        user_data_dict = user_data.model_dump()
        new_user = User(**user_data_dict)
        new_user.password_hash = generate_passwd_hash(user_data_dict['password'])
        new_user.role = "user"
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        # Check if profile already exists
        statement = select(Profile).where(Profile.user_id == new_user.uid)
        result = await session.exec(statement)
        existing_profile = result.first()
        
        if not existing_profile:
            # Create profile automatically if it doesn't exist
            profile_data = {
                "user_id": new_user.uid,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "email": new_user.email
            }
            new_profile = Profile(**profile_data)
            session.add(new_profile)
            await session.commit()
        
        return new_user

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.items():
            setattr(user, k, v) # the setattr function is used to set the value of the attribute of an object
            await session.commit()
            
            return user