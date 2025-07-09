"""
Database models for CAPSIM 2.0 using SQLAlchemy 2.0.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, BOOLEAN, JSON, MetaData, Numeric, SmallInteger, Double
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base(metadata=MetaData(schema="capsim"))


class SimulationRun(Base):
    """Метаданные запусков симуляций."""
    __tablename__ = "simulation_runs"
    
    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="RUNNING")  # RUNNING, COMPLETED, FAILED
    num_agents = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    configuration = Column(JSON, nullable=True)
    
    # Relationships
    participants = relationship("SimulationParticipant", back_populates="simulation_run")
    trends = relationship("Trend", back_populates="simulation_run")
    events = relationship("Event", back_populates="simulation_run")


class Person(Base):
    """Глобальные агенты симуляции с базовыми атрибутами."""
    __tablename__ = "persons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profession = Column(String(50), nullable=False)
    
    # Personal information (REQUIRED FIELDS)
    first_name = Column(String(100), nullable=False)  # Russian first name
    last_name = Column(String(100), nullable=False)   # Russian last name with proper gender suffix
    gender = Column(String(10), nullable=False)       # 'male' or 'female'
    date_of_birth = Column(Date, nullable=False)   # For age calculation (18-65 years)
    
    # Dynamic attributes (0.0-5.0 scale)
    financial_capability = Column(Float, default=0.0)
    trend_receptivity = Column(Float, default=0.0)
    social_status = Column(Float, default=0.0)
    energy_level = Column(Float, default=5.0)
    
    # Time and interaction tracking
    time_budget = Column(Numeric(2, 1), default=2.5)  # 0.0-5.0 with 0.5 step
    exposure_history = Column(JSON, default=dict)  # {trend_id: timestamp}
    interests = Column(JSON, default=dict)  # {interest_name: value}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    simulation_participations = relationship("SimulationParticipant", back_populates="person")
    attribute_history = relationship("PersonAttributeHistory", back_populates="person")
    originated_trends = relationship("Trend", foreign_keys="Trend.originator_id", back_populates="originator")


class SimulationParticipant(Base):
    """Участие агента в конкретной симуляции с симуляционно-специфичными атрибутами."""
    __tablename__ = "simulation_participants"
    
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.run_id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True)
    
    # v1.8: Action tracking and cooldowns (simulation-specific)
    purchases_today = Column(SmallInteger, default=0)  # Daily purchase counter
    last_post_ts = Column(Double, nullable=True)  # Last post timestamp
    last_selfdev_ts = Column(Double, nullable=True)  # Last self-development timestamp
    last_purchase_ts = Column(JSONB, default=dict)  # {L1: timestamp, L2: timestamp, L3: timestamp}
    
    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="participants")
    person = relationship("Person", back_populates="simulation_participations")


class Trend(Base):
    """Информационные тренды в социальной сети."""
    __tablename__ = "trends"
    
    trend_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.run_id"), nullable=False)
    topic = Column(String(50), nullable=False)  # Economic, Health, Spiritual, etc.
    originator_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False)
    parent_trend_id = Column(UUID(as_uuid=True), ForeignKey("trends.trend_id"), nullable=True)
    
    # Temporal data
    timestamp_start = Column(DateTime, default=datetime.utcnow)
    
    # Virality metrics  
    base_virality_score = Column(Float, default=0.0)  # 0.0-5.0 scale
    coverage_level = Column(String(20), default="Low")  # Low/Middle/High
    total_interactions = Column(Integer, default=0)

    # v1.9 sentiment
    sentiment = Column(String(10), default="Positive", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="trends")
    originator = relationship("Person", foreign_keys=[originator_id], back_populates="originated_trends")
    parent_trend = relationship("Trend", remote_side=[trend_id])
    events = relationship("Event", back_populates="trend")


class Event(Base):
    """История всех событий симуляции."""
    __tablename__ = "events"
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.run_id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # PublishPostAction, EnergyRecovery, etc.
    priority = Column(Integer, nullable=False)  # 1-5
    timestamp = Column(Float, nullable=False)  # simulation time in minutes
    
    # Optional references
    agent_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), nullable=True)
    trend_id = Column(UUID(as_uuid=True), ForeignKey("trends.trend_id"), nullable=True)
    
    # Event data
    event_data = Column(JSON, nullable=True)  # Flexible data storage
    
    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow)
    processing_duration_ms = Column(Float, nullable=True)
    
    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="events")
    agent = relationship("Person")
    trend = relationship("Trend", back_populates="events")


class PersonAttributeHistory(Base):
    """История изменений атрибутов агентов."""
    __tablename__ = "person_attribute_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.run_id"), nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False)
    
    # Change details
    attribute_name = Column(String(50), nullable=False)
    old_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)
    
    # Change context
    reason = Column(String(100), nullable=False)  # TrendInfluence, EnergyRecovery, etc.
    source_trend_id = Column(UUID(as_uuid=True), nullable=True)
    change_timestamp = Column(Float, nullable=False)  # simulation time
    
    # Real timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    person = relationship("Person", back_populates="attribute_history")


class AgentInterests(Base):
    """Статичная таблица интересов агентов по профессиям."""
    __tablename__ = "agent_interests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profession = Column(String(50), nullable=False)
    interest_name = Column(String(50), nullable=False)  # Economics, Wellbeing, etc.
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    
    # Уникальный индекс на (profession, interest_name)
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class AffinityMap(Base):
    """Статичная таблица соответствия профессий к темам трендов."""
    __tablename__ = "affinity_map"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profession = Column(String(50), nullable=False)
    topic = Column(String(50), nullable=False)  # Economic, Health, etc.
    affinity_score = Column(Float, nullable=False)  # 1-5 scale
    
    # Уникальный индекс на (profession, topic)
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class DailyTrendSummary(Base):
    """Агрегированная статистика трендов по дням."""
    __tablename__ = "daily_trend_summary"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.run_id"), nullable=False)
    simulation_day = Column(Integer, nullable=False)  # День симуляции (1, 2, 3...)
    topic = Column(String(50), nullable=False)
    
    # Aggregated metrics
    total_interactions_today = Column(Integer, default=0)
    avg_virality_today = Column(Float, default=0.0)
    top_trend_id = Column(UUID(as_uuid=True), nullable=True)
    unique_authors_count = Column(Integer, default=0)
    pct_change_virality = Column(Float, nullable=True)  # Compared to previous day
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Уникальный индекс на (simulation_id, simulation_day, topic)
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class TopicInterestMapping(Base):
    """Централизованная таблица маппинга топиков трендов к категориям интересов."""
    __tablename__ = "topic_interest_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_code = Column(String(20), nullable=False, unique=True)  # ECONOMIC, HEALTH, etc.
    topic_display = Column(String(50), nullable=False)  # Economic, Health, etc.
    interest_category = Column(String(50), nullable=False)  # Economics, Wellbeing, etc.
    description = Column(Text, nullable=True)
    
    # Уникальный индекс на topic_code
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class AgentsProfession(Base):
    """Статичная таблица диапазонов атрибутов для каждой профессии."""
    __tablename__ = "agents_profession"

    profession = Column(String(50), primary_key=True)  # Teacher, Developer, ...

    # Диапазоны
    financial_capability_min = Column(Float, nullable=False)
    financial_capability_max = Column(Float, nullable=False)
    trend_receptivity_min = Column(Float, nullable=False)
    trend_receptivity_max = Column(Float, nullable=False)
    social_status_min = Column(Float, nullable=False)
    social_status_max = Column(Float, nullable=False)
    energy_level_min = Column(Float, nullable=False)
    energy_level_max = Column(Float, nullable=False)
    time_budget_min = Column(Float, nullable=False)
    time_budget_max = Column(Float, nullable=False)

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        {'sqlite_autoincrement': True},
    ) 