# Reliability Engineering Tradeoffs

## Overview

The VitalLink reliability design involves several tradeoffs between reliability, cost, performance, operational complexity, and safety.

The following decisions were made based on the architecture and incident scenario provided in the assignment.

---

## 1. Read Replica Performance vs. Data Freshness

Using a PostgreSQL read replica reduces query load on the primary database and provides a separate location for clinician dashboards and analytics.

However, asynchronous replication means the replica can become stale.

During the incident, replica lag reached approximately 31,241 seconds, causing users to see stale information.

The tradeoff is:

```text
More reads on replica
        ↓
Lower primary database load
        BUT
Potentially stale data
```

For safety-sensitive workflows, freshness should be monitored closely and selected reads may need a controlled fallback strategy.

---

## 2. Reliability vs. Engineering Cost

Higher SLO targets require additional monitoring, redundancy, testing, capacity, and operational effort.

For example, achieving very high availability and low alert latency may require:

* Additional infrastructure.
* More detailed monitoring.
* More on-call coverage.
* More automated testing.
* More operational processes.

VitalLink should prioritize the strictest reliability requirements for patient-safety-related workflows rather than applying the same target to every system component.

---

## 3. Alert Sensitivity vs. Alert Fatigue

Aggressive alerts can detect problems earlier.

However, too many alerts can cause alert fatigue and make engineers ignore important notifications.

The design therefore separates:

```text
Warning
    ↓
Investigation

Critical
    ↓
Engineering action

Page
    ↓
Immediate on-call response
```

Alerts should be actionable and connected to clear runbook instructions.

---

## 4. Automation vs. Operational Safety

Automated remediation can reduce recovery time.

However, database actions such as dropping replication slots or terminating queries can cause data loss, replication problems, or additional outages if performed incorrectly.

Therefore, the detection script is intentionally read-only.

The preferred approach is:

```text
Automated detection
        ↓
AI / monitoring recommendation
        ↓
Human verification
        ↓
Approved production action
```

This provides automation benefits while keeping high-risk decisions under human control.

---

## 5. Analytics vs. Production Reliability

Using the PostgreSQL read replica for both clinician dashboards and analytics reduces infrastructure cost.

However, large analytical queries can interfere with replica recovery.

The incident demonstrated this type of risk through recovery conflicts.

As VitalLink grows, separating analytics workloads into a dedicated analytics platform or warehouse could improve isolation.

The tradeoff is additional infrastructure and operational cost.

---

## 6. Materialized Views vs. Data Freshness

Materialized views can make dashboard queries faster because expensive aggregation work is performed ahead of time.

However, the views become stale when refresh jobs fail.

Refreshing twice per day also creates a natural limit on freshness.

Possible improvements include:

* More frequent refreshes.
* Monitoring refresh success.
* Monitoring view age.
* Investigating recovery conflicts.
* Moving analytical workloads away from the production replica.

More frequent refreshes improve freshness but increase database workload.

---

## 7. AI Assistance vs. Security and Privacy Risk

AI-assisted operations can reduce investigation time by correlating metrics, logs, and alerts.

However, AI systems can introduce:

* Privacy risks.
* Security risks.
* Incorrect recommendations.
* Excessive access permissions.
* Additional infrastructure complexity.

For VitalLink, AI should therefore begin with read-only operational telemetry and avoid unnecessary PHI.

Human approval should remain required for high-risk production actions.

---

## 8. Simplicity vs. Observability

A small system is easier to operate, but limited monitoring makes failures harder to diagnose.

VitalLink should invest in observability for the components that directly affect user journeys:

* Reading ingestion.
* Alert processing.
* PostgreSQL primary.
* Read replica.
* Replication slots.
* Materialized-view refreshes.
* Dashboard data freshness.

The goal is not to monitor everything equally, but to provide enough visibility to detect and diagnose failures quickly.

---

## Final Position

The overall approach favors:

* Strong reliability for patient-safety-related workflows.
* Explicit data-freshness monitoring.
* Read-only automated detection.
* Human approval for destructive actions.
* Clear operational thresholds.
* Gradual introduction of AI assistance.
* Separation of analytics workloads as the platform grows.

These choices balance reliability and safety against engineering cost and operational complexity.
