#!/usr/bin/env python3
"""Add 100 global agents with fully populated attribute and interest values.

Run:
    DATABASE_URL=<your async URL> python scripts/add_interestful_agents.py

The script relies on existing tables:
- capsim.agents_profession        (attribute ranges)
- capsim.agent_interests          (interest ranges per profession)
- capsim.persons                  (target table)
"""
from __future__ import annotations

import os
import uuid
import json
import random
from datetime import datetime

from faker import Faker
from sqlalchemy import create_engine, text

# Prefer DATABASE_URL environment variable, otherwise fallback to localhost dev DSN
ASYNC_DSN = os.getenv("DATABASE_URL") or "postgresql+asyncpg://capsim_rw:capsim321@localhost:5432/capsim_db"
SYNC_DSN = ASYNC_DSN.replace("+asyncpg", "")  # sqlalchemy sync driver

fake = Faker("ru_RU")

# ---------------------------------------------------------------------------
# Load attribute and interest ranges from reference tables
# ---------------------------------------------------------------------------

e = create_engine(SYNC_DSN)
with e.connect() as conn:
    # Load attribute ranges per profession
    ranges_rows = conn.execute(text("SELECT * FROM capsim.agents_profession")).mappings().all()
    ranges_map = {
        row["profession"]: {
            "financial_capability": (row["financial_capability_min"], row["financial_capability_max"]),
            "trend_receptivity": (row["trend_receptivity_min"], row["trend_receptivity_max"]),
            "social_status": (row["social_status_min"], row["social_status_max"]),
            "energy_level": (row["energy_level_min"], row["energy_level_max"]),
            "time_budget": (row["time_budget_min"], row["time_budget_max"]),
        }
        for row in ranges_rows
    }

    # Load interest ranges per profession
    interest_rows = conn.execute(
        text(
            """
            SELECT profession, interest_name, min_value, max_value
            FROM capsim.agent_interests
            """
        )
    ).mappings().all()
    interest_map: dict[str, dict[str, tuple[float, float]]] = {}
    for row in interest_rows:
        interest_map.setdefault(row["profession"], {})[row["interest_name"]] = (
            row["min_value"],
            row["max_value"],
        )

    if not ranges_map:
        raise RuntimeError("agents_profession table is empty – bootstrap not run?")
    if not interest_map:
        raise RuntimeError("agent_interests table is empty – bootstrap not run?")

    # -----------------------------------------------------------------------
    # Generate 100 agents
    # -----------------------------------------------------------------------
    to_insert = []
    for _ in range(100):
        profession = random.choice(list(ranges_map.keys()))
        attr_ranges = ranges_map[profession]

        gender = random.choice(["male", "female"])
        first_name = fake.first_name_male() if gender == "male" else fake.first_name_female()
        last_name = fake.last_name_male() if gender == "male" else fake.last_name_female()

        financial_capability = round(random.uniform(*attr_ranges["financial_capability"]), 3)
        trend_receptivity = round(random.uniform(*attr_ranges["trend_receptivity"]), 3)
        social_status = round(random.uniform(*attr_ranges["social_status"]), 3)
        energy_level = round(random.uniform(*attr_ranges["energy_level"]), 3)
        # time_budget steps of 0.5 within range
        tb_min, tb_max = attr_ranges["time_budget"]
        time_budget = float(random.randrange(int(tb_min * 2), int(tb_max * 2) + 1) / 2)

        # birthday between 18 and 65 years old
        current_year = datetime.utcnow().year
        birth_year = random.randint(current_year - 65, current_year - 18)
        birth_date = datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date()

        # Generate interests JSON based on profession-specific ranges
        prof_int_ranges = interest_map.get(profession, {})
        interests_dict = {
            name: round(random.uniform(min_v, max_v), 3)
            for name, (min_v, max_v) in prof_int_ranges.items()
        }

        to_insert.append(
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
                "interests": json.dumps(interests_dict),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    # -----------------------------------------------------------------------
    # Bulk insert
    # -----------------------------------------------------------------------
    if to_insert:
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
            to_insert,
        )
        conn.commit()

    print(f"✅ Inserted {len(to_insert)} agents with interests into capsim.persons") 