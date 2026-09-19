# VitalLink Reliability Engineering Assignment

## Overview

This repository contains my reliability engineering submission for the VitalLink remote patient monitoring (RPM) platform.

VitalLink operates a healthcare platform where connected medical devices send patient vital readings through a mobile application to an ingestion API. The platform stores these readings in PostgreSQL and provides data to clinicians, analytics users, and an alerting pipeline.

The system handles protected health information (PHI), so reliability, data freshness, security, and controlled operational access are important considerations.

## Repository Structure

```text
vitallink-reliability-assignment/
│
├── README.md
├── PART1-reliability-strategy.md
├── PART2-incident-postmortem.md
├── PART3-runbook/
│   ├── README.md
│   └── detect_replication_issue.py
├── PART4-ai-augmented-ops.md
└── tradeoffs.md