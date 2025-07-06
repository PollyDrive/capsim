#!/usr/bin/env python3
"""
CAPSIM Production DB Simulation

• 300 глобальных агентов
• 6 часов симуляции (360 минут)
• 120x ускорение
• Полный запись событий, трендов и покупок в capsim.* таблицы
• Жёсткий лимит: в таблице persons не более 1000 записей
"""

import logging
import random
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import List, Tuple

import psycopg2
from psycopg2.extras import execute_batch
from capsim.common.db_config import SYNC_DSN, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Simulation parameters
NUM_AGENTS = 300
SIM_DURATION_MINUTES = 360  # 6 часов
SPEED_FACTOR = 120  # 120x ускорение
MAX_PERSONS = 1000  # Жёсткий лимит

TOPICS = ["Economic", "Health", "Spiritual", "Conspiracy", "Science", "Culture", "Sport"]

# Event types with weights for diversity (sum 1.0)
EVENT_WEIGHTS = [
    ("publish_post", 0.30),
    ("purchase", 0.25),
    ("self_dev", 0.20),
    ("agent_action", 0.10),
    ("trend_influence", 0.07),
    ("social_interaction", 0.05),
    ("trend_created", 0.03),
]

# Derived flat list for random.choices
EVENT_TYPES = [et for et, _ in EVENT_WEIGHTS]
EVENT_PROBS = [w for _, w in EVENT_WEIGHTS]

# Action subtype probabilities
action_subtypes = {
    "agent_action": ["move", "interact", "create", "consume"],
    "purchase": ["buy_food", "buy_clothes", "buy_gadget"],
    "self_dev": ["read_book", "exercise", "meditate"],
}

# Profession distribution (sum to NUM_AGENTS)
PROF_DIST: List[Tuple[str, int]] = [
    ("Teacher", 60), ("ShopClerk", 54), ("Developer", 36), ("Unemployed", 27),
    ("Businessman", 24), ("Artist", 24), ("Worker", 21), ("Blogger", 15),
    ("SpiritualMentor", 9), ("Philosopher", 6), ("Politician", 3), ("Doctor", 3)
]

DB_CONFIG = {
    "dsn": SYNC_DSN,
}

def get_conn():
    return psycopg2.connect(DB_CONFIG["dsn"])


def clear_tables(conn):
    """Очищает capsim.* таблицы для чистого запуска."""
    conn.autocommit = True  # avoid deadlock inside transaction
    with conn.cursor() as cur:
        # Terminate other connections to prevent deadlocks
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
              AND state <> 'idle'
        """)

        # Short lock timeout to fail fast
        cur.execute("SET lock_timeout = '3s';")

        cur.execute("SET session_replication_role = replica;")
        # Truncate in dependency order to minimise lock conflicts
        for tbl in ("capsim.events", "capsim.simulation_participants", "capsim.trends",
                    "capsim.persons", "capsim.simulation_runs"):
            cur.execute(f"TRUNCATE {tbl} CASCADE;")
        cur.execute("SET session_replication_role = DEFAULT;")
        cur.execute("RESET lock_timeout;")
    logger.info("🧹 Tables truncated (persons, participants, events, trends, simulation_runs)")


def persons_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM capsim.persons;")
        return cur.fetchone()[0]


def ensure_persons_limit(conn, new_agents: int):
    current = persons_count(conn)
    if current + new_agents > MAX_PERSONS:
        raise RuntimeError(f"❌ Persons limit exceeded: {current + new_agents} > {MAX_PERSONS}")


def create_simulation_run(conn, num_agents: int) -> str:
    run_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO capsim.simulation_runs(run_id, start_time, status, num_agents, duration_days, configuration)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                run_id, datetime.utcnow(), "running", num_agents,
                SIM_DURATION_MINUTES / 1440,
                json.dumps({"speed_factor": SPEED_FACTOR})
            )
        )
    conn.commit()
    logger.info(f"✅ Simulation run created: {run_id}")
    return run_id


def generate_agents(conn, simulation_id: str):
    ensure_persons_limit(conn, NUM_AGENTS)
    agents: List[Tuple] = []
    for profession, count in PROF_DIST:
        for _ in range(count):
            agent_id = str(uuid.uuid4())
            # Simple random attributes
            energy = round(random.uniform(3.0, 8.0), 2)
            social = round(random.uniform(0.5, 4.5), 2)
            time_budget = random.randint(3, 8)
            financial = round(random.uniform(0.2, 0.9), 2)
            trend_rec = round(random.uniform(0.3, 0.9), 2)
            agents.append((
                agent_id, profession, energy, social, time_budget,
                financial, trend_rec, json.dumps({}), datetime.utcnow(), datetime.utcnow()
            ))
    logger.info(f"👥 Generating {len(agents)} agents…")
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO capsim.persons(id, profession, energy_level, social_status, time_budget,
              financial_capability, trend_receptivity, interests, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, agents, page_size=100)
        # Insert into participants
        participant_rows = [
            (simulation_id, a[0], 0, 0.0, 0.0, json.dumps({})) for a in agents
        ]
        execute_batch(cur, """
            INSERT INTO capsim.simulation_participants(simulation_id, person_id, purchases_today,
              last_post_ts, last_selfdev_ts, last_purchase_ts)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, participant_rows, page_size=100)
    conn.commit()
    logger.info("✅ Agents and participants inserted")
    return [a[0] for a in agents]


