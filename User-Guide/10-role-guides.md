---
sidebar_position: 11
title: Role Guides & Daily Workflows
description: Role-specific responsibilities, typical daily tasks, and portal navigation cheat sheets.
---

# Role Guides & Daily Workflows

This chapter outlines daily operational workflows tailored to specific organizational roles.

---

## 1. Platform & City Administrator

**Primary Focus:** System stability, cluster capacity, tenant provisioning, and security governance.

### Daily Responsibilities

- Review system health and Linkerd service mesh traffic metrics in Grafana.
- Inspect and adjudicate **Red-Lane Merge Requests** (deletions, public endpoints, lane policies).
- Conduct quarterly access and secret key audits.
- Manage organization-level quotas and Keycloak identity integrations.

### Key Screens

- **Administration > Projects & Quotas**
- **Administration > User Management**
- **Pending Approvals (Red Lane)**
- **Cluster Diagnostics & Runbooks**

---

## 2. Data Architect

**Primary Focus:** Semantic data standards, LinkML modeling, blueprint authoring, and schema evolution.

### Daily Responsibilities

- Design and extend organisational LinkML data models in the visual schema editor.
- Import and adapt Smart Data Models for organisational departments.
- Author reusable ingestion blueprints for Data Stewards.
- Manage data dictionaries and URN namespace conventions ([ADR-N-001](../Decisions/adr-n-001-rust-typescript-stack.md)).

### Key Screens

- **Context Spaces > Data Models (LinkML Editor)**
- **Blueprint Management**
- **Data Dictionary Explorer**

---

## 3. Data Steward & Ingestion Engineer

**Primary Focus:** Day-to-day data flow management, sensor connectivity, and data quality.

### Daily Responsibilities

- Instantiate pipeline blueprints to connect IoT sensors and databases.
- Monitor pipeline throughput, error counts, and dead-letter queues.
- Manage Context Space entity lifecycles.
- Reconcile detected configuration drift using the Revert/Adopt tools.

### Key Screens

- **Pipelines & Ingestion Dashboard**
- **Context Space > Entity Explorer**
- **Drift Management Screen**

---

## 4. Data Consumer & GIS Analyst

**Primary Focus:** Data visualization, analytical reporting, and downstream consumption.

### Daily Responsibilities

- Build interactive MapLibre and deck.gl dashboards.
- Generate secure Endpoints for external visualization tools (QGIS, Excel, Grafana).
- Query live and historical context data via the Temporal API.
- Monitor endpoint rate limits and export tabular reports.

### Key Screens

- **Dashboards & Maps**
- **Endpoints & Sharing**
- **Temporal Query Explorer**

---

## 5. Security & Compliance Officer

**Primary Focus:** Data privacy, audit trail verification, GDPR compliance, and agent oversight.

### Daily Responsibilities

- Audit Context Gateway decision logs for denied access patterns.
- Review and approve public data sharing requests.
- Inspect autonomous AI agent MCP activity logs and token budgets.
- Execute subject erasure requests and monitor DPV privacy tags.

### Key Screens

- **Security & Audit Logs**
- **AI Agent Oversight & Revocation**
- **Privacy & Data Governance**

## Related

- [ADR-N-001](../Decisions/adr-n-001-rust-typescript-stack.md) — referenced above.
- [00-intro](00-intro.md) — user guide overview.
- [01-getting-started](01-getting-started.md) — first steps in the Portal.
