from sqlmodel import Relationship, SQLModel, Field, Column
import sqlalchemy.dialects.postgresql as pg
from datetime import date, datetime
from typing import List, Optional
from pydantic import EmailStr
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Boolean, Integer, event, Numeric
from enum import Enum


"""
___________________________________________________

1.  User Table
___________________________________________________

"""
class User(SQLModel, table = True):
    __tablename__ = 'users'
    uid : uuid.UUID = Field(
        sa_column = Column(
            pg.UUID,
            nullable = False,
            primary_key = True,
            default = uuid.uuid4
        )
    )
    username : str
    email : str = Field(sa_column=Column(String, unique=True, index=True))
    first_name : str
    last_name : str
    role : str = Field(sa_column=Column(
        pg.VARCHAR, nullable=False, server_default='user'
    ))
    is_verified : bool = Field(default = False)
    password_hash : str = Field(exclude=True)
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))

    products: List["Product"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin'})
    reviews: List["Review"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin'})
    cart_items: list["Cart"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin'})
    wishlist_items: List["Wishlist"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin', 'cascade': 'all, delete-orphan'})
    profile: Optional["Profile"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin', 'cascade': 'all, delete-orphan'})
    shipping_addresses: List["ShippingAddress"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin', 'cascade': 'all, delete-orphan'})
    orders: List["Order"] = Relationship(back_populates="user", sa_relationship_kwargs={'lazy':'selectin', 'cascade': 'all, delete-orphan'})
        
    def __repr__(self):
        return f'<User {self.username}>'



"""
___________________________________________________

3.  Product Table
___________________________________________________

"""
class Product(SQLModel, table=True):
    __tablename__ = "products"

    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    title: str
    description: str
    price: float = Field(sa_column=Column(Numeric(10, 2), nullable=False))  # 10 total digits, 2 decimal places
    cost_price: float = Field(sa_column=Column(Numeric(10, 2), nullable=False), default=0.0)  # Cost price, only visible to admin
    # Stock for products without variants. Required field with minimum value of 0
    stock: int = Field(sa_column=Column(Integer, nullable=False), ge=0)

    is_active: bool = Field(nullable=False, default=True)
    user_uid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))

    user: Optional[User] = Relationship(back_populates="products")
    reviews: List["Review"] = Relationship(back_populates="product", sa_relationship_kwargs={'lazy':'selectin'}) # type: ignore  
    cart_items: list["Cart"] = Relationship(back_populates="product", sa_relationship_kwargs={'lazy':'selectin'})
    wishlist_items: List["Wishlist"] = Relationship(back_populates="product", sa_relationship_kwargs={'lazy':'selectin'})
    variant_groups: List["VariantGroup"] = Relationship(back_populates="product", sa_relationship_kwargs={'lazy':'selectin'})
    images: list["ProductImage"] = Relationship(back_populates="product", sa_relationship_kwargs={'lazy': 'selectin'})
    order_items: List["OrderItem"] = Relationship(back_populates="product", sa_relationship_kwargs={'lazy': 'selectin'})

    def __repr__(self):
        return f"<Product {self.title}>"

    @property
    def available_stock(self) -> Optional[int]:
        """
        Returns the available stock for the product:
        - If product has variants:
            - If any variant stock is None (unlimited), returns None.
            - Otherwise, returns the sum of all variant stocks.
        - If product has no variants:
            - Returns the product's own stock field (None means unlimited).
        """
        if self.variant_groups:
            variant_choices = []
            for group in self.variant_groups:
                variant_choices.extend(getattr(group, 'choices', []))
            if not variant_choices:
                return self.stock  # fallback to product stock if no choices
            if any(choice.stock is None for choice in variant_choices):
                return None
            return sum(choice.stock or 0 for choice in variant_choices)
        # No variants: use product's own stock
        return self.stock

    @property
    def in_stock(self) -> bool:
        """
        Returns True if the product can be purchased (stock > 0 or unlimited).
        """
        s = self.available_stock
        return s is None or s > 0



class VariantGroup(SQLModel, table=True):
    __tablename__ = "variant_groups"

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    product_uid: uuid.UUID = Field(foreign_key="products.uid", nullable=False)
    name: str = Field(sa_column=Column(String, nullable=False))

    product: "Product" = Relationship(back_populates="variant_groups", sa_relationship_kwargs={'lazy':'selectin'})
    choices: List["VariantChoice"] = Relationship(back_populates="group", sa_relationship_kwargs={'lazy':'selectin'})


class VariantChoice(SQLModel, table=True):
    __tablename__ = "variant_choices"

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    group_id: uuid.UUID = Field(foreign_key="variant_groups.id", nullable=False)
    value: str = Field(sa_column=Column(String, nullable=False))
    # Stock for this variant choice. Required field with minimum value of 0
    stock: int = Field(sa_column=Column(Integer, nullable=False), ge=0)
    # Additional price for this variant choice. Optional field
    extra_price: Optional[float] = Field(sa_column=Column(Numeric(10, 2), default=0.0))  # 10 total digits, 2 decimal places

    group: "VariantGroup" = Relationship(back_populates="choices", sa_relationship_kwargs={'lazy':'selectin'})



class ProductImage(SQLModel, table=True):
    __tablename__ = "product_images"

    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    product_uid: uuid.UUID = Field(foreign_key="products.uid", nullable=False)
    filename: str = Field(sa_column=Column(String, nullable=False))
    is_main: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))

    product: Optional["Product"] = Relationship(back_populates="images")

    def __repr__(self):
        return f"<ProductImage {self.filename} for Product {self.product_uid}>"


"""
___________________________________________________

4.  Review Table
___________________________________________________

"""
class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    rating: int = Field(lt=6)
    review_text: str
    user_uid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    product_uid: Optional[uuid.UUID] = Field(default=None, foreign_key="products.uid")
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    
    user: Optional[User] = Relationship(back_populates="reviews")
    product: Optional[Product] = Relationship(back_populates="reviews")

    def __repr__(self):
        return f"<Review for book {self.book_uid} by user {self.user_uid}>"


"""
___________________________________________________

5.  Cart Table
___________________________________________________

"""
class Cart(SQLModel, table=True):
    __tablename__ = "carts"

    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )

    user_uid: uuid.UUID = Field(default=None, foreign_key="users.uid")
    product_uid: uuid.UUID = Field(default=None, foreign_key="products.uid", nullable=False)
    variant_choice_id: Optional[uuid.UUID] = Field(default=None, foreign_key="variant_choices.id", nullable=True)
    quantity: int = Field(default=1, gt=0)
    added_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    # Relationships
    user: Optional["User"] = Relationship(back_populates="cart_items")
    product: Optional["Product"] = Relationship(back_populates="cart_items", sa_relationship_kwargs={'lazy':'selectin'})
    variant_choice: Optional["VariantChoice"] = Relationship(sa_relationship_kwargs={'lazy':'selectin'})

    @property
    def product_title(self) -> Optional[str]:
        return self.product.title if self.product else None
    

"""
___________________________________________________

6.  Wishlist Table
___________________________________________________

"""
class Wishlist(SQLModel, table=True):
    __tablename__ = "wishlists"

    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )

    user_uid: uuid.UUID = Field(default=None, foreign_key="users.uid")
    product_uid: uuid.UUID = Field(default=None, foreign_key="products.uid", nullable=False)
    added_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="wishlist_items")
    product: Optional["Product"] = Relationship(back_populates="wishlist_items", sa_relationship_kwargs={'lazy':'selectin'})

    @property
    def product_title(self) -> Optional[str]:
        return self.product.title if self.product else None


