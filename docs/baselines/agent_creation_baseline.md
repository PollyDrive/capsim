# Agent Creation Baseline (v1.8)

> Status: **Accepted** — applies to all new agents generated after 2025-07-09.
>
> Author: Tech-Lead / Planner

This document captures the _canonical_ settings the codebase now uses to generate **global agents** (records in `capsim.persons`).  These values are seeded automatically by:

* `scripts/bootstrap.py` (initial system setup)
* `scripts/clear_and_add_agents.py` / `add_interestful_agents.py` (utility scripts)

## 1. Attribute Ranges by Profession  
(Source – `capsim.agents_profession` static table)

| Profession | financial_capability | trend_receptivity | social_status | energy_level | time_budget |
|-----------|---------------------|--------------------|---------------|--------------|-------------|
| ShopClerk | 2 – 4 | 1 – 3 | 1 – 3 | 2 – 5 | 3 – 5 |
| Worker | 2 – 4 | 1 – 3 | 1 – 2 | 2 – 5 | 3 – 5 |
| Developer | 3 – 5 | 3 – 5 | 2 – 4 | 2 – 5 | 2 – 4 |
| Politician | 3 – 5 | 3 – 5 | 4 – 5 | 2 – 5 | 2 – 4 |
| Blogger | 2 – 4 | 4 – 5 | 3 – 5 | 2 – 5 | 3 – 5 |
| Businessman | 4 – 5 | 2 – 4 | 4 – 5 | 2 – 5 | 2 – 4 |
| SpiritualMentor | 1 – 3 | 2 – 5 | 2 – 4 | 3 – 5 | 2 – 4 |
| Philosopher | 1 – 3 | 1 – 3 | 1 – 3 | 2 – 5 | 2 – 4 |
| Unemployed | 1 – 2 | 3 – 5 | 1 – 2 | 3 – 5 | 3 – 5 |
| Teacher | 1 – 3 | 1 – 3 | 2 – 4 | 2 – 5 | 2 – 4 |
| Artist | 1 – 3 | 2 – 4 | 2 – 4 | 4 – 5 | 3 – 5 |
| Doctor | 2 – 4 | 1 – 3 | 3 – 5 | 2 – 5 | 1 – 2 |

Ranges are **inclusive**.  Random values are chosen uniformly and rounded to 3 decimals (except `time_budget`, rounded to the nearest 0.5).  Any future change to these numbers **must** be reflected here and in the Alembic seed.

## 2. Interest Ranges by Profession  
(Source – `capsim.agent_interests` static table)

For each profession we define `[min, max]` for the six interest categories:

| Profession | Economics | Wellbeing | Spirituality | Knowledge | Creativity | Society |
|-----------|-----------|-----------|--------------|-----------|------------|---------|
| ShopClerk | 0.30–0.70 | 0.40–0.80 | – | 0.60–0.90 | – | – |
| Developer | 0.40–0.80 | – | – | 0.60–0.90 | 0.30–0.70 | – |
| … | … | … | … | … | … | … |

(The full table is auto-generated from the seed JSON; see `alembic/versions/8a2c1e5d9abc_create_agents_profession_table.py` and `scripts/bootstrap.py` for reference.)

During agent creation each interest value is:
```
value = round(random.uniform(min, max), 3)
```
Only interests defined for the profession are present in the resulting `interests` JSON.

## 3. Validation Rules

* `0.0 ≤ financial_capability, trend_receptivity, social_status, energy_level ≤ 5.0`
* `1.0 ≤ time_budget ≤ 5.0` (steps of `0.5`)
* Assertions in creation scripts ensure ranges; tests must break if any goes out of bounds.

## 4. Change Control

This baseline is treated as **contract** between data generation and simulation logic.  Any modification must:

1. Update this document.
2. Provide a companion Alembic migration adjusting seeds.
3. Pass integrity tests (`tests/unit/test_person.py::test_attribute_ranges`).

---

_Last updated: 2025-07-09_ 