"""add_variant_choice_to_order_items

Revision ID: fb60a4748566
Revises: f30548a306dd
Create Date: 2025-05-21 06:48:26.214809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb60a4748566'
down_revision: Union[str, None] = 'f30548a306dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add variant_choice_id column to order_items table
    op.add_column('order_items', 
                 sa.Column('variant_choice_id', 
                          sa.UUID(),  # Using UUID to match variant_choices.id
                          sa.ForeignKey('variant_choices.id'), 
                          nullable=True))

def downgrade() -> None:
    # Remove variant_choice_id column
    op.drop_constraint('order_items_variant_choice_id_fkey', 'order_items', type_='foreignkey')
    op.drop_column('order_items', 'variant_choice_id')