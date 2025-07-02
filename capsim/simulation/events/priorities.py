"""
Event Priority System для CAPSIM v1.8

Определяет приоритеты событий в симуляции согласно техническим требованиям.
"""

from enum import IntEnum


class EventPriority(IntEnum):
    """
    Приоритеты событий в симуляции.
    
    События обрабатываются в порядке возрастания приоритета.
    При равных приоритетах - по временным меткам.
    """
    
    SYSTEM = 100       # DailyResetEvent, EnergyRecoveryEvent
    AGENT_ACTION = 50  # PublishPost, Purchase, SelfDev  
    LOW = 0            # Низкоприоритетные события


# Backward compatibility aliases
LAW = 1
WEATHER = 2
TREND = 3
AGENT_ACTION_LEGACY = 4
SYSTEM_LEGACY = 5 