"""add_unified_activity_fields_to_simulation_participants

Revision ID: 9d1e1e1e1e1e
Revises: 8a2c1e5d9abc
Create Date: 2025-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9d1e1e1e1e1e'
down_revision: Union[str, Sequence[str], None] = '8a2c1e5d9abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('simulation_participants', sa.Column('last_activity_ts', sa.Float(), nullable=True), schema='capsim')
    op.add_column('simulation_participants', sa.Column('last_activity_type', sa.String(length=50), nullable=True), schema='capsim')
    op.add_column('simulation_participants', sa.Column('total_activities_today', sa.Integer(), server_default='0', nullable=False), schema='capsim')

def downgrade() -> None:
    op.drop_column('simulation_participants', 'total_activities_today', schema='capsim')
    op.drop_column('simulation_participants', 'last_activity_type', schema='capsim')
    op.drop_column('simulation_participants', 'last_activity_ts', schema='capsim') 