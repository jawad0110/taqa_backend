"""Add performance indexes

Revision ID: 9d354d0b7db5
Revises: 53789eb92fbc
Create Date: 2025-09-05 15:27:34.991697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d354d0b7db5'
down_revision: Union[str, None] = '53789eb92fbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add indexes for frequently queried fields
    op.create_index('idx_products_is_active', 'products', ['is_active'])
    op.create_index('idx_products_category_uid', 'products', ['category_uid'])
    op.create_index('idx_products_created_at', 'products', ['created_at'])
    op.create_index('idx_products_price', 'products', ['price'])
    op.create_index('idx_products_stock', 'products', ['stock'])
    
    # Add indexes for wishlist table
    op.create_index('idx_wishlists_user_uid', 'wishlists', ['user_uid'])
    op.create_index('idx_wishlists_product_uid', 'wishlists', ['product_uid'])
    op.create_index('idx_wishlists_user_product', 'wishlists', ['user_uid', 'product_uid'], unique=True)
    
    # Add indexes for cart table
    op.create_index('idx_carts_user_uid', 'carts', ['user_uid'])
    op.create_index('idx_carts_product_uid', 'carts', ['product_uid'])
    
    # Add indexes for orders table
    op.create_index('idx_orders_user_uid', 'orders', ['user_uid'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_created_at', 'orders', ['created_at'])
    
    # Add indexes for reviews table
    op.create_index('idx_reviews_product_uid', 'reviews', ['product_uid'])
    op.create_index('idx_reviews_user_uid', 'reviews', ['user_uid'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_products_is_active', 'products')
    op.drop_index('idx_products_category_uid', 'products')
    op.drop_index('idx_products_created_at', 'products')
    op.drop_index('idx_products_price', 'products')
    op.drop_index('idx_products_stock', 'products')
    
    op.drop_index('idx_wishlists_user_uid', 'wishlists')
    op.drop_index('idx_wishlists_product_uid', 'wishlists')
    op.drop_index('idx_wishlists_user_product', 'wishlists')
    
    op.drop_index('idx_carts_user_uid', 'carts')
    op.drop_index('idx_carts_product_uid', 'carts')
    
    op.drop_index('idx_orders_user_uid', 'orders')
    op.drop_index('idx_orders_status', 'orders')
    op.drop_index('idx_orders_created_at', 'orders')
    
    op.drop_index('idx_reviews_product_uid', 'reviews')
    op.drop_index('idx_reviews_user_uid', 'reviews')
