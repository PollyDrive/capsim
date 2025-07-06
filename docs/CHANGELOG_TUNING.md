# Performance Tuning Changelog

This file tracks all performance tuning changes and their results.

## Format
```
## YYYY-MM-DD HH:MM

* Lever: <parameter>=<value>
* Goal metric: <metric> from <old> → <new>
* Result: ✅ improved | ➖ no change | ⚠️ worse
```

## SLA Targets
- **CPU Temp** ≤ 85 °C (5 min avg)
- **IO-wait** < 25 % (5 min avg)
- **p95 write-latency** ≤ 200 ms
- **WAL rate** ≤ 1.5 × baseline peak

---

## Tuning History

### Initial Setup - {{ timestamp }}

* Lever: baseline_establishment
* Goal metric: establish_baseline
* Result: ✅ baseline recorded

Initial baseline metrics recorded in `baseline.yaml`.

---

<!-- New entries will be added below --> 