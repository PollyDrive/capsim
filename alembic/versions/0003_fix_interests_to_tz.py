"""Fix interests to match TZ specification

Revision ID: 0003
Revises: 0002
Create Date: 2025-06-24 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clear and rebuild agent_interests with correct TZ values
    op.execute("DELETE FROM capsim.agent_interests")
    
    op.execute("""
        INSERT INTO capsim.agent_interests (profession, interest_name, min_value, max_value) VALUES
        -- Economics, Wellbeing, Spirituality, Knowledge, Creativity, Society (from TZ spec)
        
        -- Artist
        ('Artist', 'Economics', 0.86, 1.46),
        ('Artist', 'Wellbeing', 0.91, 1.51),
        ('Artist', 'Spirituality', 2.01, 2.61),
        ('Artist', 'Knowledge', 1.82, 2.42),
        ('Artist', 'Creativity', 3.72, 4.32),
        ('Artist', 'Society', 1.94, 2.54),
        
        -- Businessman
        ('Businessman', 'Economics', 4.01, 4.61),
        ('Businessman', 'Wellbeing', 0.76, 1.36),
        ('Businessman', 'Spirituality', 0.91, 1.51),
        ('Businessman', 'Knowledge', 1.35, 1.95),
        ('Businessman', 'Creativity', 2.04, 2.64),
        ('Businessman', 'Society', 2.42, 3.02),
        
        -- Developer
        ('Developer', 'Economics', 1.82, 2.42),
        ('Developer', 'Wellbeing', 1.15, 1.75),
        ('Developer', 'Spirituality', 0.72, 1.32),
        ('Developer', 'Knowledge', 4.05, 4.65),
        ('Developer', 'Creativity', 2.31, 2.91),
        ('Developer', 'Society', 1.59, 2.19),
        
        -- Doctor
        ('Doctor', 'Economics', 1.02, 1.62),
        ('Doctor', 'Wellbeing', 3.97, 4.57),
        ('Doctor', 'Spirituality', 1.37, 1.97),
        ('Doctor', 'Knowledge', 2.01, 2.61),
        ('Doctor', 'Creativity', 1.58, 2.18),
        ('Doctor', 'Society', 2.45, 3.05),
        
        -- SpiritualMentor
        ('SpiritualMentor', 'Economics', 0.62, 1.22),
        ('SpiritualMentor', 'Wellbeing', 2.04, 2.64),
        ('SpiritualMentor', 'Spirituality', 3.86, 4.46),
        ('SpiritualMentor', 'Knowledge', 2.11, 2.71),
        ('SpiritualMentor', 'Creativity', 2.12, 2.72),
        ('SpiritualMentor', 'Society', 1.95, 2.55),
        
        -- Teacher
        ('Teacher', 'Economics', 1.32, 1.92),
        ('Teacher', 'Wellbeing', 2.16, 2.76),
        ('Teacher', 'Spirituality', 1.40, 2.00),
        ('Teacher', 'Knowledge', 3.61, 4.21),
        ('Teacher', 'Creativity', 1.91, 2.51),
        ('Teacher', 'Society', 2.24, 2.84),
        
        -- ShopClerk
        ('ShopClerk', 'Economics', 4.59, 5.0),
        ('ShopClerk', 'Wellbeing', 0.74, 1.34),
        ('ShopClerk', 'Spirituality', 0.64, 1.24),
        ('ShopClerk', 'Knowledge', 1.15, 1.75),
        ('ShopClerk', 'Creativity', 1.93, 2.53),
        ('ShopClerk', 'Society', 2.70, 3.30),
        
        -- Worker
        ('Worker', 'Economics', 3.97, 4.57),
        ('Worker', 'Wellbeing', 1.05, 1.65),
        ('Worker', 'Spirituality', 1.86, 2.46),
        ('Worker', 'Knowledge', 1.83, 2.43),
        ('Worker', 'Creativity', 0.87, 1.47),
        ('Worker', 'Society', 0.69, 1.29),
        
        -- Politician
        ('Politician', 'Economics', 0.51, 1.11),
        ('Politician', 'Wellbeing', 1.63, 2.23),
        ('Politician', 'Spirituality', 0.32, 0.92),
        ('Politician', 'Knowledge', 2.07, 2.67),
        ('Politician', 'Creativity', 1.73, 2.33),
        ('Politician', 'Society', 3.57, 4.17),
        
        -- Blogger
        ('Blogger', 'Economics', 1.32, 1.92),
        ('Blogger', 'Wellbeing', 1.01, 1.61),
        ('Blogger', 'Spirituality', 1.20, 1.80),
        ('Blogger', 'Knowledge', 1.23, 1.83),
        ('Blogger', 'Creativity', 3.27, 3.87),
        ('Blogger', 'Society', 2.43, 3.03),
        
        -- Unemployed
        ('Unemployed', 'Economics', 0.72, 1.32),
        ('Unemployed', 'Wellbeing', 1.38, 1.98),
        ('Unemployed', 'Spirituality', 3.69, 4.29),
        ('Unemployed', 'Knowledge', 2.15, 2.75),
        ('Unemployed', 'Creativity', 2.33, 2.93),
        ('Unemployed', 'Society', 2.42, 3.02),
        
        -- Philosopher
        ('Philosopher', 'Economics', 1.06, 1.66),
        ('Philosopher', 'Wellbeing', 2.22, 2.82),
        ('Philosopher', 'Spirituality', 3.71, 4.31),
        ('Philosopher', 'Knowledge', 3.01, 3.61),
        ('Philosopher', 'Creativity', 2.21, 2.81),
        ('Philosopher', 'Society', 1.80, 2.40)
    """)
    
    # Update affinity_map with CORRECT TREND TOPICS (Economic, Health, Spiritual, Conspiracy, Science, Culture, Sport)
    op.execute("DELETE FROM capsim.affinity_map")
    
    op.execute("""
        INSERT INTO capsim.affinity_map (topic, profession, affinity_score) VALUES
        -- Economic (trend topic)
        ('Economic', 'ShopClerk', 4.8), ('Economic', 'Worker', 3.2), ('Economic', 'Developer', 2.1),
        ('Economic', 'Politician', 3.8), ('Economic', 'Blogger', 2.5), ('Economic', 'Businessman', 4.9),
        ('Economic', 'Doctor', 2.0), ('Economic', 'Teacher', 2.3), ('Economic', 'Unemployed', 1.8),
        ('Economic', 'Artist', 1.9), ('Economic', 'SpiritualMentor', 1.5), ('Economic', 'Philosopher', 2.2),
        
        -- Health (trend topic)  
        ('Health', 'ShopClerk', 1.2), ('Health', 'Worker', 1.8), ('Health', 'Developer', 1.6),
        ('Health', 'Politician', 2.4), ('Health', 'Blogger', 1.9), ('Health', 'Businessman', 1.4),
        ('Health', 'Doctor', 4.8), ('Health', 'Teacher', 2.8), ('Health', 'Unemployed', 2.1),
        ('Health', 'Artist', 1.7), ('Health', 'SpiritualMentor', 3.2), ('Health', 'Philosopher', 2.9),
        
        -- Spiritual (trend topic)
        ('Spiritual', 'ShopClerk', 1.1), ('Spiritual', 'Worker', 2.3), ('Spiritual', 'Developer', 1.4),
        ('Spiritual', 'Politician', 1.2), ('Spiritual', 'Blogger', 1.8), ('Spiritual', 'Businessman', 1.6),
        ('Spiritual', 'Doctor', 2.1), ('Spiritual', 'Teacher', 2.2), ('Spiritual', 'Unemployed', 4.1),
        ('Spiritual', 'Artist', 2.8), ('Spiritual', 'SpiritualMentor', 4.9), ('Spiritual', 'Philosopher', 4.2),
        
        -- Conspiracy (trend topic)
        ('Conspiracy', 'ShopClerk', 1.5), ('Conspiracy', 'Worker', 1.9), ('Conspiracy', 'Developer', 1.2),
        ('Conspiracy', 'Politician', 1.8), ('Conspiracy', 'Blogger', 2.3), ('Conspiracy', 'Businessman', 1.4),
        ('Conspiracy', 'Doctor', 1.1), ('Conspiracy', 'Teacher', 1.6), ('Conspiracy', 'Unemployed', 2.8),
        ('Conspiracy', 'Artist', 2.1), ('Conspiracy', 'SpiritualMentor', 2.4), ('Conspiracy', 'Philosopher', 2.7),
        
        -- Science (trend topic)
        ('Science', 'ShopClerk', 1.3), ('Science', 'Worker', 1.7), ('Science', 'Developer', 4.2),
        ('Science', 'Politician', 2.5), ('Science', 'Blogger', 1.8), ('Science', 'Businessman', 1.9),
        ('Science', 'Doctor', 3.8), ('Science', 'Teacher', 4.1), ('Science', 'Unemployed', 2.2),
        ('Science', 'Artist', 2.0), ('Science', 'SpiritualMentor', 2.6), ('Science', 'Philosopher', 3.9),
        
        -- Culture (trend topic)
        ('Culture', 'ShopClerk', 2.1), ('Culture', 'Worker', 1.4), ('Culture', 'Developer', 1.8),
        ('Culture', 'Politician', 3.2), ('Culture', 'Blogger', 3.6), ('Culture', 'Businessman', 2.3),
        ('Culture', 'Doctor', 2.0), ('Culture', 'Teacher', 2.7), ('Culture', 'Unemployed', 2.5),
        ('Culture', 'Artist', 4.8), ('Culture', 'SpiritualMentor', 2.9), ('Culture', 'Philosopher', 2.8),
        
        -- Sport (trend topic)
        ('Sport', 'ShopClerk', 2.3), ('Sport', 'Worker', 2.8), ('Sport', 'Developer', 1.5),
        ('Sport', 'Politician', 2.2), ('Sport', 'Blogger', 2.1), ('Sport', 'Businessman', 2.4),
        ('Sport', 'Doctor', 1.9), ('Sport', 'Teacher', 2.0), ('Sport', 'Unemployed', 2.6),
        ('Sport', 'Artist', 1.8), ('Sport', 'SpiritualMentor', 1.7), ('Sport', 'Philosopher', 1.6)
    """)


def downgrade() -> None:
    # Restore original affinity_map data
    op.execute("DELETE FROM capsim.affinity_map")
    op.execute("DELETE FROM capsim.agent_interests") 