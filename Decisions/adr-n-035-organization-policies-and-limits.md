---
sidebar_position: 36
title: "ADR-N-035: Every Organization Policy and Limit Is a Field of the Organization"
---

# ADR-N-035: Every Organization Policy and Limit Is a Field of the Organization

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner (direction of 2026-09-24)

## 1. Context

The owner's direction of 2026-09-24: "all policies and limits should be able to set up in organization settings".

Today an organization sets four things in its manifest: who may open a project, a project's default visibility, the default project quota and the name cooling period (`Organization.spec.projects`, PF-65, PF-73, PF-78). Everything else that bounds what people and workloads may do is fixed by the installation, and an organization cannot see or change it:

- **Edge rates:** an APISIX `limit-count` per route class, written in the deployment's plugin files. It is 300 requests a minute per address for the web routes, 1200 for the Portal API and the context-space routes, and 5000 for a public endpoint.
- **Request bodies:** the edge accepts 16 MiB and the gateway 8 MiB, both constants.
- **Sign-in:** the edge session idles out after 1 hour and ends after 10 hours, the same as the realm's SSO idle and maximum. The realm's password policy is 12 characters with upper case, lower case and a digit. An invitation link lives 12 hours, the realm's admin action-token lifespan.
- **Pipelines:** a pipeline keeps its last 1000 rejected records, and a sample for a pipeline test is at most 5 MiB. Both are constants.
- **The assistant and agents:** the only bound is runs per project per day (PF-73). There is no spend limit and no list of allowed models.
- **Project quota:** an absent default means no limit at all, and two of the quota's dimensions, `ingestEventsPerSecond` and `entitiesPerSpace`, are enforced nowhere.

An organization that wants a lower rate for the web, a shorter invitation, a cap on model spend, or no public apps at all has no place to say so. The operator who runs the node has no way to say how far an organization may go.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Configuration as code | **Full** | Every setting is a field of the one `Organization` manifest in the organization repository. It is reviewed, versioned and approved like any change (PF-52). |
| Security by design | **Full** | An organization moves a setting only inside the bound the operator set. A security setting has a floor it cannot go below, and a change takes the red lane with an `org-admin` approval. |
| Standard solutions before custom code | **Full** | Each enforcer keeps its own mechanism: APISIX plugins, the gateway's rate limiter, the Keycloak realm, the Portal's verdict and the runner. Only the value's source changes. |
| Transparency | **Full** | A refusal names the limit, its effective value, where the value comes from and who may change it. |
| Resource economy | **Full** | The operator's bounds keep one organization from promising more than one node holds. |

## 3. Decision

1. **One catalog, three trees of the `Organization` manifest.**
   - `spec.projects` keeps its four fields (PF-65, PF-73, PF-78). Moving them would rewrite every committed Organization manifest for no gain.
   - `spec.policies` holds the choices.
   - `spec.limits` holds the numbers.

   Every entry has a default, a bound and one enforcer. An absent field is its default, and an unknown field is refused, as for every kind.
2. **Bounds belong to the operator.** The deployment sets them in the Portal's values (`portal.organizationBounds`), and the Portal reads them from a mounted file. An entry the values leave out keeps the built-in bound of the catalog below.
   - For a number, the bound is a ceiling.
   - For a security setting (a password length, a session lifetime), the bound is the floor or ceiling that keeps it safe.

   The Portal refuses, on every door and before a `Change` exists, an Organization change that crosses a bound. The refusal names the entry, the value and the bound. The same check runs again at approval, so a bound lowered in between is honoured.
3. **Red lane, `org-admin` approves.** An `Organization` change is red lane, as a role or the lane policy already is (PF-52).
4. **Each enforcer reads the effective value.** A project's own override, where the catalog allows one, comes first. Then the organization's value, then the default. A change reaches the enforcer on the next reconcile, and the activity log records the old and the new value.
5. **Lowering never deletes.** A lowered limit refuses new writes and new resources only. Something already over the limit keeps running, and the project's usage shows it over the limit (PF-75).
6. **A refusal says what to do.** For example: "the organization allows 3 public endpoints (3 in use); an org admin can change this in Organization settings".
7. **The catalog.** Where an entry has a project override, the project's value may only lower the organization's (PF-73).