"""
___________________________________________________

7.  orders/Checkout Table
___________________________________________________

"""
class ShippingAddress(SQLModel, table=True):
    __tablename__ = "shipping_address"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    user_uid: uuid.UUID = Field(default=None, foreign_key="users.uid")
    full_name: str
    phone_number: str
    country: str
    city: str
    area: str
    street: str
    building_number: Optional[str] = None
    apartment_number: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None
    
    user: User = Relationship(back_populates="shipping_addresses")
    orders: List["Order"] = Relationship(back_populates="shipping_address")


def generate_taqa_uid():
    return f"TQA-{uuid.uuid4().hex[:6].upper()}"  # Example: TQA-3F9D1A

class OrderStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    canceled = "canceled"
    
    
class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    uid: str = Field(default_factory=generate_taqa_uid, primary_key=True, index=True, unique=True)
    user_uid: uuid.UUID = Field(default=None, foreign_key="users.uid")
    user: User = Relationship(back_populates="orders", sa_relationship_kwargs={'lazy': 'selectin'})
    status: OrderStatus = Field(default=OrderStatus.pending)
    total_price: float
    discount: float = Field(sa_column=Column(Numeric(10, 2), default=0.0))
    final_price: float = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    shipping_rate_uid: uuid.UUID = Field(default=None, foreign_key="shipping_rates.uid")
    shipping_price: float = Field(sa_column=Column(Numeric(10, 2), default=0.0))
    shipping_address_uid: uuid.UUID = Field(default=None, sa_column=Column("shipping_address", pg.UUID, ForeignKey("shipping_address.uid"), nullable=False))
    coupon_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    user: User = Relationship(back_populates="orders", sa_relationship_kwargs={'lazy': 'selectin'})
    shipping_address: ShippingAddress = Relationship(back_populates="orders")
    shipping_rate: "ShippingRate" = Relationship(back_populates="orders", sa_relationship_kwargs={'lazy': 'selectin', 'single_parent': True})
    items: list["OrderItem"] = Relationship(back_populates="order", sa_relationship_kwargs={'lazy': 'selectin', 'cascade': 'all, delete-orphan'})


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    order_uid: str = Field(default=None, foreign_key="orders.uid")
    product_uid: uuid.UUID = Field(default=None, foreign_key="products.uid")
    variant_choice_id: Optional[uuid.UUID] = Field(
        default=None, 
        foreign_key="variant_choices.id",
        nullable=True
    )
    quantity: int
    price_at_purchase: float
    total_price: float
    
    order: Order = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="order_items", sa_relationship_kwargs={'lazy': 'selectin'})
    variant_choice: Optional["VariantChoice"] = Relationship(
        sa_relationship_kwargs={'lazy': 'selectin'}
    )