def create_initial_trends(conn, simulation_id: str, agents: List[str]):
    rows = []
    for topic in TOPICS:
        rows.append((str(uuid.uuid4()), simulation_id, topic, random.choice(agents), datetime.utcnow(),
                     random.uniform(0.3, 0.8), 0, datetime.utcnow()))
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO capsim.trends(trend_id, simulation_id, topic, originator_id, timestamp_start,
              base_virality_score, total_interactions, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, rows)
    conn.commit()
    logger.info(f"📈 {len(rows)} initial trends created")


def batch_insert_events(cur, batch):
    execute_batch(cur, """
        INSERT INTO capsim.events(event_id, simulation_id, agent_id, event_type, priority,
          event_data, processed_at, timestamp)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, batch, page_size=500)


def run_simulation(conn, simulation_id: str, agents: List[str]):
    logger.info("🚀 Starting DB simulation loop…")
    current_time = 0.0
    start_real = time.time()
    events_processed = 0
    cur = conn.cursor()

    while current_time < SIM_DURATION_MINUTES:
        batch = []
        num_events = random.randint(300, 500)  # higher volume for KPI
        attr_delta = {}  # agent_id -> dict
        for _ in range(num_events):
            agent_id = random.choice(agents)
            event_type = random.choices(EVENT_TYPES, weights=EVENT_PROBS)[0]
            priority = 3 if event_type == "trend_created" else 2 if event_type in ("purchase", "publish_post", "agent_action") else 1
            data = {
                "action": random.choice(action_subtypes.get(event_type, [event_type])),
                "topic": random.choice(TOPICS),
                "sim_time": current_time
            }
            batch.append((str(uuid.uuid4()), simulation_id, agent_id, event_type, priority,
                           json.dumps(data), datetime.utcnow(), time.time()))
            # Update purchase counter
            if event_type == "purchase":
                cur.execute("""
                    UPDATE capsim.simulation_participants
                    SET purchases_today = purchases_today + 1,
                        last_purchase_ts = %s
                    WHERE simulation_id = %s AND person_id = %s
                """, (json.dumps({"ts": time.time()}), simulation_id, agent_id))

            # Collect attribute deltas
            if agent_id not in attr_delta:
                attr_delta[agent_id] = {"energy": 0.0, "social": 0.0, "time": 0}
            if event_type == "publish_post":
                attr_delta[agent_id]["energy"] -= 0.1
                attr_delta[agent_id]["social"] += 0.1
                attr_delta[agent_id]["time"] -= 1
                # update last_post_ts
                cur.execute("""
                    UPDATE capsim.simulation_participants
                    SET last_post_ts = %s
                    WHERE simulation_id = %s AND person_id = %s
                """, (time.time(), simulation_id, agent_id))
            elif event_type == "self_dev":
                attr_delta[agent_id]["energy"] -= 0.15
                attr_delta[agent_id]["social"] += 0.05
                attr_delta[agent_id]["time"] -= 1
                cur.execute("""
                    UPDATE capsim.simulation_participants
                    SET last_selfdev_ts = %s
                    WHERE simulation_id = %s AND person_id = %s
                """, (time.time(), simulation_id, agent_id))
            elif event_type == "purchase":
                attr_delta[agent_id]["energy"] -= 0.05
                attr_delta[agent_id]["social"] += 0.05
                attr_delta[agent_id]["time"] -= 1

        # insert batch of events
        batch_insert_events(cur, batch)
        events_processed += len(batch)

        # apply attribute updates in bulk
        attr_updates = []
        for aid, delta in attr_delta.items():
            attr_updates.append((delta["energy"], delta["social"], delta["time"], datetime.utcnow(), aid))
        if attr_updates:
            execute_batch(cur, """
                UPDATE capsim.persons
                SET energy_level = GREATEST(0, LEAST(10, energy_level + %s)),
                    social_status = GREATEST(0, LEAST(5, social_status + %s)),
                    time_budget   = GREATEST(0, LEAST(10, time_budget + %s)),
                    updated_at = %s
                WHERE id = %s
            """, attr_updates, page_size=200)

        # optional trend creation chance
        if random.random() < 0.05:
            cur.execute("""
                INSERT INTO capsim.trends(trend_id, simulation_id, topic, originator_id, timestamp_start,
                  base_virality_score, total_interactions, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (str(uuid.uuid4()), simulation_id, random.choice(TOPICS), random.choice(agents),
                    datetime.utcnow(), random.uniform(0.2, 0.6), 0, datetime.utcnow()))
        conn.commit()

        # hourly natural energy recovery
        if int(current_time) % 60 == 0:
            cur.execute("""
                UPDATE capsim.persons
                SET energy_level = LEAST(10, energy_level + 0.5)
            """)

        current_time += 5  # 5-minute steps
        # realtime throttle
        expected_real = (current_time * 60) / SPEED_FACTOR
        actual_real = time.time() - start_real
        if expected_real > actual_real:
            time.sleep(expected_real - actual_real)

    # finalize
    cur.execute("UPDATE capsim.simulation_runs SET status='completed', end_time=%s WHERE run_id=%s",
                (datetime.utcnow(), simulation_id))
    conn.commit()
    logger.info(f"✅ Simulation completed with {events_processed} events")


def main():
    conn = get_conn()
    try:
        clear_tables(conn)
        sim_id = create_simulation_run(conn, NUM_AGENTS)
        agents = generate_agents(conn, sim_id)
        create_initial_trends(conn, sim_id, agents)
        run_simulation(conn, sim_id, agents)
    finally:
        conn.close()


if __name__ == "__main__":
    main() 