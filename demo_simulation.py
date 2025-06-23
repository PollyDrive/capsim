#!/usr/bin/env python3
"""
Демо симуляции CAPSIM без БД зависимостей - для тестирования основной логики.
"""

import asyncio
import heapq
import json
import math
import random
import os
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum


# === Мини-версии доменных моделей ===

class TrendTopic(Enum):
    ECONOMIC = "Economic"
    HEALTH = "Health"
    SPIRITUAL = "Spiritual"
    CONSPIRACY = "Conspiracy"
    SCIENCE = "Science"
    CULTURE = "Culture"
    SPORT = "Sport"


@dataclass
class Person:
    id: UUID = field(default_factory=uuid4)
    profession: str = ""
    financial_capability: float = 0.0
    trend_receptivity: float = 0.0
    social_status: float = 0.0
    energy_level: float = 5.0
    time_budget: int = 0
    interests: Dict[str, float] = field(default_factory=dict)
    simulation_id: Optional[UUID] = None
    exposure_history: Dict[str, datetime] = field(default_factory=dict)
    
    def decide_action(self, context) -> Optional[str]:
        if not self.can_perform_action("any"):
            return None
            
        threshold = float(os.getenv("DECIDE_SCORE_THRESHOLD", "0.25"))
        
        if not self.can_perform_action("PublishPostAction"):
            return None
            
        best_topic = self._select_best_topic()
        if not best_topic:
            return None
            
        interest_score = self.get_interest_in_topic(best_topic)
        affinity_score = self.get_affinity_for_topic(best_topic)
        
        score = (
            0.5 * interest_score / 5.0 +
            0.3 * self.social_status / 5.0 +
            0.2 * random.random()
        ) * affinity_score / 5.0
        
        return "PublishPostAction" if score >= threshold else None
        
    def _select_best_topic(self) -> Optional[str]:
        if not self.interests:
            return "ECONOMIC"
        return max(self.interests.keys(), key=lambda t: self.interests[t]).upper()
        
    def can_perform_action(self, action_type: str) -> bool:
        if action_type == "any":
            return self.energy_level > 0 and self.time_budget > 0
        if action_type == "PublishPostAction":
            return (self.energy_level >= 1.0 and 
                   self.time_budget >= 1 and
                   self.trend_receptivity > 0)
        return False
        
    def get_interest_in_topic(self, topic: str) -> float:
        topic_mapping = {
            "ECONOMIC": "Economics",
            "HEALTH": "Wellbeing", 
            "SPIRITUAL": "Religion",
            "CONSPIRACY": "Politics",
            "SCIENCE": "Education",
            "CULTURE": "Entertainment",
            "SPORT": "Entertainment"
        }
        interest_category = topic_mapping.get(topic, "Economics")
        return self.interests.get(interest_category, 2.5)
        
    def get_affinity_for_topic(self, topic: str) -> float:
        # Affinity map из ТЗ
        base_affinities = {
            "ShopClerk": {"ECONOMIC": 3, "HEALTH": 2, "SPIRITUAL": 2, "CONSPIRACY": 3, "SCIENCE": 1, "CULTURE": 2, "SPORT": 2},
            "Worker": {"ECONOMIC": 3, "HEALTH": 3, "SPIRITUAL": 2, "CONSPIRACY": 3, "SCIENCE": 1, "CULTURE": 2, "SPORT": 3},
            "Developer": {"ECONOMIC": 3, "HEALTH": 2, "SPIRITUAL": 1, "CONSPIRACY": 2, "SCIENCE": 5, "CULTURE": 3, "SPORT": 2},
            "Politician": {"ECONOMIC": 5, "HEALTH": 4, "SPIRITUAL": 2, "CONSPIRACY": 2, "SCIENCE": 3, "CULTURE": 3, "SPORT": 2},
            "Blogger": {"ECONOMIC": 4, "HEALTH": 4, "SPIRITUAL": 3, "CONSPIRACY": 4, "SCIENCE": 3, "CULTURE": 5, "SPORT": 4},
            "Businessman": {"ECONOMIC": 5, "HEALTH": 3, "SPIRITUAL": 2, "CONSPIRACY": 2, "SCIENCE": 3, "CULTURE": 3, "SPORT": 3},
            "Doctor": {"ECONOMIC": 3, "HEALTH": 5, "SPIRITUAL": 2, "CONSPIRACY": 1, "SCIENCE": 5, "CULTURE": 2, "SPORT": 3},
            "Teacher": {"ECONOMIC": 3, "HEALTH": 4, "SPIRITUAL": 3, "CONSPIRACY": 2, "SCIENCE": 4, "CULTURE": 4, "SPORT": 3},
            "Unemployed": {"ECONOMIC": 4, "HEALTH": 3, "SPIRITUAL": 3, "CONSPIRACY": 4, "SCIENCE": 2, "CULTURE": 3, "SPORT": 3},
            "Artist": {"ECONOMIC": 2, "HEALTH": 2, "SPIRITUAL": 4, "CONSPIRACY": 2, "SCIENCE": 2, "CULTURE": 5, "SPORT": 2},
            "SpiritualMentor": {"ECONOMIC": 2, "HEALTH": 3, "SPIRITUAL": 5, "CONSPIRACY": 3, "SCIENCE": 2, "CULTURE": 3, "SPORT": 2},
            "Philosopher": {"ECONOMIC": 3, "HEALTH": 3, "SPIRITUAL": 5, "CONSPIRACY": 3, "SCIENCE": 4, "CULTURE": 4, "SPORT": 1}
        }
        
        profession_affinities = base_affinities.get(self.profession, {})
        return profession_affinities.get(topic, 2.5)
        
    def update_state(self, changes: Dict[str, float]) -> None:
        for attribute, delta in changes.items():
            if hasattr(self, attribute):
                current_value = getattr(self, attribute)
                
                if attribute in ["energy_level", "financial_capability", 
                               "trend_receptivity", "social_status"]:
                    new_value = max(0.0, min(5.0, current_value + delta))
                elif attribute == "time_budget":
                    new_value = max(0, min(5, int(current_value + delta)))
                else:
                    new_value = current_value + delta
                    
                setattr(self, attribute, new_value)
    
    @classmethod
    def create_random_agent(cls, profession: str, simulation_id: UUID) -> "Person":
        profession_ranges = {
            "Banker": {"financial_capability": (3.0, 5.0), "social_status": (3.0, 4.5), 
                      "trend_receptivity": (1.0, 3.0), "time_budget": (2, 4)},
            "Developer": {"financial_capability": (2.5, 4.0), "social_status": (2.0, 3.5), 
                         "trend_receptivity": (2.0, 4.0), "time_budget": (3, 5)},
            "Teacher": {"financial_capability": (1.5, 3.0), "social_status": (2.5, 4.0), 
                       "trend_receptivity": (3.0, 4.5), "time_budget": (2, 4)},
            "Worker": {"financial_capability": (1.0, 2.5), "social_status": (1.5, 3.0), 
                      "trend_receptivity": (2.0, 3.5), "time_budget": (1, 3)},
            "ShopClerk": {"financial_capability": (1.5, 3.0), "social_status": (2.0, 3.5), 
                         "trend_receptivity": (2.5, 4.0), "time_budget": (2, 4)}
        }
        
        ranges = profession_ranges.get(profession, profession_ranges["Worker"])
        
        base_interests = {
            "Economics": random.uniform(1.0, 5.0),
            "Wellbeing": random.uniform(1.0, 5.0),
            "Religion": random.uniform(0.5, 3.0),
            "Politics": random.uniform(1.0, 4.0),
            "Education": random.uniform(1.5, 4.5),
            "Entertainment": random.uniform(2.0, 5.0)
        }
        
        return cls(
            profession=profession,
            simulation_id=simulation_id,
            financial_capability=random.uniform(*ranges["financial_capability"]),
            social_status=random.uniform(*ranges["social_status"]),
            trend_receptivity=random.uniform(*ranges["trend_receptivity"]),
            energy_level=5.0,
            time_budget=random.randint(*ranges["time_budget"]),
            interests=base_interests
        )


