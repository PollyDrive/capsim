"""Add person fields for Russian names and demographics

Revision ID: 0002
Revises: 0001
Create Date: 2025-06-24 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add personal information fields to persons table
    op.add_column('persons', sa.Column('first_name', sa.String(length=100), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('last_name', sa.String(length=100), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('gender', sa.String(length=10), nullable=True), schema='capsim')
    op.add_column('persons', sa.Column('date_of_birth', sa.DateTime(), nullable=True), schema='capsim')
    
    # Add complete agent_interests for all professions
    op.execute("""
        INSERT INTO capsim.agent_interests (profession, interest_name, min_value, max_value) VALUES
        -- ShopClerk
        ('ShopClerk', 'Economics', 0.6, 0.9),
        ('ShopClerk', 'Wellbeing', 0.2, 0.6),
        ('ShopClerk', 'Security', 0.3, 0.7),
        ('ShopClerk', 'Entertainment', 0.4, 0.8),
        ('ShopClerk', 'Education', 0.1, 0.5),
        ('ShopClerk', 'Technology', 0.2, 0.6),
        ('ShopClerk', 'SocialIssues', 0.3, 0.7),
        
        -- Worker
        ('Worker', 'Economics', 0.4, 0.8),
        ('Worker', 'Wellbeing', 0.3, 0.7),
        ('Worker', 'Security', 0.5, 0.9),
        ('Worker', 'Entertainment', 0.3, 0.7),
        ('Worker', 'Education', 0.1, 0.5),
        ('Worker', 'Technology', 0.1, 0.4),
        ('Worker', 'SocialIssues', 0.4, 0.8),
        
        -- Politician
        ('Politician', 'Economics', 0.5, 0.9),
        ('Politician', 'Wellbeing', 0.3, 0.7),
        ('Politician', 'Security', 0.6, 0.9),
        ('Politician', 'Entertainment', 0.4, 0.8),
        ('Politician', 'Education', 0.4, 0.8),
        ('Politician', 'Technology', 0.2, 0.6),
        ('Politician', 'SocialIssues', 0.7, 0.9),
        
        -- Blogger
        ('Blogger', 'Economics', 0.2, 0.6),
        ('Blogger', 'Wellbeing', 0.3, 0.7),
        ('Blogger', 'Security', 0.2, 0.6),
        ('Blogger', 'Entertainment', 0.7, 0.9),
        ('Blogger', 'Education', 0.3, 0.7),
        ('Blogger', 'Technology', 0.6, 0.9),
        ('Blogger', 'SocialIssues', 0.5, 0.9),
        
        -- Unemployed
        ('Unemployed', 'Economics', 0.3, 0.7),
        ('Unemployed', 'Wellbeing', 0.4, 0.8),
        ('Unemployed', 'Security', 0.5, 0.9),
        ('Unemployed', 'Entertainment', 0.6, 0.9),
        ('Unemployed', 'Education', 0.2, 0.6),
        ('Unemployed', 'Technology', 0.1, 0.5),
        ('Unemployed', 'SocialIssues', 0.6, 0.9),
        
        -- Philosopher
        ('Philosopher', 'Economics', 0.3, 0.7),
        ('Philosopher', 'Wellbeing', 0.5, 0.9),
        ('Philosopher', 'Security', 0.2, 0.6),
        ('Philosopher', 'Entertainment', 0.2, 0.6),
        ('Philosopher', 'Education', 0.7, 0.9),
        ('Philosopher', 'Technology', 0.1, 0.5),
        ('Philosopher', 'SocialIssues', 0.6, 0.9)
        ON CONFLICT (profession, interest_name) DO NOTHING
    """)


def downgrade() -> None:
    # Remove added columns
    op.drop_column('persons', 'date_of_birth', schema='capsim')
    op.drop_column('persons', 'gender', schema='capsim')
    op.drop_column('persons', 'last_name', schema='capsim')
    op.drop_column('persons', 'first_name', schema='capsim')
    
    # Remove added agent_interests (keeping only original ones)
    op.execute("""
        DELETE FROM capsim.agent_interests 
        WHERE profession IN ('ShopClerk', 'Worker', 'Politician', 'Blogger', 'Unemployed', 'Philosopher')
    """) 