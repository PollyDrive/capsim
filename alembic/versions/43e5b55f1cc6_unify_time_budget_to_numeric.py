"""unify_time_budget_to_numeric

Revision ID: 43e5b55f1cc6
Revises: 0004
Create Date: 2025-06-27 15:08:34.872549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '43e5b55f1cc6'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - унифицируем time_budget к NUMERIC(2,1) и energy_level к 5.0 по умолчанию."""
    # Изменяем time_budget на NUMERIC(2,1) с дефолтом 2.5
    op.execute("ALTER TABLE capsim.persons ALTER COLUMN time_budget TYPE numeric(2,1) USING time_budget::numeric(2,1)")
    op.alter_column('persons', 'time_budget',
                    existing_type=postgresql.NUMERIC(precision=2, scale=1),
                    type_=postgresql.NUMERIC(precision=2, scale=1),
                    existing_nullable=True,
                    server_default='2.5',
                    schema='capsim')
    
    # Унифицируем energy_level дефолт к 5.0 (как в DB модели)
    op.alter_column('persons', 'energy_level',
                    existing_type=sa.Float(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    server_default='5.0',
                    schema='capsim')


def downgrade() -> None:
    """Downgrade schema - возвращаем обратно к Float."""
    # Возвращаем time_budget к Float
    op.execute("ALTER TABLE capsim.persons ALTER COLUMN time_budget TYPE double precision USING time_budget::double precision")
    op.alter_column('persons', 'time_budget',
                    existing_type=sa.Float(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    server_default='2.5',
                    schema='capsim')
    
    # Возвращаем energy_level дефолт к 0.0
    op.alter_column('persons', 'energy_level',
                    existing_type=sa.Float(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    server_default='0.0',
                    schema='capsim') 