@dataclass
class Trend:
    trend_id: UUID = field(default_factory=uuid4)
    topic: str = ""
    originator_id: UUID = field(default_factory=uuid4)
    parent_trend_id: Optional[UUID] = None
    timestamp_start: datetime = field(default_factory=datetime.utcnow)
    base_virality_score: float = 0.0
    coverage_level: str = "Low"
    total_interactions: int = 0
    simulation_id: UUID = field(default_factory=uuid4)
    
    def calculate_current_virality(self) -> float:
        if self.total_interactions == 0:
            return self.base_virality_score
        logarithmic_bonus = 0.05 * math.log(self.total_interactions + 1)
        return min(5.0, self.base_virality_score + logarithmic_bonus)
        
    def add_interaction(self) -> None:
        self.total_interactions += 1
        
    def get_coverage_factor(self) -> float:
        coverage_map = {"Low": 0.3, "Middle": 0.6, "High": 1.0}
        return coverage_map.get(self.coverage_level, 0.3)
        
    @classmethod
    def create_from_action(cls, topic: str, originator_id: UUID, simulation_id: UUID,
                          base_virality: float, coverage_level: str = "Low", 
                          parent_id: Optional[UUID] = None) -> "Trend":
        return cls(
            topic=topic, originator_id=originator_id, simulation_id=simulation_id,
            base_virality_score=base_virality, coverage_level=coverage_level,
            parent_trend_id=parent_id
        )


