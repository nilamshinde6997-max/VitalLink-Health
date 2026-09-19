# Part 2 — Incident Postmortem

## Incident Summary

VitalLink experienced an approximately nine-hour period during which the clinician dashboard and BI reports served stale patient data.

The primary database was also experiencing steadily increasing disk usage. Investigation showed that an inactive logical replication slot was retaining approximately 94 GB of WAL. At the same time, the read replica was experiencing recovery conflicts and severe replication lag.

The materialized-view refresh jobs also failed because of recovery conflicts.

The incident was caused by a combination of uncontrolled WAL retention, replica recovery conflicts, increasing replica lag, and insufficient monitoring and response to the resulting reliability signals.

---

## 1. Incident Timeline

### 2025-07-20 08:00

Primary database disk usage was approximately 61%.

No critical user impact was reported at this point.

### 2025-07-20 20:00

Primary database disk usage increased to approximately 68%.

The upward trend indicates that database storage consumption was increasing steadily.

### 2025-07-21 08:00

Primary database disk usage reached approximately 77%.

The increasing storage usage should have triggered investigation into WAL growth, database growth, or replication-slot retention.

### 2025-07-21 Overnight

Replica lag alarms were firing but were ignored.

The replica log showed:

```text
LOG: recovery is paused because of recovery conflict

LOG: replica lag: 31241 s (and climbing)
```

31,241 seconds is approximately 8.7 hours of replication lag.

This meant the replica was significantly behind the primary.

### 2025-07-21 20:00

Primary disk usage reached approximately 86%.

The continued increase in disk utilization represented a growing risk of database write failure.

### 2025-07-22 02:00

The scheduled materialized-view refresh failed:

```text
ERROR: canceling statement due to conflict with recovery
DETAIL: User query might have needed to see row versions that must be removed.
```

The refresh script exited with status 1.

The failed refresh meant the materialized view was not updated.

### 2025-07-22 06:00

Primary disk usage reached approximately 93%.

Write latency alarms began.

At this point the database was approaching a critical storage condition.

### Morning of Incident

A care-team lead reported that a patient's dashboard had not updated since the previous afternoon.

Investigation showed that the clinician dashboard and BI reports had been serving stale data for approximately nine hours.

### 14:00

The second scheduled materialized-view refresh also failed with the same recovery-conflict error.

This confirmed that the refresh problem was recurring rather than a one-time failure.

---

## 2. Impact Statement

### Clinician Impact

Clinicians using the dashboard could see stale patient vital information because the dashboard reads from the asynchronous replica.

The replica was approximately 31,241 seconds behind the primary at one point, which is roughly 8.7 hours.

This means the dashboard could show information that was several hours old.

### BI and Analytics Impact

Metabase also reads from the replica, so BI reports and analytics were affected by the same replication lag.

Materialized-view refreshes were also failing, making aggregate trend information stale.

### Database Impact

The primary database disk usage increased from:

```text
61% → 68% → 77% → 86% → 93%
```

over the observed period.

The inactive logical replication slot was retaining approximately 94 GB of WAL.

The database therefore faced increasing disk pressure and eventually began showing write-latency alarms.

### Clinical Significance

The most important concern is not simply that the dashboard was technically available.

The dashboard could successfully return a response while displaying outdated information.

In a remote patient monitoring system, stale data can affect clinical decision-making because clinicians may not have visibility into the patient's most recent readings.

The incident therefore represents a data-freshness and clinical-workflow reliability problem rather than only a conventional availability outage.

---

## 3. Root Cause Analysis

### Artifact A — Replication Slots

The primary showed:

```text
slot_name             | slot_type | active | retained_wal
----------------------+-----------+--------+-------------
replica_1             | physical  | true   | 128 MB
pglogical_legacy_sub  | logical   | false  | 94 GB
```

The physical replica slot was active and retaining only 128 MB.

The important problem was the logical slot:

```text
pglogical_legacy_sub
active: false
retained_wal: 94 GB
```

An inactive logical replication slot can retain WAL because PostgreSQL must preserve WAL needed by the slot's consumer.

