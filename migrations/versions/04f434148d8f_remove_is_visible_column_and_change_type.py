"""Remove is_visible column and change type"""


from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '04f434148d8f'
down_revision: Union[str, None] = '878e9d0c2e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the existing 'is_visible' column
    op.drop_column('products', 'is_visible')
    
    # Add the 'is_visible' column with the correct type (boolean)
    op.add_column('products', sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()))

def downgrade():
    # In case you need to downgrade, revert the changes
    op.drop_column('products', 'is_visible')
    op.add_column('products', sa.Column('is_visible', sa.Float(), nullable=False))
