# CAPSIM Database Schema Requirements

## Senior Database Developer Documentation

### 📋 Person Table Requirements

Таблица `persons` должна содержать **ОБЯЗАТЕЛЬНЫЕ** поля для каждого агента:

#### ✅ Personal Identity Fields (CRITICAL)
```sql
first_name VARCHAR(100) NOT NULL    -- Русские имена (Александр, София, etc.)
last_name VARCHAR(100) NOT NULL     -- Русские фамилии с правильными окончаниями по полу
gender VARCHAR(10) NOT NULL         -- 'male' или 'female' 
date_of_birth DATE NOT NULL         -- Для расчета возраста агентов
```

#### ✅ Agent Attributes (Current)
```sql
profession VARCHAR(50) NOT NULL
financial_capability FLOAT         -- 0.0-5.0, округлено до 3 знаков
trend_receptivity FLOAT           -- 0.0-5.0, округлено до 3 знаков  
social_status FLOAT              -- 0.0-4.5, округлено до 3 знаков
energy_level FLOAT               -- 0.0-5.0, округлено до 3 знаков
time_budget FLOAT                -- 0.0-5.0, согласно tech specification
exposure_history JSON            -- История просмотра трендов
interests JSON                   -- Значения интересов агента
```

### 📊 Agent Interests Coverage Requirements

Таблица `agent_interests` должна содержать **ВСЕ 12 профессий** с **полным набором из 6 интересов**:

#### ✅ Agent Interests Matrix (72 records required)
```
Professions (12):
- Artist, Businessman, Developer, Doctor, SpiritualMentor, Teacher
- ShopClerk, Worker, Politician, Blogger, Unemployed, Philosopher

Agent Interests (6 categories):
- Economics, Wellbeing, Spirituality, Knowledge, Creativity, Society
```

#### ✅ Trend Topics Coverage (separate from agent interests)

Таблица `affinity_map` содержит **топики трендов** (отличаются от интересов агентов):

```
Trend Topics (7 categories):
- Economic, Health, Spiritual, Conspiracy, Science, Culture, Sport

Total affinity_map records: 12 professions × 7 topics = 84 records
```

#### ✅ Current Status: ✅ COMPLETE
- **Agent interests**: 72/72 records ✅ (12 × 6)
- **Trend topics**: 84/84 records ✅ (12 × 7)
- **All professions covered**: 12/12 ✅  
- **Clear separation**: Agent interests ≠ Trend topics ✅

### 🔨 Implementation Standards

#### Name Generation Rules
```python
# ОБЯЗАТЕЛЬНО: Русские имена с правильным соответствием пола
male_names = ['Александр', 'Дмитрий', 'Максим', 'Сергей', ...]
female_names = ['София', 'Мария', 'Анна', 'Виктория', ...]

male_surnames = ['Петров', 'Иванов', 'Сидоров', ...]      # мужские окончания
female_surnames = ['Петрова', 'Иванова', 'Сидорова', ...]  # женские окончания
```

#### Attribute Precision
```python
# Все числовые атрибуты округляются до 3 знаков после запятой
financial_capability = round(value, 3)
trend_receptivity = round(value, 3)
social_status = round(value, 3)
energy_level = round(value, 3)
```

#### Age Distribution
```python
# Даты рождения должны давать реалистичное распределение возрастов
# Диапазон: 18-65 лет
min_birth_date = current_date - 65 years
max_birth_date = current_date - 18 years
```

### 🚀 Migration History

#### Migration 0002: Person Demographics + Complete Agent Interests
- ✅ Added `first_name`, `last_name`, `gender`, `date_of_birth` to persons
- ✅ Completed agent_interests for all 12 professions (72 total records)
- ✅ Updated 1000 existing agents with Russian names
- ✅ Applied proper gender matching for surnames

#### Migration 0003: Fix Interests vs Trend Topics Separation
- ✅ Separated agent interests from trend topics according to TZ
- ✅ Agent interests: Economics, Wellbeing, Spirituality, Knowledge, Creativity, Society (6 × 12 = 72)
- ✅ Trend topics: Economic, Health, Spiritual, Conspiracy, Science, Culture, Sport (7 × 12 = 84)
- ✅ Updated affinity_map with correct trend topics from config/trend_affinity.json

#### Migration 0004: Fix Birth Years and Time Budget Type
- ✅ Changed date_of_birth from DateTime to Date (only date, no time)
- ✅ Updated age range from 18-80 to 18-65 years (birth years 1960-2007)
- ✅ Changed time_budget from INTEGER to FLOAT (0.0-5.0 scale)
- ✅ Unified time_budget specification across all documentation

### 🔍 Verification Queries

```sql
-- Check person demographics coverage
SELECT 
  COUNT(*) as total_agents,
  COUNT(first_name) as with_names,
  COUNT(DISTINCT gender) as gender_variants,
  MIN(date_of_birth) as oldest_agent,
  MAX(date_of_birth) as youngest_agent
FROM capsim.persons;

-- Verify complete agent_interests coverage  
SELECT 
  profession,
  COUNT(*) as interest_count,
  CASE WHEN COUNT(*) = 6 THEN '✅' ELSE '❌' END as status
FROM capsim.agent_interests 
GROUP BY profession 
ORDER BY profession;

-- Check agent interests vs trend topics separation
SELECT 'Agent Interests:' as type, COUNT(*) as count FROM capsim.agent_interests
UNION ALL
SELECT 'Trend Topics:' as type, COUNT(*) as count FROM capsim.affinity_map;
```

### ❗ Critical Requirements Summary

1. **Персональные данные**: Все агенты должны иметь русские имена, фамилии, пол и дату рождения
2. **Интересы агентов**: Все 12 профессий должны иметь по 6 интересов (72 записи total)
3. **Топики трендов**: Все 12 профессий должны иметь affinity к 7 топикам (84 записи total)
4. **Разделение сущностей**: Agent interests ≠ Trend topics (согласно ТЗ)
5. **Соответствие пола**: Фамилии должны правильно оканчиваться в зависимости от пола
6. **Точность атрибутов**: Все float значения округлены до 3 знаков после запятой
7. **Миграции**: Версионность через alembic для отслеживания изменений схемы

---
**Senior Database Developer**: @senior-db  
**Last Updated**: 2025-06-24  
**Schema Version**: 0004 