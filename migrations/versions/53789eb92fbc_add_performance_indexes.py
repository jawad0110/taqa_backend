"""Add performance indexes

Revision ID: 53789eb92fbc
Revises: e88b6d9635fb
Create Date: 2025-09-05 15:27:29.254880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53789eb92fbc'
down_revision: Union[str, None] = 'e88b6d9635fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