# === События ===

class EventPriority:
    LAW = 1
    WEATHER = 2
    TREND = 3
    AGENT_ACTION = 4
    SYSTEM = 5


@dataclass
class BaseEvent:
    event_id: UUID
    priority: int
    timestamp: float
    
    def __init__(self, priority: int, timestamp: float):
        self.event_id = uuid4()
        self.priority = priority
        self.timestamp = timestamp
    
    def process(self, engine) -> None:
        pass


class PublishPostAction(BaseEvent):
    def __init__(self, agent_id: UUID, topic: str, timestamp: float):
        super().__init__(EventPriority.AGENT_ACTION, timestamp)
        self.agent_id = agent_id
        self.topic = topic
        
    def process(self, engine) -> None:
        agent = next((p for p in engine.agents if p.id == self.agent_id), None)
        if not agent or not agent.can_perform_action("PublishPostAction"):
            return
            
        # Создать тренд
        base_virality = min(5.0, agent.social_status + (agent.trend_receptivity * 0.2))
        coverage = "High" if agent.financial_capability >= 4.0 else "Middle" if agent.financial_capability >= 2.5 else "Low"
        
        new_trend = Trend.create_from_action(
            topic=self.topic, originator_id=self.agent_id,
            simulation_id=agent.simulation_id, base_virality=base_virality,
            coverage_level=coverage
        )
        
        engine.active_trends[str(new_trend.trend_id)] = new_trend
        
        # Обновить агента
        agent.update_state({
            "energy_level": -1.0,
            "time_budget": -1,
            "social_status": 0.1
        })
        
        print(f"📝 {agent.profession} опубликовал пост на тему {self.topic} (viralicy={base_virality:.2f})")


class EnergyRecoveryEvent(BaseEvent):
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)
        
    def process(self, engine) -> None:
        recovery_count = 0
        for agent in engine.agents:
            old_energy = agent.energy_level
            if agent.energy_level < 3.0:
                agent.energy_level = 5.0
            else:
                agent.energy_level = min(5.0, agent.energy_level + 2.0)
                
            if agent.energy_level != old_energy:
                recovery_count += 1
                
        next_recovery = EnergyRecoveryEvent(self.timestamp + 360.0)
        engine.add_event(next_recovery, EventPriority.SYSTEM, next_recovery.timestamp)
        print(f"⚡ Восстановление энергии: {recovery_count} агентов")


# === Движок симуляции ===

@dataclass
class SimulationContext:
    current_time: float
    active_trends: Dict[str, Trend]
    affinity_map: Dict[str, Dict[str, float]]


