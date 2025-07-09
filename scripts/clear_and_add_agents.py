#!/usr/bin/env python3
"""Reset capsim.persons and related rows, then add 100 new agents.

Usage:
    DATABASE_URL=<async url> python scripts/clear_and_add_agents.py

This script performs:
1. TRUNCATE capsim.persons CASCADE (removes references in participants, trends, etc.)
2. Inserts 100 freshly generated agents with attributes and interests within valid ranges.

Requires that the bootstrap has seeded agents_profession and agent_interests tables.
"""

from __future__ import annotations

import os
import uuid
import json
import random
from datetime import datetime

from faker import Faker
from sqlalchemy import create_engine, text

ASYNC_DSN = os.getenv("DATABASE_URL") or "postgresql+asyncpg://capsim_rw:capsim321@localhost:5432/capsim_db"
SYNC_DSN = ASYNC_DSN.replace("+asyncpg", "")

fake = Faker("ru_RU")

engine = create_engine(SYNC_DSN)
with engine.connect() as conn:
    print("🗑️  Truncating capsim.persons (cascade)…")
    conn.execute(text("TRUNCATE TABLE capsim.persons CASCADE"))
    conn.commit()

    # Load attribute and interest ranges
    ranges = {
        row["profession"]: {
            "financial_capability": (row["financial_capability_min"], row["financial_capability_max"]),
            "trend_receptivity": (row["trend_receptivity_min"], row["trend_receptivity_max"]),
            "social_status": (row["social_status_min"], row["social_status_max"]),
            "energy_level": (row["energy_level_min"], row["energy_level_max"]),
            "time_budget": (row["time_budget_min"], row["time_budget_max"]),
        }
        for row in conn.execute(text("SELECT * FROM capsim.agents_profession")).mappings()
    }
    inter_ranges: dict[str, dict[str, tuple[float, float]]] = {}
    for row in conn.execute(
        text("SELECT profession, interest_name, min_value, max_value FROM capsim.agent_interests")
    ).mappings():
        inter_ranges.setdefault(row["profession"], {})[row["interest_name"]] = (
            row["min_value"],
            row["max_value"],
        )

    if not ranges or not inter_ranges:
        raise RuntimeError("Required reference tables missing – run bootstrap first.")

    agents = []
    for _ in range(100):
        profession = random.choice(list(ranges.keys()))
        attr = ranges[profession]
        gender = random.choice(["male", "female"])
        first_name = fake.first_name_male() if gender == "male" else fake.first_name_female()
        last_name = fake.last_name_male() if gender == "male" else fake.last_name_female()

        financial_capability = round(random.uniform(*attr["financial_capability"]), 3)
        trend_receptivity = round(random.uniform(*attr["trend_receptivity"]), 3)
        social_status = round(random.uniform(*attr["social_status"]), 3)
        energy_level = round(random.uniform(*attr["energy_level"]), 3)
        tb_min, tb_max = attr["time_budget"]
        time_budget = float(random.randrange(int(tb_min * 2), int(tb_max * 2) + 1) / 2)

        year = datetime.utcnow().year
        birth_date = datetime(random.randint(year - 65, year - 18), random.randint(1, 12), random.randint(1, 28)).date()

        interests = {
            name: round(random.uniform(lo, hi), 3)
            for name, (lo, hi) in inter_ranges.get(profession, {}).items()
        }

        agents.append(
            {
                "id": str(uuid.uuid4()),
                "profession": profession,
                "first_name": first_name,
                "last_name": last_name,
                "gender": gender,
                "date_of_birth": birth_date,
                "financial_capability": financial_capability,
                "trend_receptivity": trend_receptivity,
                "social_status": social_status,
                "energy_level": energy_level,
                "time_budget": time_budget,
                "exposure_history": json.dumps({}),
                "interests": json.dumps(interests),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    conn.execute(
        text(
            """
            INSERT INTO capsim.persons (
                id, profession, first_name, last_name, gender, date_of_birth,
                financial_capability, trend_receptivity, social_status, energy_level,
                time_budget, exposure_history, interests, created_at, updated_at
            ) VALUES (
                :id, :profession, :first_name, :last_name, :gender, :date_of_birth,
                :financial_capability, :trend_receptivity, :social_status, :energy_level,
                :time_budget, :exposure_history, :interests, :created_at, :updated_at
            )
            """
        ),
        agents,
    )
    conn.commit()
    print(f"✅ Inserted {len(agents)} agents.") 