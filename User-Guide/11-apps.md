---
sidebar_position: 12
title: "Apps on Demand"
description: Ask for a small application, review what data it may use, preview it, publish it.
---

# Apps on Demand

An application on demand is a purpose-built web tool built for a specific city workflow, such as an air-quality monitor per district or an equipment inspection log. You pick an existing data endpoint, describe what you want, and an autonomous AI builder generates, tests, and deploys the application inside the platform.

All generated applications are strictly private to authenticated users within your project or organization. The AI builder operates in an isolated workspace and never holds your passwords, model API keys, or platform credentials.

## 1. Ask for an Application

1. Open your project, select **Applications**, and click **New Application**.
2. **Step 1: Pick an Endpoint.** Choose the published Endpoint that holds your context data. Inspect the live data preview: review the entity types, attribute names, LinkML schema terms, and a live sample of five entity records to ensure the data matches your expectations.
3. **Step 2: Describe Your Application.** Enter a title and explain in plain language what the application should display and how it should behave. Choose between a full-stack application (Rust backend with an embedded React interface) or a static web page.
4. **Step 3: Confirm Data Access.** Review the pre-populated access checklist derived from the endpoint. You may untick attributes or types your application does not need. The resulting list defines the strict perimeter of what your application can read.
5. Choose your target audience: **Project** (members of your team) or **Organization** (all signed-in users in the city). Generated applications cannot be made public.
6. Click **Generate Application**.

## 2. Watch the Builder and Answer Questions

1. The Portal opens a live conversation feed showing the builder's progress across each lifecycle stage (`starting`, `interviewing`, `building`, `testing`, `previewing`).
2. Watch the agent think, plan file changes, invoke build tools, and compile code in real time.
3. **Interactive Questionnaire:** If the agent needs architectural decisions clarified (such as choosing a default map center or chart colors), a structured form appears directly in the conversation. Fill in your answers and click **Submit Answer** to proceed.
4. If a build or test fails, the agent inspects the diagnostic compiler output and repairs its code autonomously.

## 3. Preview in the Sandbox

1. Once compilation and automated test suites pass, a sandboxed preview frame appears in the portal.
2. The preview runs in an isolated iframe. You can interact with the live map, test filters, and inspect layouts.
3. Read-only applications connect directly to your endpoint's policy-narrowed view. Applications that write data are wired to an ephemeral sandbox space so production records cannot be modified during evaluation.

## 4. Publish and Maintain

1. Click **Publish Application**. The platform generates a change proposal and submits a merge request to your organization's Gitea repository.
2. A domain approver reviews the diff and approves the merge request.
3. Once merged, the application is live at `https://{host}/apps/{name}/`.
4. Anyone opening the application URL must log in through Keycloak. Unauthenticated visitors are redirected to the platform login page.
5. In the Applications catalog, you can inspect operational metrics, review the Git commit history, or retire the application when no longer needed.

## 5. What Applications and Builders Cannot Do

- **No Public Exposure:** Generated applications require user login; they cannot be accessed anonymously.
- **No Stored Credentials:** Applications do not store API tokens or database passwords. Requests pass through the platform edge, which verifies your identity and forwards an authenticated session token.
- **No External Egress:** Applications and builder workspaces cannot connect to third-party databases, arbitrary internet hosts, or platform administration APIs.
- **No Self-Approval:** The builder agent cannot approve its own merge requests or alter platform security rules.

## 6. I Want a Map: Application or Dashboard?

When you need a map on screen, choose between an Application and a Dashboard based on what you are doing:

- **Use a Dashboard** when you need a standing operational view with curated map layers, deck.gl overlays, time-series charts, and multi-layer filters across your organization. Dashboards are configured declaratively in the Dashboards section and require no code generation.
- **Ask for an Application** when you need a purpose-built screen for a specific task or audience combining a map with tables, interactive stat cards, detail panels, forms to edit records, or client-side file downloads (PDF, CSV, GeoJSON). Applications are created on demand from a prompt against a single data endpoint.

## Related

- [00-intro.md](00-intro.md) — user guide overview and platform concepts.
- [05-endpoints-and-sharing.md](05-endpoints-and-sharing.md) — publishing and configuring data endpoints.
- [08-working-with-ai-agents.md](08-working-with-ai-agents.md) — collaborating with autonomous agents via MCP.
