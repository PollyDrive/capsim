"""
Clock abstraction для поддержки realtime и fast симуляций.
"""

import time
import asyncio
import os
from typing import Protocol
from abc import abstractmethod
import logging

logger = logging.getLogger(__name__)


class Clock(Protocol):
    """
    Протокол для управления временем симуляции.
    
    Позволяет переключаться между fast и realtime режимами
    без изменения основного кода движка.
    """
    
    @abstractmethod
    def now(self) -> float:
        """
        Возвращает текущее время симуляции в минутах.
        
        Returns:
            float: Время в минутах от начала симуляции
        """
        pass
    
    @abstractmethod
    async def sleep_until(self, timestamp: float) -> None:
        """
        Ожидает наступления указанного времени симуляции.
        
        Args:
            timestamp: Целевое время симуляции в минутах
        """
        pass


class SimClock:
    """
    Legacy clock для максимальной скорости симуляции.
    
    Используется для тестирования и быстрого анализа.
    Не выполняет реальных задержек.
    """
    
    def __init__(self, start_time: float = 0.0):
        self.current_time = start_time
        
    def now(self) -> float:
        """Возвращает текущее симуляционное время."""
        return self.current_time
        
    async def sleep_until(self, timestamp: float) -> None:
        """
        No-op sleep для максимальной скорости.
        
        Args:
            timestamp: Целевое время (игнорируется)
        """
        self.current_time = max(self.current_time, timestamp)
        # Micro-yield для cooperative multitasking
        await asyncio.sleep(0)


class RealTimeClock:
    """
    Realtime clock с синхронизацией по настенному времени.
    
    Использует SIM_SPEED_FACTOR для управления скоростью:
    - 1.0 = реальное время
    - 60.0 = 60x ускорение  
    - 0.5 = 2x замедление
    """
    
    def __init__(self, speed_factor: float = None):
        self.speed_factor = speed_factor or float(os.getenv("SIM_SPEED_FACTOR", "60"))
        self.start_real_time = time.time()
        self.start_sim_time = 0.0
        
        # Валидация speed_factor
        if not (0.1 <= self.speed_factor <= 1000.0):
            raise ValueError(f"SIM_SPEED_FACTOR must be between 0.1 and 1000, got {self.speed_factor}")
            
        logger.info({
            "event": "realtime_clock_initialized",
            "speed_factor": self.speed_factor,
            "start_real_time": self.start_real_time
        })
        
    def now(self) -> float:
        """
        Возвращает текущее симуляционное время на основе реального времени.
        
        Returns:
            float: Время в минутах от начала симуляции
        """
        elapsed_real = time.time() - self.start_real_time
        elapsed_sim_minutes = elapsed_real * self.speed_factor / 60.0
        return self.start_sim_time + elapsed_sim_minutes
        
    async def sleep_until(self, target_sim_time: float) -> None:
        """
        Ожидает наступления целевого времени симуляции.
        
        Args:
            target_sim_time: Целевое время симуляции в минутах
        """
        current_sim_time = self.now()
        
        if target_sim_time <= current_sim_time:
            # Время уже наступило или прошло
            await asyncio.sleep(0)  # Cooperative yield
            return
            
        # Вычисляем необходимую задержку в реальном времени
        sim_delta = target_sim_time - current_sim_time
        real_delay = sim_delta * 60.0 / self.speed_factor
        
        if real_delay > 0:
            logger.debug({
                "event": "clock_sleep",
                "target_sim_time": target_sim_time,
                "current_sim_time": current_sim_time,
                "real_delay_seconds": real_delay
            })
            await asyncio.sleep(real_delay)


def create_clock(realtime: bool = None) -> Clock:
    """
    Factory function для создания нужного типа часов.
    
    Args:
        realtime: Если True - создать RealTimeClock, если False - SimClock
                 Если None - определить по ENV ENABLE_REALTIME
                 
    Returns:
        Clock: Соответствующая реализация часов
    """
    if realtime is None:
        realtime = os.getenv("ENABLE_REALTIME", "false").lower() == "true"
        
    if realtime:
        return RealTimeClock()
    else:
        return SimClock() 