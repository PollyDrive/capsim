"""create_topic_interest_mapping

Revision ID: 2bebdbfef5d5
Revises: 43e5b55f1cc6
Create Date: 2025-06-27 16:06:24.092718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bebdbfef5d5'
down_revision: Union[str, Sequence[str], None] = '43e5b55f1cc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create topic_interest_mapping table and seed canonical mappings."""
    # Create the table
    op.create_table(
        'topic_interest_mapping',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('topic_code', sa.String(20), nullable=False, unique=True),
        sa.Column('topic_display', sa.String(50), nullable=False),
        sa.Column('interest_category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        schema='capsim'
    )
    
    # Seed canonical mappings (7 rows as specified)
    mapping_data = [
        ('ECONOMIC', 'Economic', 'Economics', 'Economic trends and financial topics'),
        ('HEALTH', 'Health', 'Wellbeing', 'Health, wellness and medical topics'),
        ('SPIRITUAL', 'Spiritual', 'Spirituality', 'Spiritual, religious and philosophical topics'),
        ('CONSPIRACY', 'Conspiracy', 'Society', 'Conspiracy theories and social distrust topics'),
        ('SCIENCE', 'Science', 'Knowledge', 'Scientific discoveries and educational content'),
        ('CULTURE', 'Culture', 'Creativity', 'Cultural events, arts and creative expression'),
        ('SPORT', 'Sport', 'Society', 'Sports events and physical activities')
    ]
    
    # Insert the mappings
    connection = op.get_bind()
    for topic_code, topic_display, interest_category, description in mapping_data:
        connection.execute(
            sa.text("""
                INSERT INTO capsim.topic_interest_mapping 
                (topic_code, topic_display, interest_category, description) 
                VALUES (:topic_code, :topic_display, :interest_category, :description)
            """),
            {
                'topic_code': topic_code,
                'topic_display': topic_display, 
                'interest_category': interest_category,
                'description': description
            }
        )


def downgrade() -> None:
    """Drop topic_interest_mapping table."""
    op.drop_table('topic_interest_mapping', schema='capsim')
