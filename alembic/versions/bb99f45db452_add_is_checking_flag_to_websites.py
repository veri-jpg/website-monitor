"""add is_checking flag to websites

Revision ID: bb99f45db452
Revises: 7e91c20b139b
Create Date: 2026-06-30 02:39:54.540136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bb99f45db452'
down_revision: Union[str, None] = '7e91c20b139b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'websites',
        sa.Column('is_checking', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column('websites', 'is_checking')