@dataclass
class PriorityEvent:
    priority: int
    timestamp: float
    event: BaseEvent
    
    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class DemoSimulationEngine:
    def __init__(self):
        self.agents: List[Person] = []
        self.current_time: float = 0.0
        self.event_queue: List[PriorityEvent] = []
        self.active_trends: Dict[str, Trend] = {}
        self.affinity_map: Dict[str, Dict[str, float]] = {}
        self.simulation_id: Optional[UUID] = None
        self._running = False
        
    async def initialize(self, num_agents: int = 10) -> None:
        self.simulation_id = uuid4()
        
        # Создать агентов согласно ТЗ распределению (масштабировано для num_agents)
        profession_distribution = [
            ("Teacher", max(1, int(num_agents * 0.20))),
            ("ShopClerk", max(1, int(num_agents * 0.18))),
            ("Developer", max(1, int(num_agents * 0.12))),
            ("Unemployed", max(1, int(num_agents * 0.09))),
            ("Businessman", max(1, int(num_agents * 0.08))),
            ("Artist", max(1, int(num_agents * 0.08))),
            ("Worker", max(1, int(num_agents * 0.07))),
            ("Blogger", max(1, int(num_agents * 0.05))),
            ("SpiritualMentor", max(1, int(num_agents * 0.03))),
            ("Philosopher", max(1, int(num_agents * 0.02))),
            ("Politician", max(1, int(num_agents * 0.01))),
            ("Doctor", max(1, int(num_agents * 0.01))),
        ]
        
        # Корректируем количество
        total_assigned = sum(count for _, count in profession_distribution)
        if total_assigned < num_agents:
            remaining = num_agents - total_assigned
            profession_distribution[0] = ("Teacher", profession_distribution[0][1] + remaining)
        
        for profession, count in profession_distribution[:sum(1 for _, c in profession_distribution if c > 0)]:
            for _ in range(min(count, num_agents - len(self.agents))):
                agent = Person.create_random_agent(profession, self.simulation_id)
                self.agents.append(agent)
            
        # Системные события
        energy_event = EnergyRecoveryEvent(360.0)
        self.add_event(energy_event, EventPriority.SYSTEM, 360.0)
        
        print(f"🚀 Симуляция инициализирована: {len(self.agents)} агентов")
        
    async def run_simulation(self, duration_days: float = 1) -> None:
        self._running = True
        end_time = duration_days * 1440.0
        events_processed = 0
        actions_scheduled = 0
        
        print(f"▶️  Запуск симуляции на {duration_days} дней ({end_time:.1f} минут)")
        
        # Планируем первые действия агентов
        await self._schedule_agent_actions()
        
        while self._running and self.current_time < end_time:
            # Обработать события
            if self.event_queue:
                priority_event = heapq.heappop(self.event_queue)
                self.current_time = priority_event.timestamp
                
                priority_event.event.process(self)
                events_processed += 1
                
                # Планировать новые действия агентов после каждого обработанного события
                if isinstance(priority_event.event, (PublishPostAction, EnergyRecoveryEvent)):
                    scheduled = await self._schedule_agent_actions()
                    actions_scheduled += scheduled
            else:
                # Если очередь пуста, продвигаем время и планируем действия
                self.current_time += 15.0
                scheduled = await self._schedule_agent_actions()
                actions_scheduled += scheduled
            
            # Небольшая пауза
            if events_processed % 50 == 0:
                await asyncio.sleep(0.001)
                
        print(f"✅ Симуляция завершена за {self.current_time:.1f} минут")
        print(f"📊 События обработано: {events_processed}")
        print(f"🎯 Действий запланировано: {actions_scheduled}")
        print(f"📈 Трендов создано: {len(self.active_trends)}")
        
    async def _schedule_agent_actions(self) -> int:
        context = SimulationContext(self.current_time, self.active_trends, self.affinity_map)
        scheduled_count = 0
        
        for agent in self.agents:
            if agent.energy_level <= 0 or agent.time_budget <= 0:
                continue
                
            action_type = agent.decide_action(context)
            if action_type == "PublishPostAction":
                topic = agent._select_best_topic()
                if topic:
                    delay = random.uniform(1.0, 30.0)
                    action_event = PublishPostAction(
                        agent_id=agent.id, topic=topic,
                        timestamp=self.current_time + delay
                    )
                    self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                    scheduled_count += 1
        
        return scheduled_count
        
    def add_event(self, event: BaseEvent, priority: int, timestamp: float) -> None:
        priority_event = PriorityEvent(priority, timestamp, event)
        heapq.heappush(self.event_queue, priority_event)
        
    def get_simulation_stats(self) -> Dict:
        active_agents = sum(1 for agent in self.agents if agent.energy_level > 0)
        return {
            "simulation_id": str(self.simulation_id),
            "current_time": self.current_time,
            "active_agents": active_agents,
            "total_agents": len(self.agents),
            "active_trends": len(self.active_trends),
            "queue_size": len(self.event_queue),
            "running": self._running
        }


# === MAIN ===

async def demo_simulation():
    print("🎮 CAPSIM Simulation Engine - Demo Version")
    print("=" * 50)
    
    engine = DemoSimulationEngine()
    await engine.initialize(num_agents=20)
    
    # Показать начальное состояние агентов
    print("\n👥 Агенты по профессиям:")
    professions = {}
    for agent in engine.agents:
        professions[agent.profession] = professions.get(agent.profession, 0) + 1
    for prof, count in professions.items():
        print(f"  {prof}: {count}")
    
    # Запустить мини-симуляцию
    await engine.run_simulation(duration_days=120/1440)  # 2 часа
    
    # Финальная статистика
    print("\n📊 Финальная статистика:")
    stats = engine.get_simulation_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n🎯 Топ трендов по виральности:")
    if engine.active_trends:
        sorted_trends = sorted(
            engine.active_trends.values(),
            key=lambda t: t.calculate_current_virality(),
            reverse=True
        )[:5]
        
        for i, trend in enumerate(sorted_trends, 1):
            print(f"  {i}. {trend.topic}: виральность {trend.calculate_current_virality():.2f}, "
                  f"взаимодействий {trend.total_interactions}")
    else:
        print("  Нет созданных трендов")


if __name__ == "__main__":
    asyncio.run(demo_simulation()) 