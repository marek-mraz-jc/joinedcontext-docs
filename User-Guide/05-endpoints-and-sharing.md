---
sidebar_position: 6
title: Endpoints, Data Sharing & Integration
description: Publishing multi-representation endpoints, configuring audiences, projections, filters, and cross-project sharing.
---

# Endpoints, Data Sharing & Integration

In the joinedcontext platform, context spaces are private by default. The only mechanism for external systems, partner projects, public portals, or AI agents to access context data is through an Endpoint. This guide explains how to publish endpoints, configure audiences and representations, apply attribute projections and area filters, connect third-party tools, and reference shared endpoints across projects. It is written for data stewards, GIS analysts, and integration engineers.

Every change to an endpoint follows the change approval flow: you configure the endpoint form, run **Check**, click **Propose change**, and an approver reviews and merges the proposal in Approvals. Public endpoints route through the Red lane and require typing the resource name to confirm.

## 1. Endpoint Boundaries and Audiences

An Endpoint provides a policy-guarded view over one Context Space. Access is controlled by the endpoint audience:

- **Selected projects (`project-list`):** Only specified collaborative projects within the organization can query or reference this endpoint.
- **Organization (`organization`):** Any signed-in user or service account in the city administration can access this endpoint.
- **Public (`public`):** Open to anonymous callers worldwide for reading. Anonymous callers cannot write data or register subscriptions.

Each endpoint has its own address: a 26-character random slug nobody can guess.
`https://{host}/api/endpoint/{slug}/`

## 2. Publishing an Endpoint

### Create a New Endpoint

#### By hand

1. Navigate to **Endpoints** at `/projects/helsinki/endpoints`.
2. Click **New endpoint**.
3. In **Name**, enter `helsinki-bikes`. In **Title**, enter `City bikes live feed`.
4. In **Context Space**, select `helsinki`.
5. Click **Generate slug** to mint a random address.
6. Under **Audience**, select `Public: anyone with the address` (or `Organization`).
7. Under **Representations**, check the needed formats: `NGSI-LD API`, `GeoJSON`, `CSV`, `Excel (xlsx)`, and `MCP for AI assistants`.
8. Under **Model projection**, tick the classes (e.g. `BikeHireDockingStation`) and slots to expose. Identity slots `id` and `type` remain locked.
9. Click **Check**. You should see the verdict chip display `Checked`.
10. Click **Propose change**.
11. In `/projects/helsinki/approvals`, an approver enters `helsinki-bikes` into **Resource name confirmation** and clicks **Approve**.

The live journey `share.spec.ts` replays these steps.

#### By asking the assistant

Type into the assistant composer:
`Set the helsinki-bikes endpoint's rate limit to 300 requests per minute`

The assistant opens `/projects/helsinki/endpoints` with the form open and the rate limit updated. You run **Check** and click **Propose change**. An approver confirms it in Approvals.

The live journey `change.spec.ts` replays these steps.

## 3. Filtering Attributes and Geographic Areas

### Manage Filters on the Endpoint Page

#### By hand

1. On `/projects/helsinki/endpoints`, click the endpoint title to open its detail page at `/projects/helsinki/endpoints/helsinki-bikes`.
2. Review the live URL, audience, and enabled representations.
3. Under **Filtering**, view the active queries.
4. To add an attribute condition, scroll to **Add a condition**: choose **Attribute** (`availableBikeNumber`), **Condition** (`is greater than`), enter `Value` as `0`, and click **Add to the query**.
5. To restrict geographically, scroll to **Set the area from a box**: enter coordinates in **West**, **South**, **East**, and **North**, then click **Use this area**.
6. You should see the entity count update to show how many records match the filter.
7. Click **Propose this filter**.
8. In `/projects/helsinki/approvals`, an approver reviews and merges the filter change.

#### By asking the assistant

Type into the assistant composer:
`Propose a filter for endpoint helsinki-bikes with query availableBikeNumber>0`

The assistant updates the projection filter and opens `/projects/helsinki/endpoints/helsinki-bikes`. You inspect the matching count and click **Propose this filter**.

## 4. Connecting External Tools

### Connect GIS, Analytics, and Agent Clients

Copy endpoint addresses using the **Copy URL** button beside any slug:

- **QGIS & Desktop GIS:** Add a new vector layer using the GeoJSON representation at `https://{host}/api/endpoint/{slug}/file.geojson`, or add an OGC API Features connection pointing to `https://{host}/api/endpoint/{slug}/ogc/features`.
- **Microsoft Excel & Power BI:** Select **Data > From Web** and enter the CSV export URL `https://{host}/api/endpoint/{slug}/file.csv`.
- **Grafana:** In the Infinity datasource plugin, query `/file.geojson` to plot live positions on a Geomap panel.
- **AI Agents (MCP):** Connect external agent environments (such as Claude Code) to `https://{host}/api/endpoint/{slug}/mcp`. The agent discovers query tools automatically according to the endpoint policy.
- The schema and what you may do: `https://{host}/api/endpoint/{slug}/schema/v1/AirQualityObserved.json` is the published schema of one type, and `https://{host}/api/endpoint/{slug}/access` answers what the caller of that moment may read and write.

## 5. Cross-Project Data Sharing

### Reference a Shared Endpoint

#### By hand

1. Navigate to `/projects/helsinki/endpoints`.
2. Scroll to the **Shared with this project** section.
3. Review endpoints that other projects in the organization have shared with `helsinki`.
4. On the chosen row, click **Use in this project**.
5. A change proposal is submitted to declare a `SharedSpaceReference`.
6. In `/projects/helsinki/approvals`, an approver approves the reference. Once merged, the status chip shows **Referenced**.
7. To view all published endpoints across every project in the organization, open **All endpoints** at `/endpoints`.

#### By asking the assistant

Type into the assistant composer:
`What endpoints are shared with project helsinki?`

The assistant checks the cross-project directory and lists accessible endpoints, their source projects, and their published entity types.

## Related

- [Getting Started](./01-getting-started.md): first steps in the Portal.
- [Pipelines & Ingestion](./04-pipelines.md): ingesting data through target endpoints.
- [Dashboards & Visualization](./06-dashboards.md): drawing the entities of an endpoint on a map.
- [Collaborating with AI Agents](./08-working-with-ai-agents.md): connecting autonomous agents to endpoints via MCP.
