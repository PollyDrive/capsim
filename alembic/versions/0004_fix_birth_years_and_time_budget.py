"""Fix birth years to 18-65 range and time_budget type

Revision ID: 0004
Revises: 0003
Create Date: 2025-06-24 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Change date_of_birth from DateTime to Date type
    op.alter_column(
        'persons', 
        'date_of_birth',
        type_=sa.Date(),
        schema='capsim'
    )
    
    # 2. Update birth years to proper age range 18-65 years
    # Current date: 2025, so birth years should be 1960-2007
    op.execute("""
        UPDATE capsim.persons
        SET date_of_birth = CASE
            WHEN EXTRACT(YEAR FROM date_of_birth) > 2007 THEN 
                DATE(2007 - (EXTRACT(YEAR FROM date_of_birth) - 2007), EXTRACT(MONTH FROM date_of_birth), EXTRACT(DAY FROM date_of_birth))
            WHEN EXTRACT(YEAR FROM date_of_birth) < 1960 THEN
                DATE(1960 + (1960 - EXTRACT(YEAR FROM date_of_birth)), EXTRACT(MONTH FROM date_of_birth), EXTRACT(DAY FROM date_of_birth))
            ELSE date_of_birth
        END
        WHERE date_of_birth IS NOT NULL
    """)
    
    # 3. Ensure all persons have proper age range (18-65)
    # For those without dates, generate random dates in valid range
    op.execute("""
        UPDATE capsim.persons 
        SET date_of_birth = DATE('1960-01-01') + INTERVAL '1 day' * (RANDOM() * (DATE('2007-12-31') - DATE('1960-01-01')))
        WHERE date_of_birth IS NULL
    """)
    
    # 4. Change time_budget from INTEGER to FLOAT to match tech specification
    op.alter_column(
        'persons',
        'time_budget', 
        type_=sa.Float(),
        schema='capsim'
    )
    
    # 5. Update time_budget values to float range 0.0-5.0 from current integer 1-5
    op.execute("""
        UPDATE capsim.persons
        SET time_budget = CASE
            WHEN time_budget IS NULL THEN 2.5
            WHEN time_budget < 1 THEN 1.0
            WHEN time_budget > 5 THEN 5.0
            ELSE time_budget::float
        END
    """)


def downgrade() -> None:
    # Revert time_budget back to INTEGER
    op.alter_column(
        'persons',
        'time_budget',
        type_=sa.Integer(),
        schema='capsim'
    )
    
    # Revert date_of_birth back to DateTime
    op.alter_column(
        'persons',
        'date_of_birth', 
        type_=sa.DateTime(),
        schema='capsim'
    ) 