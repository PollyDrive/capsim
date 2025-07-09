"""add_sentiment_to_trends

Revision ID: 9c3c4e6afa12
Revises: 8a2c1e5d9abc
Create Date: 2025-07-09 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c3c4e6afa12'
down_revision: Union[str, Sequence[str], None] = '8a2c1e5d9abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add sentiment column to capsim.trends."""
    op.add_column('trends', sa.Column('sentiment', sa.String(length=10), nullable=False, server_default='Positive'), schema='capsim')

    # Optional: create index for faster filtering by sentiment
    op.create_index('idx_trends_sentiment', 'trends', ['sentiment'], schema='capsim')


def downgrade() -> None:
    op.drop_index('idx_trends_sentiment', table_name='trends', schema='capsim')
    op.drop_column('trends', 'sentiment', schema='capsim') 