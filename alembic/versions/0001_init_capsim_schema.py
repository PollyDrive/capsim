"""Init CAPSIM schema and tables

Revision ID: 0001
Revises: 
Create Date: 2025-06-23 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema already created manually
    # op.execute("CREATE SCHEMA IF NOT EXISTS capsim")
    
    # Create simulation_runs table
    op.create_table('simulation_runs',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('num_agents', sa.Integer(), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('run_id'),
        schema='capsim'
    )
    
    # Create persons table
    op.create_table('persons',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profession', sa.String(length=50), nullable=False),
        sa.Column('financial_capability', sa.Float(), nullable=True),
        sa.Column('trend_receptivity', sa.Float(), nullable=True),
        sa.Column('social_status', sa.Float(), nullable=True),
        sa.Column('energy_level', sa.Float(), nullable=True),
        sa.Column('time_budget', sa.Integer(), nullable=True),
        sa.Column('exposure_history', sa.JSON(), nullable=True),
        sa.Column('interests', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['capsim.simulation_runs.run_id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='capsim'
    )
    
    # Create trends table
    op.create_table('trends',
        sa.Column('trend_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic', sa.String(length=50), nullable=False),
        sa.Column('originator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_trend_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp_start', sa.DateTime(), nullable=True),
        sa.Column('base_virality_score', sa.Float(), nullable=True),
        sa.Column('coverage_level', sa.String(length=20), nullable=True),
        sa.Column('total_interactions', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['originator_id'], ['capsim.persons.id'], ),
        sa.ForeignKeyConstraint(['parent_trend_id'], ['capsim.trends.trend_id'], ),
        sa.ForeignKeyConstraint(['simulation_id'], ['capsim.simulation_runs.run_id'], ),
        sa.PrimaryKeyConstraint('trend_id'),
        schema='capsim'
    )
    
    # Create events table
    op.create_table('events',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trend_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_data', sa.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_duration_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['capsim.persons.id'], ),
        sa.ForeignKeyConstraint(['simulation_id'], ['capsim.simulation_runs.run_id'], ),
        sa.ForeignKeyConstraint(['trend_id'], ['capsim.trends.trend_id'], ),
        sa.PrimaryKeyConstraint('event_id'),
        schema='capsim'
    )
    
    # Create person_attribute_history table
    op.create_table('person_attribute_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attribute_name', sa.String(length=50), nullable=False),
        sa.Column('old_value', sa.Float(), nullable=True),
        sa.Column('new_value', sa.Float(), nullable=False),
        sa.Column('delta', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('source_trend_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('change_timestamp', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['capsim.persons.id'], ),
        sa.ForeignKeyConstraint(['simulation_id'], ['capsim.simulation_runs.run_id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='capsim'
    )
    
    # Create agent_interests table
    op.create_table('agent_interests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('profession', sa.String(length=50), nullable=False),
        sa.Column('interest_name', sa.String(length=50), nullable=False),
        sa.Column('min_value', sa.Float(), nullable=False),
        sa.Column('max_value', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profession', 'interest_name'),
        schema='capsim'
    )
    
    # Create affinity_map table
    op.create_table('affinity_map',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('profession', sa.String(length=50), nullable=False),
        sa.Column('topic', sa.String(length=50), nullable=False),
        sa.Column('affinity_score', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profession', 'topic'),
        schema='capsim'
    )
    
    # Create daily_trend_summary table
    op.create_table('daily_trend_summary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_day', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(length=50), nullable=False),
        sa.Column('total_interactions_today', sa.Integer(), nullable=True),
        sa.Column('avg_virality_today', sa.Float(), nullable=True),
        sa.Column('top_trend_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('unique_authors_count', sa.Integer(), nullable=True),
        sa.Column('pct_change_virality', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['capsim.simulation_runs.run_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('simulation_id', 'simulation_day', 'topic'),
        schema='capsim'
    )
    
    # Create indexes for performance
    op.create_index('idx_persons_simulation_id', 'persons', ['simulation_id'], schema='capsim')
    op.create_index('idx_trends_simulation_id', 'trends', ['simulation_id'], schema='capsim')
    op.create_index('idx_trends_topic', 'trends', ['topic'], schema='capsim')
    op.create_index('idx_events_simulation_id', 'events', ['simulation_id'], schema='capsim')
    op.create_index('idx_events_timestamp', 'events', ['timestamp'], schema='capsim')
    op.create_index('idx_events_priority', 'events', ['priority'], schema='capsim')


def downgrade() -> None:
    # Drop all tables
    op.drop_table('daily_trend_summary', schema='capsim')
    op.drop_table('affinity_map', schema='capsim')
    op.drop_table('agent_interests', schema='capsim')
    op.drop_table('person_attribute_history', schema='capsim')
    op.drop_table('events', schema='capsim')
    op.drop_table('trends', schema='capsim')
    op.drop_table('persons', schema='capsim')
    op.drop_table('simulation_runs', schema='capsim')
    
    # Drop schema
    op.execute("DROP SCHEMA IF EXISTS capsim CASCADE") 