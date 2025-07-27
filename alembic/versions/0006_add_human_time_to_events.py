"""Add human_time field to events table

Revision ID: 0006_add_human_time_to_events
Revises: 9d1e1e1e1e1e
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_add_human_time_to_events'
down_revision = '9d1e1e1e1e1e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add human_time column to events table."""
    # Add the human_time column
    op.add_column('events', sa.Column('human_time', sa.String(5), nullable=True))
    
    # Create an index on human_time for better query performance
    op.create_index('ix_events_human_time', 'events', ['human_time'])


def downgrade() -> None:
    """Remove human_time column from events table."""
    # Drop the index first
    op.drop_index('ix_events_human_time', table_name='events')
    
    # Drop the column
    op.drop_column('events', 'human_time')