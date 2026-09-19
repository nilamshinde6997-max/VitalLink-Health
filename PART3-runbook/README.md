# Part 3 — Runbook: Primary Disk Filling Due to Stale Replication Slot / Recovery Conflict

## Purpose

This runbook describes how to detect, investigate, and respond to a PostgreSQL reliability incident involving:

* An inactive replication slot.
* Excessive retained WAL.
* Increasing primary database disk usage.
* Recovery conflicts on the read replica.
* Increasing replica lag.
* Failed materialized-view refreshes.

The objective is to restore reliable data freshness while protecting the primary database from running out of disk space.

This runbook is intended for the on-call engineer or database owner.

---

## Scope

This runbook applies when one or more of the following conditions occur:

* Primary database disk usage is increasing rapidly.
* A replication slot is inactive.
* A replication slot is retaining an unusually large amount of WAL.
* Replica lag is increasing.
* Replica recovery is paused because of a recovery conflict.
* Materialized-view refresh jobs are failing.
* Clinician or BI users report stale data.

---

# 1. Detection

The following signals should be monitored continuously.

### Primary Disk Usage

Recommended thresholds:

```text
WARNING  > 75%
CRITICAL > 85%
EMERGENCY > 90%
```

The exact thresholds should be tuned using observed WAL growth and the amount of time required for the team to respond.

### Replica Lag

Recommended thresholds:

```text
WARNING  > 60 seconds
CRITICAL > 5 minutes
PAGE     > 15 minutes
```

Because the clinician dashboard reads from the replica, prolonged lag should be treated as a user-impacting reliability problem.

### Replication Slots

Monitor every replication slot for:

* Active/inactive state.
* Slot type.
* Retained WAL.
* Slot owner or associated application.

Example condition requiring investigation:

```text
inactive slot AND retained WAL > 1 GB
```

### Materialized-View Refresh

Every scheduled refresh should produce a success or failure status.

Alert immediately when a refresh fails.

Also monitor the time since the last successful refresh.

---

# 2. Initial Incident Response

When an alert fires or a user reports stale data:

1. Acknowledge the alert.
2. Assign an incident owner.
3. Determine whether clinicians are currently seeing stale patient data.
4. Check primary database disk usage.
5. Check replication lag.
6. Check replication slots.
7. Check replica recovery status.
8. Check materialized-view refresh failures.
9. Communicate the current impact to relevant stakeholders.

Do not immediately delete replication slots or restart database components without understanding the dependency.

---

# 3. Check Primary Disk Usage

Check current database storage utilization.

If disk usage is above 85%, treat the situation as high priority.

If disk usage is above 90%, prioritize preventing the primary from running out of storage.

Check:

* Current disk utilization.
* Disk growth rate.
* WAL directory usage.
* Database growth.
* Replication-slot WAL retention.

If supported by the platform, controlled storage expansion may be used to create additional recovery time.

---

# 4. Check Replication Slots

Inspect replication slots on the primary.

Example PostgreSQL query:

```sql
SELECT
    slot_name,
    slot_type,
    active,
    restart_lsn,
    confirmed_flush_lsn,
    pg_size_pretty(
        pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
    ) AS retained_wal
FROM pg_replication_slots;
```

Look for:

* `active = false`
* Large retained WAL
* Slots with unknown ownership
* Legacy slots that are no longer expected

### Important Safety Rule

**Do not automatically drop an inactive replication slot.**

First determine:

1. What system owns the slot?
2. Is the consumer permanently retired?
3. Is the slot required for recovery?
4. Is there another system depending on it?

Dropping a slot can permanently prevent a consumer from receiving the WAL it requires.

Any slot removal must be approved by the incident owner or database owner.

---

# 5. Check Replica Health

Check the replica for:

* Current replication lag.
* WAL replay position.
* Recovery status.
* Recovery conflicts.
* Long-running queries.
* CPU and I/O pressure.

The supplied incident contained:

```text
LOG: recovery is paused because of recovery conflict

LOG: replica lag: 31241 s (and climbing)
```

31,241 seconds is approximately 8.7 hours.

This should be treated as a severe data-freshness problem because the clinician dashboard reads from the replica.

---

# 6. Investigate Recovery Conflicts