class ShippingRate(SQLModel, table=True):
    __tablename__ = "shipping_rates"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    country: str = Field(sa_column=Column(String, nullable=False))
    city: str = Field(sa_column=Column(String, nullable=False))
    price: float = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    
    orders: List["Order"] = Relationship(back_populates="shipping_rate", sa_relationship_kwargs={'lazy': 'selectin', 'cascade': 'all, delete-orphan'})


"""
___________________________________________________

8.  Discount Table
___________________________________________________

"""
class Discount(SQLModel, table=True):
    __tablename__ = "discounts"

    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    code: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    discount_type: str = Field(sa_column=Column(String, nullable=False))  # "percent" or "amount"
    value: float = Field(sa_column=Column(Numeric(10, 2), nullable=False))  # e.g., 15 for 15% or 5 for 5 JOD
    minimum_order_amount: Optional[float] = Field(sa_column=Column(Numeric(10, 2), nullable=True))
    is_active: bool = True
    expires_at: Optional[datetime] = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True))
    usage_limit: Optional[int] = None
    used_count: int = 0
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.now))


"""
___________________________________________________

9.  Profile Table
___________________________________________________

"""
class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    
    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    user_id: uuid.UUID = Field(foreign_key="users.uid", nullable=False, unique=True)
    first_name: str
    last_name: str
    email: str = Field(sa_column=Column(String, unique=True, index=True))
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    
    user: User = Relationship(back_populates="profile")

    def __repr__(self):
        return f"<Profile for user {self.user_id}>"

# Event listeners for automatic profile updates
@event.listens_for(User, 'after_insert')
def create_profile(mapper, connection, target):
    """Automatically create a profile when a new user is created"""
    from sqlalchemy import insert
    profile_table = Profile.__table__
    connection.execute(
        insert(profile_table).values(
            user_id=target.uid,
            first_name=target.first_name,
            last_name=target.last_name,
            email=target.email
        )
    )

@event.listens_for(User, 'after_update')
def update_profile(mapper, connection, target):
    """Automatically update profile when user details change"""
    from sqlalchemy import update
    if target.profile:
        profile_table = Profile.__table__
        connection.execute(
            update(profile_table)
            .where(profile_table.c.user_id == target.uid)
            .values(
                first_name=target.first_name,
                last_name=target.last_name,
                email=target.email,
                updated_at=datetime.now()
            )
        )

