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

## 6. Deciding Who May Read and Write: Policies

An endpoint says where the data is served; a Policy says who may do what with it. Each policy covers one Context Space and grants (or refuses) a set of operations to one grantee. Like every other change, a new policy takes effect only once its proposal is approved.

### Write a Policy with the Form

The example below is the policy that lets anyone read the air quality measurements of Banská Bystrica, `public-read` in project `banskabystrica`.

1. Open **Policies** in the sidebar, at `/projects/banskabystrica/policies`. Each row says what the policy grants, to whom, on which space, and how many operations that covers. A refusal carries a red **Refusal** badge.
2. Click **New Policy**. The form opens in three groups; the first one is open.
3. **Who and what:**
   - **Name**: the short name the policy is filed under, for example `public-read`. Two policies of one project cannot share a name.
   - **Context Space**: the space whose data the policy decides about, here `ovzdusie`. A policy covers exactly one space.
   - **Effect**: **Grant** gives what the policy lists. **Refusal** takes it away, and the platform reads every refusal before any grant, so choose it only to close something another policy opens.
   - **Kind of grantee**: a role, a group, one person, a service account or a DID. For anonymous callers choose `role`.
   - **Grantee**: the name of that role, group, person or account as the identity provider spells it, here `public`.
   - **Operations**: tick one of the five named groups. Beside each group the form lists the operations it covers, and the two groups that change data carry a **changes data** mark. For read access tick `retrieveOps`. The single operations sit under **Individual operations**; a grant normally names a group instead. Nothing is granted until at least one box is ticked.
4. **Entities and attributes** (open the group):
   - Under **Entity selectors**, add one and enter **Entity type** `AirQualityObserved`. A selector with no type covers nothing, and the form refuses it at the field.
   - **Identifier pattern** is optional and narrows the grant to identifiers that match it, for example `^urn:ngsi-ld:AirQualityObserved:banskabystrica\.sk:ovzdusie:.*$`.
   - **Properties**: list the properties the grantee may reach, here `dateObserved`, `location`, `observedAt`, `pm10`, `pm25`. An attribute you leave out is not served, so the station's `reliability` and `refDevice` stay private. An empty list reaches every property.
   - **Relationships**: the same for relationships, for example `refDistrict`. An empty list reaches all of them.
5. **Residual filters and validity** (optional, open the group):
   - **q**: a condition on the attributes, for example `pm10>=0`. An entity that fails it is outside the grant.
   - **scopeQ**: the branch of the scope tree the grant covers, for example `/geo/SK/BB`, and everything under it.
   - **geoQ**: the area the grant covers; an entity outside it is neither read nor written.
   - **temporalQ**: the window of history the grant covers, for example `timerel=after&timeAt=2026-01-01T00:00:00Z`.
   - **Valid from** and **Valid to**: the instants the grant starts and stops applying. Leave both empty for a grant with no end.
6. Click **Check**. The verdict chip shows `Checked` when the policy is complete.
7. Click **Propose change**. The form will not propose a grant wider than you may propose yourself; when it is refused, the reason stands next to the button.
8. In `/projects/banskabystrica/approvals`, an approver reviews the grant and approves it. From then on the endpoints on `ovzdusie` answer anonymous readers with the five listed properties.

To change an existing policy, open its row menu and choose **Edit**. The same form opens with the stored values. The **YAML** view shows the same manifest, and a change in either view appears in the other.

## Related

- [Getting Started](./01-getting-started.md): first steps in the Portal.
- [Pipelines & Ingestion](./04-pipelines.md): ingesting data through target endpoints.
- [Dashboards & Visualization](./06-dashboards.md): drawing the entities of an endpoint on a map.
- [Collaborating with AI Agents](./08-working-with-ai-agents.md): connecting autonomous agents to endpoints via MCP.
