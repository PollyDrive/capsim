# ADR-0002: Person Schema Extension for v1.8 Action System

## Status
ACCEPTED - 2025-01-27

## Context
CAPSIM v1.8 requires tracking of agent actions and cooldowns to implement:
- Purchase action system with L1/L2/L3 levels
- Daily purchase limits per agent
- Cooldown management for Post and SelfDev actions
- Purchase history tracking by level

## Decision

### Database Schema Changes
Add four new fields to `capsim.persons` table:

```sql
-- Daily counters and limits
purchases_today SMALLINT DEFAULT 0 CHECK (purchases_today >= 0)

-- Action cooldown timestamps (simulation time in minutes as DOUBLE)
last_post_ts DOUBLE PRECISION NULL
last_selfdev_ts DOUBLE PRECISION NULL

-- Purchase history by level (JSONB for efficient querying)
last_purchase_ts JSONB DEFAULT '{}'::jsonb
```

### JSONB Structure for last_purchase_ts
```json
{
  "L1": 1678901234.567,  // timestamp of last L1 purchase
  "L2": 1678902345.678,  // timestamp of last L2 purchase  
  "L3": null             // L3 purchase never made
}
```

### Performance Optimizations
- GIN index on `last_purchase_ts` using `jsonb_path_ops`
- SmallInteger for `purchases_today` (max 5 per day per spec)
- Double precision for timestamps (simulation time precision)

### ORM Mapping
- SQLAlchemy models updated with proper types
- Domain models maintain type safety
- Repository layer handles conversion with fallbacks

## Consequences

### Positive
- **Backward Compatible**: All fields have defaults, existing code unaffected
- **Performance Optimized**: GIN index enables fast JSONB queries
- **Type Safe**: Strong typing in domain models
- **Constraint Protected**: Database enforces business rules

### Negative
- **Memory Overhead**: ~24 bytes per person for new fields
- **Migration Time**: Large person tables will require maintenance window
- **JSONB Complexity**: Requires understanding of PostgreSQL JSONB operations

### Risks Mitigated
- **Data Integrity**: Constraints prevent negative purchases
- **Query Performance**: Index handles purchase history lookups
- **Rollback Safety**: Downgrade migration fully removes changes

## Implementation Notes
- Migration: `0005_add_new_person_fields_v1_8.py`
- Models: `capsim.db.models.Person` and `capsim.domain.person.Person`
- Repository: Updated conversion methods with backward compatibility

## Related
- Links to v1.8 requirements specification
- Connects to future ADR for Action Factory Pattern 