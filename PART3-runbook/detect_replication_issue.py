"""
VitalLink Replication Issue Detection Script

This script is intentionally READ-ONLY.

It detects potentially dangerous conditions involving:
* Primary database disk usage
* Inactive replication slots
* Excessive retained WAL
* Replica lag
* Materialized-view refresh failures

It does NOT:
* Drop replication slots
* Delete WAL
* Terminate database queries
* Restart PostgreSQL
* Change replication configuration

Those actions require human approval.
"""

import argparse
import json
import sys


# Alert thresholds

DISK_WARNING_PERCENT = 75
DISK_CRITICAL_PERCENT = 85
DISK_EMERGENCY_PERCENT = 90

REPLICA_LAG_WARNING_SECONDS = 60
REPLICA_LAG_CRITICAL_SECONDS = 300
REPLICA_LAG_SEVERE_SECONDS = 900

RETAINED_WAL_WARNING_GB = 1
RETAINED_WAL_CRITICAL_GB = 10


def get_sample_data():
    """
    Returns synthetic data based on the incident in the assignment.

    No real patient data or PHI is used.
    """

    return {
        "disk_usage_percent": 93,

        "replica_lag_seconds": 31241,

        "replication_slots": [
            {
                "slot_name": "replica_1",
                "slot_type": "physical",
                "active": True,
                "retained_wal_gb": 0.128,
            },
            {
                "slot_name": "pglogical_legacy_sub",
                "slot_type": "logical",
                "active": False,
                "retained_wal_gb": 94,
            },
        ],

        "materialized_view_refresh_failures": 2,
    }


def load_input_file(filename):
    """Load monitoring data from a JSON file."""

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        print(f"ERROR: Input file not found: {filename}")
        sys.exit(1)

    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in input file: {filename}")
        sys.exit(1)


def detect_disk_issue(data):
    """Check primary database disk usage."""

    disk_usage = data.get("disk_usage_percent", 0)

    if disk_usage >= DISK_EMERGENCY_PERCENT:
        return (
            "CRITICAL",
            f"Primary disk usage is {disk_usage}%. "
            "Immediate action is required to prevent database failure.",
        )

    if disk_usage >= DISK_CRITICAL_PERCENT:
        return (
            "CRITICAL",
            f"Primary disk usage is {disk_usage}%. "
            "Investigate WAL growth and database storage.",
        )

    if disk_usage >= DISK_WARNING_PERCENT:
        return (
            "WARNING",
            f"Primary disk usage is {disk_usage}%. "
            "Monitor growth and investigate the cause.",
        )

    return None


def detect_replica_lag(data):
    """Check read replica lag."""

    lag = data.get("replica_lag_seconds", 0)

    if lag >= REPLICA_LAG_SEVERE_SECONDS:
        return (
            "CRITICAL",
            f"Replica lag is {lag} seconds "
            f"({lag / 3600:.1f} hours).",
        )

    if lag >= REPLICA_LAG_CRITICAL_SECONDS:
        return (
            "CRITICAL",
            f"Replica lag is {lag} seconds.",
        )

    if lag >= REPLICA_LAG_WARNING_SECONDS:
        return (
            "WARNING",
            f"Replica lag is {lag} seconds.",
        )

    return None


def detect_slot_issues(data):
    """Check replication slots for inactivity and excessive WAL."""

    alerts = []

    slots = data.get("replication_slots", [])

    for slot in slots:
        slot_name = slot.get("slot_name", "unknown")
        slot_type = slot.get("slot_type", "unknown")
        active = slot.get("active", False)
        retained_wal = slot.get("retained_wal_gb", 0)

        if not active and retained_wal >= RETAINED_WAL_CRITICAL_GB:
            alerts.append(
                (
                    "CRITICAL",
                    f"Replication slot '{slot_name}' "
                    f"({slot_type}) is inactive and retaining "
                    f"{retained_wal} GB of WAL.",
                )
            )

        elif not active and retained_wal >= RETAINED_WAL_WARNING_GB:
            alerts.append(
                (
                    "WARNING",
                    f"Replication slot '{slot_name}' is inactive "
                    f"and retaining {retained_wal} GB of WAL.",
                )
            )

        elif retained_wal >= RETAINED_WAL_CRITICAL_GB:
            alerts.append(
                (
                    "CRITICAL",
                    f"Replication slot '{slot_name}' is retaining "
                    f"{retained_wal} GB of WAL.",
                )
            )

    return alerts


def detect_refresh_failures(data):
    """Check materialized-view refresh failures."""

    failures = data.get("materialized_view_refresh_failures", 0)

    if failures > 0:
        return (
            "CRITICAL",
            f"Materialized-view refresh failures detected: {failures}.",
        )

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Detect VitalLink PostgreSQL replication issues."
    )

    parser.add_argument(
        "--input",
        help="Optional JSON file containing monitoring data.",
    )

    args = parser.parse_args()

    if args.input:
        data = load_input_file(args.input)
    else:
        data = get_sample_data()

    print("=" * 65)
    print("VitalLink Replication Issue Detection")
    print("=" * 65)

    alerts = []

    # Check disk
    disk_alert = detect_disk_issue(data)

    if disk_alert:
        alerts.append(disk_alert)

    # Check replica lag
    lag_alert = detect_replica_lag(data)

    if lag_alert:
        alerts.append(lag_alert)

    # Check replication slots
    alerts.extend(detect_slot_issues(data))

    # Check materialized-view refresh
    refresh_alert = detect_refresh_failures(data)

    if refresh_alert:
        alerts.append(refresh_alert)

    print()

    if not alerts:
        print("STATUS: OK")
        print("No replication reliability issues detected.")
    else:
        print(f"ALERTS DETECTED: {len(alerts)}")
        print()

        for severity, message in alerts:
            print(f"[{severity}] {message}")

    print()
    print("-" * 65)
    print("IMPORTANT:")
    print("This script is READ-ONLY.")
    print("No production changes are performed automatically.")
    print("Destructive actions require human approval.")
    print("-" * 65)


if __name__ == "__main__":
    main()