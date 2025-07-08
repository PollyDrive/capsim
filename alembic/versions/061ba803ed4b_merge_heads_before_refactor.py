"""merge_heads_before_refactor

Revision ID: 061ba803ed4b
Revises: 0005, 2bebdbfef5d5
Create Date: 2025-07-06 14:38:58.691704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '061ba803ed4b'
down_revision: Union[str, Sequence[str], None] = ('0005', '2bebdbfef5d5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