The 94 GB retained WAL therefore explains a significant portion of the primary's increasing disk usage.

The slot name also suggests that it may belong to a legacy integration, although the exact ownership cannot be proven from the artifact alone.

The appropriate response would be to identify the owner and purpose of the slot before removing it.

---

## 4. Connecting the Artifacts

The artifacts form a chain of related failures.

### Step 1 — WAL Was Retained

The inactive logical replication slot retained approximately 94 GB of WAL.

```text
Inactive logical slot
        ↓
WAL cannot be recycled
        ↓
WAL accumulates on primary
```

### Step 2 — Primary Disk Usage Increased

The primary disk increased steadily:

```text
61%
 ↓
68%
 ↓
77%
 ↓
86%
 ↓
93%
```

This is consistent with sustained storage pressure caused in part by retained WAL.

### Step 3 — Replica Recovery Was Delayed

The replica log reported:

```text
recovery is paused because of recovery conflict
```

This indicates that recovery/replay was being blocked by a conflict with a query or operation on the replica.

The replica therefore could not keep up with the primary.

### Step 4 — Replica Lag Became Severe

The replica reported:

```text
replica lag: 31241 s (and climbing)
```

31,241 seconds is approximately 8.7 hours.

Because clinicians and Metabase read from the replica, the replica's lag directly translated into stale data for those consumers.

### Step 5 — Materialized-View Refresh Failed

The materialized-view refresh reported:

```text
ERROR: canceling statement due to conflict with recovery
```

This indicates that the refresh query conflicted with PostgreSQL recovery on the replica.

The refresh therefore failed instead of updating the materialized view.

### Step 6 — Users Saw Stale Information

The combination of:

* Severe replica lag.
* Failed materialized-view refreshes.
* Lack of effective freshness alerting.
* Ignored replica-lag alarms.

resulted in clinicians and BI users receiving stale information for approximately nine hours.

---

## 5. Five Whys

### Why did clinicians see stale patient data?

Because the clinician dashboard reads from a replica that was several hours behind the primary.

### Why was the replica several hours behind?

Because recovery/replay was being blocked by recovery conflicts and replica lag continued to increase.

### Why were recovery conflicts allowed to continue?

Queries and materialized-view refresh activity on the replica were conflicting with recovery, while there was no effective automated response to the growing lag.

### Why was the database under increasing storage pressure?

An inactive logical replication slot was retaining approximately 94 GB of WAL on the primary.

### Why did the problem reach users?

The team had no formal freshness SLO, replica-lag alarms were noisy and ignored, materialized-view refresh failures were not treated as urgent reliability signals, and there was no automated guardrail for stale replication slots or excessive WAL retention.

---

## 6. Immediate Remediation

The response should prioritize protecting the primary database and restoring trustworthy data visibility.

### Step 1 — Declare and Assign the Incident

Assign an incident owner and communicate the impact to engineering and clinical stakeholders.

The team should explicitly state that dashboard data may be stale.

### Step 2 — Protect the Primary Database

Monitor primary disk usage continuously.

At 93% utilization, the team should treat additional disk growth as a high-priority risk.

Avoid unnecessary operations that increase database load or generate additional WAL.

If the platform supports controlled storage expansion, increase available storage before the disk reaches a critical level.

### Step 3 — Identify the Replication Slot Owner

Investigate:

```text
pglogical_legacy_sub
```

and determine whether it is still required.

Do not immediately drop the slot simply because it is inactive.

Dropping an active production dependency could cause data loss or break a replication consumer.

### Step 4 — Stop or Reduce the Source of Recovery Conflicts

Identify the queries causing recovery conflicts on the replica.

Cancel or stop non-essential long-running analytical activity if approved by the incident owner.

The goal is to allow replica recovery to make progress.

### Step 5 — Restore Replica Health

Monitor:

* Replica lag.
* WAL replay position.
* Recovery status.
* Recovery conflicts.
* Database CPU and I/O.

