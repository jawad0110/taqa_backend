from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, and_
from typing import List, Optional
import uuid

from src.db.models import Wishlist, Product, User
from sqlalchemy.orm import selectinload


class WishlistService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_wishlist(self, user_uid: str) -> List[Wishlist]:
        """Get all wishlist items for a user"""
        statement = (
            select(Wishlist)
            .options(selectinload(Wishlist.product).selectinload(Product.images))
            .where(Wishlist.user_uid == user_uid)
            .order_by(Wishlist.added_at.desc())
        )
        result = await self.session.exec(statement)
        return result.unique().all()

    async def add_to_wishlist(self, user_uid: str, product_uid: str) -> Wishlist:
        """Add a product to user's wishlist"""
        # Check if item already exists in wishlist
        existing_statement = select(Wishlist).where(
            and_(Wishlist.user_uid == user_uid, Wishlist.product_uid == product_uid)
        )
        existing_item = await self.session.exec(existing_statement)
        existing_wishlist_item = existing_item.first()
        
        if existing_wishlist_item:
            return existing_wishlist_item

        # Check if product exists
        product_statement = select(Product).where(Product.uid == product_uid)
        product_result = await self.session.exec(product_statement)
        product = product_result.first()
        
        if not product:
            raise ValueError("Product not found")

        # Create new wishlist item
        wishlist_item = Wishlist(
            user_uid=user_uid,
            product_uid=product_uid
        )
        
        self.session.add(wishlist_item)
        await self.session.commit()
        await self.session.refresh(wishlist_item)
        
        return wishlist_item

    async def remove_from_wishlist(self, user_uid: str, product_uid: str) -> bool:
        """Remove a product from user's wishlist"""
        statement = select(Wishlist).where(
            and_(Wishlist.user_uid == user_uid, Wishlist.product_uid == product_uid)
        )
        result = await self.session.exec(statement)
        wishlist_item = result.first()
        
        if not wishlist_item:
            return False
            
        await self.session.delete(wishlist_item)
        await self.session.commit()
        return True

    async def is_in_wishlist(self, user_uid: str, product_uid: str) -> bool:
        """Check if a product is in user's wishlist"""
        statement = select(Wishlist).where(
            and_(Wishlist.user_uid == user_uid, Wishlist.product_uid == product_uid)
        )
        result = await self.session.exec(statement)
        return result.first() is not None

    async def get_wishlist_count(self, user_uid: str) -> int:
        """Get the count of items in user's wishlist"""
        statement = select(Wishlist).where(Wishlist.user_uid == user_uid)
        result = await self.session.exec(statement)
        return len(result.all())

    async def batch_check_wishlist_status(self, user_uid: str, product_uids: List[str]) -> dict:
        """Check wishlist status for multiple products at once"""
        if not product_uids:
            return {}
            
        statement = select(Wishlist.product_uid).where(
            and_(Wishlist.user_uid == user_uid, Wishlist.product_uid.in_(product_uids))
        )
        result = await self.session.exec(statement)
        wishlist_product_uids = set(str(uid) for uid in result.all())
        
        return {product_uid: product_uid in wishlist_product_uids for product_uid in product_uids}
