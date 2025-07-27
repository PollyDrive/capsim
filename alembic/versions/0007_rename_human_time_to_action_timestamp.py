"""Rename human_time to action_timestamp in events table

Revision ID: 0007_rename_human_time_to_action_timestamp
Revises: 0006_add_human_time_to_events
Create Date: 2025-07-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_rename_human_time_to_action_timestamp'
down_revision = '0006_add_human_time_to_events'
branch_labels = None
depends_on = None


def upgrade():
    """Rename human_time column to action_timestamp in events table."""
    # Drop the old index
    op.drop_index('ix_events_human_time', table_name='events')
    
    # Rename the column
    op.alter_column('events', 'human_time', new_column_name='action_timestamp')
    
    # Create new index on action_timestamp
    op.create_index('ix_events_action_timestamp', 'events', ['action_timestamp'])


def downgrade():
    """Rename action_timestamp column back to human_time in events table."""
    # Drop the new index
    op.drop_index('ix_events_action_timestamp', table_name='events')
    
    # Rename the column back
    op.alter_column('events', 'action_timestamp', new_column_name='human_time')
    
    # Recreate the old index
    op.create_index('ix_events_human_time', 'events', ['human_time'])