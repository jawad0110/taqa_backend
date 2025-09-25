"""remove categories

Revision ID: 15b4f3ad74c9
Revises: 9d354d0b7db5
Create Date: 2025-09-07 15:27:45.687652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15b4f3ad74c9'
down_revision: Union[str, None] = '9d354d0b7db5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
