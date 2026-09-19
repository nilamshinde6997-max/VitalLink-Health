# Part 4 — AI-Augmented Operations

## Overview

AI-assisted operations could help VitalLink reduce the time required to investigate reliability incidents.

The AI system should be used as an investigation and decision-support tool rather than as an autonomous production operator.

Because VitalLink handles protected health information (PHI), the design must prioritize data minimization, access control, auditability, and human approval.

---

## 1. Where AI Should Be Introduced First

The first use case should be **incident investigation and alert correlation**.

For example, during the replication incident, an AI-assisted operations tool could correlate:

* Primary database disk usage.
* PostgreSQL replication-slot information.
* Retained WAL.
* Replica lag.
* Recovery-conflict logs.
* Materialized-view refresh failures.
* Application and worker logs.
* Monitoring alerts.

Instead of requiring an engineer to inspect each signal separately, the tool could produce an investigation summary such as:

```text
Primary disk usage is increasing.

An inactive logical replication slot is retaining significant WAL.

The read replica is experiencing recovery conflicts.

Replica lag is increasing.

Materialized-view refresh jobs are failing because of recovery conflicts.

These conditions are consistent with the stale-data incident.
```

The AI should show the evidence supporting each observation so that the engineer can verify the reasoning.

---

## 2. Potential Open-Source Tooling

A self-hosted observability platform such as SigNoz could provide a central telemetry layer using OpenTelemetry.

An AI investigation assistant such as HolmesGPT could then be used to investigate alerts and operational signals.

A possible architecture is:

```text
Applications
     |
     v
OpenTelemetry
     |
     v
Self-hosted observability platform
     |
     +--------------------+
     |                    |
     v                    v
Metrics / Logs / Traces   Alerts
     |                    |
     +---------+----------+
               |
               v
       AI investigation assistant
               |
               v
       Human incident responder
```

The AI component should not directly execute production changes.

---

## 3. Data Sources

The AI investigation system should have access to operational telemetry such as:

### Database Metrics

* Primary disk utilization.
* WAL generation rate.
* Replication-slot retention.
* Replica lag.
* Database connections.
* Query duration.
* Database errors.

### PostgreSQL Logs

Relevant events include:

* Recovery conflicts.
* Replication errors.
* Connection errors.
* Long-running queries.
* Materialized-view refresh failures.

### Application Telemetry

Useful information includes:

* API error rates.
* Request latency.
* Background worker failures.
* Alert-processing latency.
* Queue depth.

### Infrastructure Metrics

Examples include:

* CPU utilization.
* Memory utilization.
* Disk I/O.
* Network errors.
* Container or host health.

---

## 4. PHI and HIPAA Guardrails

AI should not receive unnecessary patient information.

The AI investigation workflow should follow data-minimization principles.

### Avoid Sending

The system should avoid exposing:

* Patient names.
* Phone numbers.
* Email addresses.
* Medical record numbers.
* Exact patient vital readings.
* Free-text clinical notes.
* Other unnecessary identifiers.

### Prefer Sending

The AI should receive operational information such as:

```text
replica_lag_seconds = 31241
primary_disk_percent = 93
inactive_slot = true
retained_wal_gb = 94
materialized_view_refresh_failures = 2
```

This provides enough information for infrastructure investigation without exposing patient information.

---

## 5. Data Protection Controls

A production implementation should include:

* Self-hosted deployment where appropriate.
* Encryption in transit.
* Encryption at rest.
* Strong authentication.
* Role-based access control.
* Least-privilege permissions.
* Audit logging.
* Secret management.
* Network isolation.
* Log redaction.
* PHI detection and removal before AI processing.
* Defined data-retention policies.

AI providers or external services should not receive PHI unless the organization has completed the necessary security, privacy, contractual, and compliance requirements.

---

## 6. Read-Only Access

The AI system should initially have read-only access.

For example, it may be allowed to retrieve:

* Monitoring metrics.
* Database health information.
* Logs.
* Deployment information.
* Recent alert history.
* Runbook documentation.

It should not initially be allowed to:

* Drop replication slots.
* Delete WAL.
* Terminate database sessions.
* Restart PostgreSQL.
* Change replication configuration.
* Modify production data.
* Change infrastructure settings.

This reduces the risk of an incorrect AI recommendation causing an outage or data loss.

---

## 7. Human-in-the-Loop Operations

AI recommendations should require human review before production changes.

For example:

```text
AI detects:
Inactive replication slot
+
94 GB retained WAL
+
93% primary disk usage

        ↓

AI recommends:
Investigate the legacy replication slot owner.

        ↓

Human verifies:
The slot is no longer required.

        ↓

Human approves:
Slot removal.

        ↓

Authorized operator performs the change.

        ↓

AI continues monitoring the system.
```

The AI should therefore act as an assistant rather than an autonomous database administrator.

---

## 8. Example Incident Investigation

During the supplied incident, an AI assistant could correlate the following events:

```text
08:00  Primary disk = 77%

14:00  Materialized-view refresh fails

20:00  Primary disk = 86%

02:00  Materialized-view refresh fails again

06:00  Primary disk = 93%

06:00  Replica lag = 31,241 seconds
```

It could then highlight the relationship between:

```text
Inactive replication slot
        ↓
94 GB retained WAL
        ↓
Primary disk growth
        ↓
Replica/recovery pressure
        ↓
Recovery conflict
        ↓
Replica lag
        ↓
Failed materialized-view refresh
        ↓
Stale dashboard and BI data
```

The engineer would still verify these relationships against the underlying metrics and logs.

---

## 9. Measuring Whether AI Helps

AI should not be adopted simply because it produces interesting summaries.

VitalLink should measure whether it improves operational outcomes.

Useful measurements include:

### Mean Time to Detect (MTTD)

Measure whether incidents are detected sooner.

### Mean Time to Resolve (MTTR)

Compare incident-resolution time before and after AI assistance.

### Time to Diagnosis

Measure how long it takes an engineer to identify the likely root cause.

### Alert Triage Time

Measure the amount of engineer time required to investigate alerts.

### False Recommendations

Track cases where the AI provides an incorrect diagnosis or unsafe recommendation.

### Human Acceptance Rate

Measure how often engineers consider AI-generated investigation summaries useful.

### Safety Metrics

Track:

* Unauthorized production actions.
* Incorrect automated actions.
* PHI exposure incidents.
* Security-policy violations.

A successful implementation should reduce investigation time without increasing operational or privacy risk.

---

## 10. Recommended Rollout

A gradual rollout is preferable.

### Phase 1 — Read-Only Investigation

AI can inspect telemetry and produce summaries.

No production actions are allowed.

### Phase 2 — Recommendation

AI can suggest specific runbook steps.

A human must approve every production action.

### Phase 3 — Limited Automation

Only very low-risk actions may be automated after testing and approval.

Examples might include:

* Creating an incident ticket.
* Adding context to an alert.
* Generating a diagnostic report.

High-risk database actions should continue to require human approval.

---

## Conclusion

AI can improve VitalLink's reliability operations by correlating large amounts of telemetry and reducing the time required to understand incidents.

The safest starting point is read-only incident investigation.

The AI should receive operational telemetry rather than unnecessary PHI, use least-privilege access, provide evidence for its conclusions, and keep a human in control of production changes.

The success of the system should be measured using operational outcomes such as MTTD, MTTR, diagnosis time, alert-triage time, recommendation accuracy, and security/privacy incidents.
