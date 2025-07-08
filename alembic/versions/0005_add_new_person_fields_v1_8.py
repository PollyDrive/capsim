"""Add new person fields for v1.8 - purchases tracking and action cooldowns

Revision ID: 0005
Revises: 43e5b55f1cc6
Create Date: 2025-01-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '43e5b55f1cc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields for v1.8 action system."""
    
    # Add new Person fields for action tracking
    op.add_column('persons', sa.Column('purchases_today', sa.SmallInteger(), server_default='0', nullable=False), schema='capsim')
    op.add_column('persons', sa.Column('last_post_ts', sa.Double(), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('last_selfdev_ts', sa.Double(), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('last_purchase_ts', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), schema='capsim')
    
    # Add GIN index for JSONB operations on last_purchase_ts
    op.create_index(
        'idx_persons_last_purchase_ts',
        'persons',
        ['last_purchase_ts'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'last_purchase_ts': 'jsonb_path_ops'},
        schema='capsim'
    )
    
    # Add constraint to ensure purchases_today is non-negative
    op.create_check_constraint(
        'check_purchases_today_positive',
        'persons',
        'purchases_today >= 0',
        schema='capsim'
    )
    
    # Add constraint to ensure energy_level is non-negative (if not exists)
    # First check if constraint exists to avoid duplicate creation
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'check_energy_level_positive'
                AND conrelid = 'capsim.persons'::regclass
            ) THEN
                ALTER TABLE capsim.persons 
                ADD CONSTRAINT check_energy_level_positive 
                CHECK (energy_level >= 0);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove v1.8 fields and constraints."""
    
    # Drop constraints
    op.drop_constraint('check_purchases_today_positive', 'persons', schema='capsim')
    op.drop_constraint('check_energy_level_positive', 'persons', schema='capsim')
    
    # Drop index
    op.drop_index('idx_persons_last_purchase_ts', 'persons', schema='capsim')
    
    # Drop columns
    op.drop_column('persons', 'last_purchase_ts', schema='capsim')
    op.drop_column('persons', 'last_selfdev_ts', schema='capsim')
    op.drop_column('persons', 'last_post_ts', schema='capsim')
    op.drop_column('persons', 'purchases_today', schema='capsim') 