| Section | Field | Default | Built-in bound | Enforcer |
|---|---|---|---|---|
| Projects | `spec.projects.creation` | `org-admin` | — | Portal, `POST /api/v1/projects` (PF-65) |
| Projects | `spec.projects.visibility` | `organization` | — | Portal doors |
| Projects | `spec.projects.quota.*` (PF-73's dimensions) | no limit | the operator's per-dimension ceiling | Portal verdict (PF-74), reconciler, agent runner, gateway |
| Projects | `spec.projects.nameCooldownDays` | 30 | 0 … 365 | Portal, `POST /api/v1/projects` (PF-78) |
| Applications | `spec.policies.apps.public` | `allowed` (`allowed` or `refused`) | — | Portal verdict on every door (AP-120) |
| Edge | `spec.limits.edge.requestsPerMinute.web` | 300 per address | 3000 | the edge: APISIX routes and the composed edge file (ADR-N-030) |
| Edge | `spec.limits.edge.requestsPerMinute.api` | 1200 per token | 12000 | the edge |
| Edge | `spec.limits.edge.requestsPerMinute.dataRead` | 1200 per token | 12000 | the edge, context-space routes, `GET` and `HEAD` |
| Edge | `spec.limits.edge.requestsPerMinute.dataWrite` | 1200 per token | 12000 | the edge, context-space routes, other methods |
| Edge | `spec.limits.edge.requestsPerMinute.publicEndpoint` | 5000 per address | 50000 | the edge, public endpoint routes |
| Edge | `spec.limits.edge.maxRequestBodyMegabytes` | 16 | 64 | the edge (`client_max_body_size`) |
| Edge | `spec.limits.gateway.maxRequestBodyMegabytes` | 8 | 64, and at most the edge's | the gateway |
| Sign-in | `spec.limits.signIn.sessionIdleMinutes` | 60 | 5 … 480; the reconciler writes the same value to the edge session and the realm's SSO idle, so the cookie never outlives the realm (AP-29) | the edge session and the realm |
| Sign-in | `spec.limits.signIn.sessionMaxHours` | 10 | 1 … 24 | the edge session and the realm |
| Sign-in | `spec.policies.signIn.password.minLength` | 12 | at least 12 | the realm's password policy |
| Sign-in | `spec.policies.signIn.password.history` | 0 | 0 … 24 | the realm's password policy |
| People | `spec.limits.people.invitationHours` | 12 | 1 … 168 | the realm's admin action-token lifespan, and the Portal's invitation call |
| Assistant and agents | `spec.policies.agents.models` | every model the installation's agent profiles name | only those models | the agent proxy |
| Assistant and agents | `spec.limits.agents.spendPerDay` | no limit | the operator's ceiling | the agent proxy |
| Assistant and agents | `spec.limits.agents.spendPerMonth` | no limit | the operator's ceiling | the agent proxy |
| Pipelines and data | `spec.limits.pipelines.rejectedKept` | 1000 per pipeline | 10000 | the Portal's pipeline outcomes |
| Pipelines and data | `spec.limits.pipelines.sampleMegabytes` | 5 | 50, and at most the edge body | the Portal and jcctl pipeline test |
| Pipelines and data | `spec.limits.data.uploadMegabytes` | 16 | at most the edge body | the Portal's upload and import routes |

Model spend is counted in the currency the agent proxy's provider bills in, with the day and the month in UTC. When a limit is reached, the agent proxy refuses the next model call, and the run ends with that reason.

Two entries of the owner's list are deliberately left out:

- **A required second factor.** The owner decided on 2026-09-24 that no second factor is required for now (T-2351). It joins `spec.policies.signIn` when the owner asks.
- **Temporal retention.** The broker has no retention to set. It joins `spec.limits.data` with the broker work that adds it, not before.

Who may create people is not a setting. It is the `people-admin` role (PF-91), and bindings decide who holds it.

## 4. Alternatives Considered

- **Settings in the deployment only.** This is what the platform does today. An organization can neither see nor choose, and every change is an operator's release.
- **A settings table in the Portal's database.** It would take the settings out of review, history and the red lane. A setting is configuration, so it is a manifest field.
- **Everything under `spec.policies` and `spec.limits`, including the projects section.** This would move three fields that are implemented and committed in every organization repository. The catalog names each field's path instead.

## 5. Consequences

- PF-96…PF-103 are new. PF-73's default quota keeps its meaning, and the operator's ceiling now bounds it.
- The platform's jc-core `OrganizationSpec` gains `policies` and `limits`, and the Portal pins the new jc-core. Organization settings edit every entry, and each enforcer reads it. Work: T-2715 (settings), T-2716 (enforcers), T-2717 (live journey).
- The deployment renders the bounds file from `portal.organizationBounds` and keeps today's values as the defaults, so an installation that sets nothing behaves as before.

## Related

- [Requirements/platform](../Requirements/platform.md) — PF-52, PF-65, PF-73…PF-75, PF-78, PF-96…PF-103.
- [Requirements/apps](../Requirements/apps.md) — AP-29, AP-120.
- [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md) — the composed edge file that writes the edge's rates.
- [ADR-N-031](adr-n-031-people-groups-and-app-groups.md) — people and the `people-admin` role.