Do not declare the incident resolved until the replica has caught up sufficiently to meet the freshness requirement.

### Step 6 — Restore Materialized Views

After the replica is healthy, manually run the failed materialized-view refreshes if safe.

Verify that the refresh succeeds.

Record the successful refresh timestamp.

### Step 7 — Validate User-Facing Data

Verify that:

* Recent patient readings are visible.
* The clinician dashboard is current.
* Metabase data is current.
* Materialized views have been refreshed.
* Alert processing is operating normally.

Only then should the incident be considered resolved.

---

## 7. Prevention — Detection

The following alerts should have fired before the incident became user-visible.

### Primary Disk Usage

Warning:

```text
Disk > 75%
```

Critical:

```text
Disk > 85%
```

Emergency investigation:

```text
Disk > 90%
```

The exact thresholds should be tuned using observed WAL growth and available time to respond.

### Replication Lag

Warning:

```text
Replica lag > 60 seconds
```

Critical:

```text
Replica lag > 5 minutes
```

Page immediately for:

```text
Replica lag > 15 minutes
```

For this system, prolonged replica lag is especially important because clinicians depend on the replica.

### Inactive Replication Slot

Alert when a replication slot is inactive and retains a significant amount of WAL.

For example:

```text
inactive = true
AND retained_wal > 1 GB
```

The threshold should be tuned using normal WAL generation.

### WAL Growth

Monitor:

* WAL generation rate.
* WAL retained by each replication slot.
* Total retained WAL.
* Rate of WAL growth.

An increasing WAL-retention rate should generate an alert before disk capacity becomes critical.

### Materialized-View Refresh

Alert whenever a scheduled refresh exits unsuccessfully.

Also monitor:

```text
current_time - last_successful_refresh_time
```

This provides a direct measurement of dashboard freshness.

---

## 8. Prevention — Automation

Several automated safeguards should be added.

### Replication-Slot Guardrail

A scheduled check should identify inactive slots with excessive retained WAL.

The check should create a high-priority alert and identify the slot owner.

Automatic slot deletion should not be enabled by default because of the potential for destructive consequences.

### Replica Health Gate

The application should monitor replica health and freshness.

If the replica becomes too stale, the system should either:

* Temporarily route selected reads to the primary, or
* Clearly mark the affected data as stale and prevent misleading clinical workflows.

The exact fallback should be tested before production use.

### Materialized-View Refresh Monitoring

Every refresh should report:

* Start time.
* Completion time.
* Success/failure.
* Error message.
* Last successful refresh.

A failed refresh should immediately create an operational alert.

### Alert Quality Improvements

The existing alerting system is described as noisy, causing the team to ignore alarms.

Alerts should therefore be tied to user impact and actionable thresholds.

For example:

```text
Replica lag increasing
+
Clinician data freshness approaching SLO violation
```

should receive higher priority than a low-level informational event.

---

## 9. Lessons Learned

The incident demonstrates that infrastructure health and user-facing reliability are related but different.

The database and application may remain technically available while clinicians receive stale information.

The key lessons are:

1. Data freshness should be treated as a first-class reliability metric.
2. Replica lag should be connected to user impact.
3. Replication slots require ownership and lifecycle management.
4. WAL retention must be monitored independently from disk capacity.
5. Failed background jobs must generate actionable alerts.
6. Alert fatigue can turn useful signals into ignored signals.
7. Healthcare systems require more conservative reliability thresholds for safety-sensitive workflows.
8. Automated remediation should be carefully controlled when it can affect database integrity.

## Conclusion

The incident was not caused by a single isolated failure.

An inactive logical replication slot retained a large amount of WAL, primary disk usage increased, replica recovery was affected by conflicts, replica lag grew to approximately 8.7 hours, materialized-view refreshes failed, and existing alarms were not acted upon.

The resulting stale data affected clinician dashboards and BI reports.

The most important long-term improvements are to establish explicit freshness SLOs, monitor replication and WAL retention, make background-job failures actionable, reduce alert noise, and automate detection while keeping potentially destructive database actions behind human approval.
