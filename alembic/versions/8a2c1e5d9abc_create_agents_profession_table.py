"""create_agents_profession_table

Revision ID: 8a2c1e5d9abc
Revises: 7b1c109b885a
Create Date: 2025-07-08 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8a2c1e5d9abc'
down_revision: Union[str, Sequence[str], None] = '7b1c109b885a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agents_profession table and seed attribute ranges"""
    op.create_table(
        'agents_profession',
        sa.Column('profession', sa.String(length=50), primary_key=True),
        sa.Column('financial_capability_min', sa.Float(), nullable=False),
        sa.Column('financial_capability_max', sa.Float(), nullable=False),
        sa.Column('trend_receptivity_min', sa.Float(), nullable=False),
        sa.Column('trend_receptivity_max', sa.Float(), nullable=False),
        sa.Column('social_status_min', sa.Float(), nullable=False),
        sa.Column('social_status_max', sa.Float(), nullable=False),
        sa.Column('energy_level_min', sa.Float(), nullable=False),
        sa.Column('energy_level_max', sa.Float(), nullable=False),
        sa.Column('time_budget_min', sa.Float(), nullable=False),
        sa.Column('time_budget_max', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        schema='capsim'
    )

    # seed data based on tech v1.5 table 2.4
    seed_sql = """
    INSERT INTO capsim.agents_profession (
        profession, financial_capability_min, financial_capability_max,
        trend_receptivity_min, trend_receptivity_max,
        social_status_min, social_status_max,
        energy_level_min, energy_level_max,
        time_budget_min, time_budget_max
    ) VALUES
        ('ShopClerk', 2, 4, 1, 3, 1, 3, 2, 5, 3, 5),
        ('Worker', 2, 4, 1, 3, 1, 2, 2, 5, 3, 5),
        ('Developer', 3, 5, 3, 5, 2, 4, 2, 5, 2, 4),
        ('Politician', 3, 5, 3, 5, 4, 5, 2, 5, 2, 4),
        ('Blogger', 2, 4, 4, 5, 3, 5, 2, 5, 3, 5),
        ('Businessman', 4, 5, 2, 4, 4, 5, 2, 5, 2, 4),
        ('SpiritualMentor', 1, 3, 2, 5, 2, 4, 3, 5, 2, 4),
        ('Philosopher', 1, 3, 1, 3, 1, 3, 2, 5, 2, 4),
        ('Unemployed', 1, 2, 3, 5, 1, 2, 3, 5, 3, 5),
        ('Teacher', 1, 3, 1, 3, 2, 4, 2, 5, 2, 4),
        ('Artist', 1, 3, 2, 4, 2, 4, 4, 5, 3, 5),
        ('Doctor', 2, 4, 1, 3, 3, 5, 2, 5, 1, 2);
    """
    op.execute(seed_sql)


def downgrade() -> None:
    op.drop_table('agents_profession', schema='capsim') 