A recovery conflict can occur when a query running on the replica needs row versions that PostgreSQL recovery needs to remove while replaying WAL.

Check for:

* Long-running queries.
* Large analytical queries.
* Materialized-view refreshes.
* BI queries.
* Repeated recovery-conflict messages.

If an approved non-critical query is blocking recovery, the incident owner may authorize terminating or cancelling it.

**Do not terminate clinical or safety-critical workloads without understanding their impact.**

---

# 7. Check Materialized-View Refreshes

Check the cron logs and job status.

The incident example showed:

```text
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_vitals_7d ...

ERROR: canceling statement due to conflict with recovery

refresh_vitals.sh exited with status 1
```

A failed refresh means the materialized view may remain stale.

Record:

* Last successful refresh.
* Failed refresh times.
* Error messages.
* Current age of the materialized view.

After the replica becomes healthy, rerun the refresh if safe and verify successful completion.

---

# 8. Immediate Remediation

Follow this order:

### Step 1 — Protect the Primary

Prevent the primary from reaching 100% disk utilization.

If supported, increase storage capacity.

### Step 2 — Identify the WAL Source

Determine which replication slot is retaining WAL.

Identify the owner before taking any destructive action.

### Step 3 — Resolve the Replica Conflict

Identify the workload causing recovery conflicts.

Reduce or stop non-essential conflicting queries if approved.

### Step 4 — Allow Replica Recovery

Monitor replay and replication lag until the replica begins catching up.

### Step 5 — Restore Materialized Views

Once the replica is healthy, rerun failed materialized-view refreshes.

### Step 6 — Validate User Data

Verify that:

* Recent patient readings are visible.
* Clinician dashboards are current.
* BI data is current.
* Materialized views have refreshed.
* Alert processing is healthy.

---

# 9. Human Approval Required

The following actions require explicit human approval:

* Dropping a replication slot.
* Terminating production database queries.
* Restarting PostgreSQL.
* Changing replication configuration.
* Switching application reads from replica to primary.
* Deleting database files or WAL manually.
* Making destructive infrastructure changes.

The detection script in this submission does **not** perform these actions.

It only detects and reports potentially dangerous conditions.

---

# 10. Recovery Verification

The incident should not be considered resolved merely because disk usage stops increasing.

Verify all of the following:

* Primary disk usage is stable.
* WAL retention is returning to normal.
* Replication slot health is understood.
* Replica lag is decreasing.
* Replica recovery is active.
* Recovery conflicts have stopped or are understood.
* Materialized-view refresh succeeds.
* Clinician dashboard displays recent readings.
* Metabase displays current data.
* Alert processing is functioning normally.

The incident owner should confirm recovery with both technical and user-facing checks.

---

# 11. Post-Incident Actions

After recovery:

1. Preserve relevant logs and metrics.
2. Document the complete incident timeline.
3. Identify the owner of every replication slot.
4. Add monitoring for inactive slots.
5. Add monitoring for retained WAL.
6. Add disk-growth alerts.
7. Add replica-lag paging.
8. Add materialized-view refresh monitoring.
9. Reduce alert noise and remove non-actionable alerts.
10. Review whether analytics should be moved away from the production read replica.
11. Review and update the relevant SLOs.

---

# 12. Detection Script

The accompanying script is:

```text
detect_replication_issue.py
```

It performs read-only checks for:

* Inactive replication slots.
* Excessive retained WAL.
* Replica lag.
* Materialized-view refresh failures.

Example usage:

```bash
python detect_replication_issue.py
```

The script reports detected problems but does not make production changes.

---

# Assumptions

This runbook assumes:

* PostgreSQL 15.
* One asynchronous read replica.
* Clinician and BI workloads use the replica.
* Materialized views are refreshed by cron.
* Database access is available to the on-call engineer.
* Production actions require appropriate authorization.
* No real PHI is included in the script or runbook.

---

# Future Improvements

With more time, this runbook could be integrated with the organization's monitoring platform.

Potential improvements include:

* Prometheus/Grafana metrics.
* Automated paging.
* Database-specific dashboards.
* Automated ticket creation.
* Runbook links directly from alerts.
* Safer automated remediation for low-risk conditions.
* A tested procedure for controlled fallback to the primary database.
