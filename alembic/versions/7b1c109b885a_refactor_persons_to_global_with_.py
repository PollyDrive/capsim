"""refactor_persons_to_global_with_simulation_participants

Revision ID: 7b1c109b885a
Revises: 061ba803ed4b
Create Date: 2025-07-06 14:39:04.107058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7b1c109b885a'
down_revision: Union[str, Sequence[str], None] = '061ba803ed4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Refactor persons to global and create simulation_participants table."""
    
    # 1. Create simulation_participants table
    op.create_table('simulation_participants',
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('purchases_today', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('last_post_ts', sa.Double(), nullable=True),
        sa.Column('last_selfdev_ts', sa.Double(), nullable=True),
        sa.Column('last_purchase_ts', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.ForeignKeyConstraint(['simulation_id'], ['capsim.simulation_runs.run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['capsim.persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('simulation_id', 'person_id'),
        schema='capsim'
    )
    
    # 2. Create indexes for simulation_participants
    op.create_index('idx_simulation_participants_simulation_id', 'simulation_participants', ['simulation_id'], schema='capsim')
    op.create_index('idx_simulation_participants_person_id', 'simulation_participants', ['person_id'], schema='capsim')
    op.create_index('idx_simulation_participants_last_purchase_ts', 'simulation_participants', ['last_purchase_ts'], 
                   unique=False, postgresql_using='gin', postgresql_ops={'last_purchase_ts': 'jsonb_path_ops'}, schema='capsim')
    
    # 3. Migrate existing data from persons to simulation_participants
    op.execute("""
        INSERT INTO capsim.simulation_participants 
        (simulation_id, person_id, purchases_today, last_post_ts, last_selfdev_ts, last_purchase_ts)
        SELECT 
            simulation_id,
            id as person_id,
            purchases_today,
            last_post_ts,
            last_selfdev_ts,
            last_purchase_ts
        FROM capsim.persons
        WHERE simulation_id IS NOT NULL
    """)
    
    # 4. Remove simulation-specific columns from persons table
    op.drop_column('persons', 'simulation_id', schema='capsim')
    op.drop_column('persons', 'purchases_today', schema='capsim')
    op.drop_column('persons', 'last_post_ts', schema='capsim')
    op.drop_column('persons', 'last_selfdev_ts', schema='capsim')
    op.drop_column('persons', 'last_purchase_ts', schema='capsim')
    
    # 5. Drop old indexes that referenced simulation_id (if they exist)
    op.execute("DROP INDEX IF EXISTS capsim.idx_persons_simulation_id")
    op.execute("DROP INDEX IF EXISTS capsim.idx_persons_last_purchase_ts")
    
    # 6. Add constraint to ensure purchases_today is non-negative in simulation_participants
    op.create_check_constraint(
        'check_simulation_participants_purchases_today_positive',
        'simulation_participants',
        'purchases_today >= 0',
        schema='capsim'
    )


def downgrade() -> None:
    """Revert changes - restore simulation_id in persons and drop simulation_participants."""
    
    # 1. Add simulation_id column back to persons
    op.add_column('persons', sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=True), schema='capsim')
    
    # 2. Add simulation-specific columns back to persons
    op.add_column('persons', sa.Column('purchases_today', sa.SmallInteger(), server_default='0', nullable=False), schema='capsim')
    op.add_column('persons', sa.Column('last_post_ts', sa.Double(), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('last_selfdev_ts', sa.Double(), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('last_purchase_ts', postgresql.JSONB(), server_default='{}', nullable=False), schema='capsim')
    
    # 3. Migrate data back from simulation_participants to persons
    op.execute("""
        UPDATE capsim.persons 
        SET 
            simulation_id = sp.simulation_id,
            purchases_today = sp.purchases_today,
            last_post_ts = sp.last_post_ts,
            last_selfdev_ts = sp.last_selfdev_ts,
            last_purchase_ts = sp.last_purchase_ts
        FROM capsim.simulation_participants sp
        WHERE capsim.persons.id = sp.person_id
    """)
    
    # 4. Add foreign key constraint back to persons
    op.create_foreign_key(
        'fk_persons_simulation_id',
        'persons', 'simulation_runs',
        ['simulation_id'], ['run_id'],
        source_schema='capsim', referent_schema='capsim'
    )
    
    # 5. Recreate old indexes
    op.create_index('idx_persons_simulation_id', 'persons', ['simulation_id'], schema='capsim')
    op.create_index('idx_persons_last_purchase_ts', 'persons', ['last_purchase_ts'], 
                   unique=False, postgresql_using='gin', postgresql_ops={'last_purchase_ts': 'jsonb_path_ops'}, schema='capsim')
    
    # 6. Add constraint back to persons
    op.create_check_constraint(
        'check_purchases_today_positive',
        'persons',
        'purchases_today >= 0',
        schema='capsim'
    )
    
    # 7. Drop simulation_participants table
    op.drop_table('simulation_participants', schema='capsim')
