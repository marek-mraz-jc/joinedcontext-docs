---
sidebar_position: 8
title: Workflow Coverage Matrix
description: Every step of every Portal workflow against the five test layers, the assistant tool that takes it, and the mutating routes each step owns.
---

# Workflow Coverage Matrix

This page is for whoever changes a workflow of the Portal and has to know what proves it still works: which test holds each step at each layer, which live journey walks it on `dev`, and which assistant tool takes the same step. TS-26 makes the matrix binding. The Portal's UI suite reads it (`ui/tests/workflow_coverage.json`, recorded from this page) and `ui/tests/gate_workflows.test.ts` fails when the tree stops matching it. Read off the code on 2026-09-25.

---

## 1. The layers and the rule

| Layer | What it proves | Where it lives |
|---|---|---|
| unit | the logic of the step, without I/O | `#[cfg(test)]` modules of the Portal crate, named by their source file |
| API | the route answers, refuses and writes as the step says, against the real router | `tests/*_tests.rs` of `joinedcontext-portal` |
| mocked UI | the page does the step against a mocked API: labels, refusals, the request it sends | `ui/tests/*.test.tsx` and `ui/e2e/*.spec.ts` of `joinedcontext-portal` |
| live journey | a real person does the step on `dev`, through Keycloak, and sees the result | `ui/e2e/live/*.spec.ts` of `joinedcontext-portal`, run in the hourly batch |
| assistant | the registered operation the assistant calls for the step, through the same handler, permission check and Change as the UI | `src/ops/` and `src/agents/capabilities.rs` of `joinedcontext-portal` |

The rule (TS-26): every step has a live journey and an assistant tool, or a cell that names the open task owing it. A step only a person may take (approving, deleting directly, minting a key, bringing a copy back; AG-11, AG-77) says so in the assistant cell instead of naming a tool, and `tests/attack_person_only_operations_tests.rs` proves the operation refuses an agent.

Every write step carries three refusals beside it, gated like the success they refuse:

- **no permission**: a viewer meets the write control disabled with its reason, and the route answers `403` (UI-44);
- **red verdict**: a check that fails keeps Propose closed and names the field (AG-77, PF-57);
- **secret typed in**: a literal secret where a `secretRef` belongs is refused before a branch exists, and never echoed (MF-24).

A workflow with no field that can hold a secret (people, groups, changes) has no secret row.

## 2. Reading a row

- A step is `workflow/step`; the workflow is the backticked name in the heading, the step the backticked name in the first column.
- The live cell is `` `ui/e2e/live/<spec>` › "<test title>" `` or `owed: T-nnnn`. A title rendered from a template (`${kind}: …`) counts only when the spec names the value as a string.
- The assistant cell is `` `jc_…` ``, `owed: T-nnnn`, or `person only: <why>`.
- The route table in section 4 gives every mutating operation of the Portal's OpenAPI document its steps, or `none: <why>`.
- After editing this page, run `pnpm record:workflows <docs>/Testing/07-workflow-coverage.md` in the Portal's `ui/` and commit the JSON with the change that made the page true.

## 3. Workflows

### 3.1 Sign in and out (`session`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `sign-in` | `joinedcontext-portal/src/auth/oidc.rs` | `tests/auth_tests.rs` | `ui/tests/page_login_page.test.tsx` | `ui/e2e/live/login.spec.ts` › "a person signs in from /login to the page they asked for, and signs out" | person only: signing in is a person proving who they are to Keycloak; no agent holds a person's password |
| `sign-out` | `joinedcontext-portal/src/auth/session.rs` | `tests/auth_tests.rs` | `ui/tests/auth.test.tsx` | `ui/e2e/live/login.spec.ts` › "a person signs in from /login to the page they asked for, and signs out" | person only: ending a session is the person's own act and would end the assistant's conversation with it |
| `refused-wrong-password` | `joinedcontext-portal/src/auth/oidc.rs` | `tests/edge_auth_csrf_tests.rs` | `ui/tests/page_login_page.test.tsx` | `ui/e2e/live/login.spec.ts` › "a wrong password gets no session, and an address off the Portal is not followed" | person only: a password is typed into Keycloak by the person, never through the assistant |

### 3.2 Organization settings and limits (`organization`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `read` | `joinedcontext-portal/src/branding.rs` | `tests/branding_api_tests.rs` | `ui/tests/organization_page.test.tsx` | `ui/e2e/live/organization.spec.ts` › "an administrator reads the organization and grants a role that reaches the person" | `jc_resource_get` |
| `edit-settings` | `joinedcontext-portal/src/quotas.rs` | `tests/ui_limits_tests.rs` | `ui/tests/organization_route.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | `jc_resource_propose` |
| `refused-no-permission` | `joinedcontext-portal/src/api/people.rs` | `tests/roles_matrix_tests.rs` | `ui/tests/organization_page.test.tsx` | `ui/e2e/live/organization.spec.ts` › "a viewer is told who can see the members, and the list is never fetched for them" | `jc_resource_propose` |

### 3.3 People (`people`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | `jc_person_create` |
| `read` | `joinedcontext-portal/src/api/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/organization.spec.ts` › "an administrator reads the organization and grants a role that reaches the person" | `jc_person_get` |
| `edit` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | `jc_person_edit` |
| `disable` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | `jc_person_disable` |
| `enable` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | `jc_person_enable` |
| `reset-password` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | person only: a reset sends a person a way into their account; an agent that can start one can take the account over |
| `remove-second-factor` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | person only: removing a second factor weakens a person's sign-in and is decided by an administrator in person |
| `sign-out-everywhere` | `joinedcontext-portal/src/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "10. nothing of the walk is left, the person is signed out everywhere and removed, and the steward signs out" | `jc_person_sign_out` |
| `remove` | `joinedcontext-portal/src/api/people.rs` | `tests/last_administrator_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "10. nothing of the walk is left, the person is signed out everywhere and removed, and the steward signs out" | person only: removing a person deletes their account and cannot be proposed as a Change a second person approves |
| `refused-no-permission` | `joinedcontext-portal/src/api/people.rs` | `tests/people_tests.rs` | `ui/tests/people_page.test.tsx` | `ui/e2e/live/organization.spec.ts` › "a viewer is told who can see the members, and the list is never fetched for them" | `jc_person_list` |

### 3.4 Groups and roles (`groups`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/groups.rs` | `tests/groups_api_tests.rs` | `ui/tests/access_groups.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "2. the organization: a settings edit rejected, a new person edited, disabled, enabled and reset, a group with a role, and the person's page" | `jc_resource_propose` |
| `grant-role` | `joinedcontext-portal/src/agents/grant.rs` | `tests/roles_matrix_tests.rs` | `ui/tests/role_bindings.test.tsx` | `ui/e2e/live/project-settings.spec.ts` › "a project role bound to a group reaches the group's member, and only as far as it says" | `jc_resource_propose` |
| `edit` | `joinedcontext-portal/src/groups.rs` | `tests/groups_api_tests.rs` | `ui/tests/group_page.test.tsx` | `ui/e2e/live/parity.spec.ts` › "RoleBinding stewards: the form, the REST route, the registry and the assistant plan the same change" | `jc_resource_propose` |
| `retire` | `joinedcontext-portal/src/reconciler/groups.rs` | `tests/group_delete_tests.rs` | `ui/tests/group_page.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "10. nothing of the walk is left, the person is signed out everywhere and removed, and the steward signs out" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/agents/grant.rs` | `tests/attack_grant_escalation_tests.rs` | `ui/tests/access_forms.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "nobody grants above their own rights, and the page gives the reason" | `jc_resource_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/agents/grant.rs` | `tests/access_escalation_tests.rs` | `ui/tests/form_role_bindings.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "a grant wider than the proposer's own rights is refused, and a narrower control is not" | `jc_resource_propose` |

### 3.5 Projects (`project`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/api/projects.rs` | `tests/projects_api_tests.rs` | `ui/tests/new_project.test.tsx` | `ui/e2e/live/readiness-project.spec.ts` › "a project is opened, duplicated where it can be, and deleted" | `jc_project_create` |
| `read` | `joinedcontext-portal/src/api/export.rs` | `tests/project_read_tests.rs` | `ui/tests/page_project_settings.test.tsx` | `ui/e2e/live/walk.spec.ts` › "every page opens cleanly for the steward" | `jc_project_get` |
| `copy` | `joinedcontext-portal/src/api/import.rs` | `tests/project_duplicate_tests.rs` | `ui/tests/project_duplicate_import.test.tsx` | `ui/e2e/live/readiness-project.spec.ts` › "a project is opened, duplicated where it can be, and deleted" | person only: copying a whole repository of the forge under a new slug is a person's decision in the Portal, not a tool a run holds (PF-89) |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/delete_not_there_tests.rs` | `ui/tests/project_settings.test.tsx` | `ui/e2e/live/readiness-project.spec.ts` › "a project is opened, duplicated where it can be, and deleted" | person only: deleting a project removes its repository and every resource in it, and no agent may take that act (AG-11) |
| `refused-no-permission` | `joinedcontext-portal/src/api/delete.rs` | `tests/attack_cross_project_tests.rs` | `ui/tests/project_settings.test.tsx` | `ui/e2e/live/project-settings.spec.ts` › "an old Access link lands on Members, and a viewer meets Delete project refused" | `jc_project_delete` |

### 3.6 Import a project (`import`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `upload` | `joinedcontext-portal/src/api/import.rs` | `tests/import_api_tests.rs` | `ui/e2e/import.spec.ts` | `ui/e2e/live/import.spec.ts` › "a steward checks a bundle, reads what it would do, proposes it, and the rejected import leaves nothing" | `jc_project_import` |
| `from-git` | `joinedcontext-portal/src/api/import_git.rs` | `tests/project_import_git_tests.rs` | none: the Portal has no Git import screen; `jcctl` and `jc_project_import` send `?format=git` | `ui/e2e/live/import-git.spec.ts` › "a steward checks a project's Git export as a new project, and nothing is created" | `jc_project_import` |
| `refused-no-permission` | `joinedcontext-portal/src/api/import.rs` | `tests/edge_import_mutate_tests.rs` | `ui/tests/import_wizard.test.tsx` | `ui/e2e/live/import.spec.ts` › "a viewer meets Propose disabled with its reason, and the door refuses the same bundle" | `jc_project_import` |
| `refused-secret` | `joinedcontext-portal/src/api/import.rs` | `tests/import_credential_needs_tests.rs` | `ui/e2e/import.spec.ts` | `ui/e2e/live/import.spec.ts` › "a credential written into a bundle is refused at the door, before a report, and never echoed" | `jc_project_import` |

### 3.7 Context spaces (`space`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/spaces.rs` | `tests/spaces_api_tests.rs` | `ui/tests/page_spaces_page.test.tsx` | `ui/e2e/live/assistant-creates.spec.ts` › "the assistant opens the form for a context space, filled from one sentence" | `jc_space_propose` |
| `complete-from-sample` | `joinedcontext-portal/src/ops/space_complete.rs` | `tests/space_complete_tests.rs` | `ui/tests/space_complete.test.tsx` | `ui/e2e/live/space_complete.spec.ts` › "complete a space from sample file and propose change" | `jc_space_complete` |
| `read` | `joinedcontext-portal/src/spaces.rs` | `tests/resource_get_tests.rs` | `ui/tests/space_inside.test.tsx` | `ui/e2e/live/walk.spec.ts` › "every page opens cleanly for the steward" | `jc_resource_get` |
| `edit` | `joinedcontext-portal/src/api/mutate.rs` | `tests/resource_mutate_tests.rs` | `ui/tests/resource_edit.test.tsx` | `ui/e2e/live/form-pages.spec.ts` › "an edit form opened from its address survives a reload, and saving lands on the list" | `jc_resource_propose` |
| `approve` | `joinedcontext-portal/src/change.rs` | `tests/changes_tests.rs` | `ui/tests/approval_actions.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "an administrator of the kind approves their own change, and the space is created" | person only: a person approves a change and an agent never does (AG-11, PF-58) |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/change.spec.ts` › "the assistant opens a change or a removal on the kind's page, and the person proposes it" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/permissions_tests.rs` | `ui/tests/permission_guard.test.tsx` | `ui/e2e/live/viewer-refused.spec.ts` › "a viewer is refused with a reason on every page, and at the door" | `jc_space_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/ops/verdict.rs` | `tests/edge_verdict_gate_tests.rs` | `ui/tests/propose_checked.test.ts` | `ui/e2e/live/verdict-gate.spec.ts` › "the verdict gate: unchecked refuses, a check opens it, an edit closes it again" | `jc_space_propose` |

### 3.8 Data models (`datamodel`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/agents/model_change.rs` | `tests/datamodel_source_tests.rs` | `ui/tests/datamodel_form.test.tsx` | `ui/e2e/live/parity.spec.ts` › "DataModel helsinki: the form, the REST route, the registry and the assistant plan the same change" | `jc_model_propose` |
| `infer-from-sample` | `joinedcontext-portal/src/tools/model_tools.rs` | `tests/model_tools_proxy_tests.rs` | `ui/tests/model_file_drop.test.tsx` | `ui/e2e/live/models.spec.ts` › "a steward drafts a model from a CSV sample into the editor" | `jc_model_infer` |
| `import-smart-data-model` | `joinedcontext-portal/src/tools/model_tools.rs` | `tests/edge_model_tools_tests.rs` | `ui/tests/sdm_import.test.tsx` | `ui/e2e/live/models.spec.ts` › "a steward imports a Smart Data Model into a model being built" | `jc_catalog_search` |
| `add-class-enum-relation` | `joinedcontext-portal/src/api/datamodels.rs` | `tests/datamodel_source_tests.rs` | `ui/tests/linkml_visual_editor.test.tsx` | `ui/e2e/live/models.spec.ts` › "a steward builds a model with classes, an enum and a has-many relation, edits its source, checks and proposes it" | `jc_model_source_put` |
| `validate` | `joinedcontext-portal/src/tools/model_tools.rs` | `tests/edge_model_tools_tests.rs` | `ui/tests/linkml_preview.test.tsx` | `ui/e2e/live/verdict-gate.spec.ts` › "a check refuses a model that does not exist, names the field, and a fix clears it" | `jc_manifest_dry_run` |
| `read` | `joinedcontext-portal/src/api/datamodels.rs` | `tests/organization_datamodels_tests.rs` | `ui/tests/models_list_page.test.tsx` | `ui/e2e/live/walk.spec.ts` › "every page opens cleanly for the steward" | `jc_model_source_get` |
| `edit-source` | `joinedcontext-portal/src/api/datamodels.rs` | `tests/datamodel_source_tests.rs` | `ui/tests/linkml_source_editor.test.tsx` | `ui/e2e/live/models.spec.ts` › "a steward builds a model with classes, an enum and a has-many relation, edits its source, checks and proposes it" | `jc_model_source_put` |
| `share-with-organization` | `joinedcontext-portal/src/api/datamodels.rs` | owed: T-2884 | owed: T-2884 | owed: T-2885 | person only: sharing puts a project's schema in front of every project; the Change is red and an organization administrator approves it, so a person decides to ask (DM-77, PF-58) |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/models.spec.ts` › "a steward proposes removing a model, and the rejected removal keeps it" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/permissions_tests.rs` | `ui/tests/models_page_save.test.tsx` | `ui/e2e/live/viewer-refused.spec.ts` › "a viewer is refused with a reason on every page, and at the door" | `jc_model_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/ops/verdict.rs` | `tests/verdict_findings_tests.rs` | `ui/tests/linkml_editor.test.tsx` | `ui/e2e/live/verdict-gate.spec.ts` › "a check refuses a model that does not exist, names the field, and a fix clears it" | `jc_model_propose` |

### 3.9 Data sources (`datasource`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/pipeline_secrets.rs` | `tests/datasources_api_tests.rs` | `ui/tests/page_data_sources_page.test.tsx` | `ui/e2e/live/load.spec.ts` › "a data source and a pipeline, checked, tested, proposed and approved through the UI; entities in Explore" | `jc_datasource_propose` |
| `check` | `joinedcontext-portal/src/ops/verdict.rs` | `tests/datasources_api_tests.rs` | `ui/tests/datasources_view.test.tsx` | `ui/e2e/live/runner-inputs.spec.ts` › "csv: declared from the runner's form, tested, approved; entities arrive and the counter moves" | `jc_datasource_check` |
| `read` | `joinedcontext-portal/src/api/resources.rs` | `tests/resource_get_tests.rs` | `ui/tests/datasources_view.test.tsx` | `ui/e2e/live/walk.spec.ts` › "every page opens cleanly for the steward" | `jc_resource_get` |
| `edit` | `joinedcontext-portal/src/api/mutate.rs` | `tests/resource_mutate_tests.rs` | `ui/tests/resource_edit.test.tsx` | `ui/e2e/live/form-pages.spec.ts` › "an edit form opened from its address survives a reload, and saving lands on the list" | `jc_datasource_propose` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/change.spec.ts` › "the assistant opens a change or a removal on the kind's page, and the person proposes it" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/permissions_tests.rs` | `ui/tests/permission_guard.test.tsx` | `ui/e2e/live/viewer-refused.spec.ts` › "a viewer is refused with a reason on every page, and at the door" | `jc_datasource_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/ops/verdict.rs` | `tests/strict_gate_tests.rs` | `ui/tests/propose_checked.test.ts` | `ui/e2e/live/forms-examples.spec.ts` › "every create form is green from its own examples" | `jc_datasource_check` |
| `refused-secret` | `joinedcontext-portal/src/pipeline_secrets.rs` | `tests/attack_secret_leak_tests.rs` | `ui/tests/secret_ref_widget.test.tsx` | `ui/e2e/live/secrets.spec.ts` › "a secret written into the YAML view is refused by its field, and the value is never echoed" | `jc_datasource_propose` |

### 3.10 Pipelines (`pipeline`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/api/pipelines.rs` | `tests/pipeline_test_tests.rs` | `ui/tests/page_pipelines_page.test.tsx` | `ui/e2e/live/load.spec.ts` › "a data source and a pipeline, checked, tested, proposed and approved through the UI; entities in Explore" | `jc_pipeline_propose` |
| `sample-source` | `joinedcontext-portal/src/ops/pipeline_steps.rs` | `tests/ops_pipeline_steps_tests.rs` | `ui/tests/pipeline_flow_steps.test.tsx` | `ui/e2e/live/build-samples.spec.ts` › "a build on helsinki-news reads its samples and the preview shows rows" | `jc_pipeline_sample_source` |
| `mapping` | `joinedcontext-portal/src/ops/pipeline_steps.rs` | `tests/ops_pipeline_steps_tests.rs` | `ui/tests/mappings_editor.test.tsx` | `ui/e2e/live/runner-inputs.spec.ts` › "csv: declared from the runner's form, tested, approved; entities arrive and the counter moves" | `jc_pipeline_try_mapping` |
| `validation` | `joinedcontext-portal/src/pipeline_validation.rs` | `tests/ops_pipeline_steps_tests.rs` | `ui/tests/part_pipeline_test.test.tsx` | `ui/e2e/live/runner-inputs.spec.ts` › "csv: declared from the runner's form, tested, approved; entities arrive and the counter moves" | `jc_pipeline_validate` |
| `test` | `joinedcontext-portal/src/api/pipeline_test.rs` | `tests/pipeline_test_tests.rs` | `ui/tests/pipeline_test_functions.test.ts` | `ui/e2e/live/load.spec.ts` › "a data source and a pipeline, checked, tested, proposed and approved through the UI; entities in Explore" | `jc_pipeline_test` |
| `target` | `joinedcontext-portal/src/ops/feed_shape.rs` | `tests/pipeline_metrics_tests.rs` | `ui/tests/pipeline_runs.test.tsx` | `ui/e2e/live/assistant-paths.spec.ts` › "Integrate a pipeline from a CSV and its feed stays within its budgets (T-2695, T-2697)" | `jc_pipeline_metrics` |
| `retry-rejected` | `joinedcontext-portal/src/api/internal/pipeline_rejected.rs` | `tests/pipeline_rejected_api_tests.rs` | `ui/tests/pipeline_rejected.test.tsx` | `ui/e2e/live/pipeline-workbench.spec.ts` › "a pipeline built in the workbench writes only what the model takes" | person only: a person replays the records they picked on the pipeline page once the fix merged; the assistant changes the mapping with `jc_pipeline_propose` (PL-61) |
| `edit` | `joinedcontext-portal/src/api/mutate.rs` | `tests/resource_mutate_tests.rs` | `ui/tests/pipeline_editor.test.tsx` | `ui/e2e/live/parity.spec.ts` › "Pipeline hel-news: the form, the REST route, the registry and the assistant plan the same change" | `jc_pipeline_propose` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/change.spec.ts` › "the assistant opens a change or a removal on the kind's page, and the person proposes it" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/permissions_tests.rs` | `ui/tests/pipelines_view.test.tsx` | `ui/e2e/live/viewer-refused.spec.ts` › "a viewer is refused with a reason on every page, and at the door" | `jc_pipeline_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/pipeline_validation.rs` | `tests/strict_gate_tests.rs` | `ui/tests/pipeline_studio_debug.test.tsx` | `ui/e2e/live/verdict-gate.spec.ts` › "the verdict gate: unchecked refuses, a check opens it, an edit closes it again" | `jc_pipeline_validate` |
| `refused-secret` | `joinedcontext-portal/src/pipeline_secrets.rs` | `tests/pipeline_secrets_tests.rs` | `ui/tests/part_secret_ref.test.tsx` | `ui/e2e/live/secrets.spec.ts` › "no form offers a field for a secret's value, on any data source type" | `jc_pipeline_propose` |

### 3.11 Endpoints (`endpoint`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/agents/endpoints.rs` | `tests/assistant_share_tests.rs` | `ui/tests/endpoint_form.test.tsx` | `ui/e2e/live/share.spec.ts` › "an endpoint proposed and approved through the UI: Live, the hidden attribute absent, the viewer refused on the organization one" | `jc_endpoint_propose` |
| `read` | `joinedcontext-portal/src/api/resources.rs` | `tests/resource_list_tests.rs` | `ui/tests/all_endpoints_view.test.tsx` | `ui/e2e/live/all-endpoints.spec.ts` › "an administrator reads every project's endpoints in one table and opens one project's" | `jc_endpoint_list_all` |
| `try-it` | `joinedcontext-portal/src/agents/data_query.rs` | `tests/edge_resource_reads_tests.rs` | `ui/tests/try_it.test.tsx` | `ui/e2e/live/workspace-preview.spec.ts` › "a copy's preview answers on its own addresses and stops answering when stopped" | `jc_ask` |
| `edit` | `joinedcontext-portal/src/api/mutate.rs` | `tests/resource_mutate_tests.rs` | `ui/tests/endpoint_editor_toggles.test.tsx` | `ui/e2e/live/parity.spec.ts` › "Endpoint helsinki-bikes: the form, the REST route, the registry and the assistant plan the same change" | `jc_endpoint_propose` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/change.spec.ts` › "the assistant opens a change or a removal on the kind's page, and the person proposes it" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/agents/share.rs` | `tests/edge_agents_share_tests.rs` | `ui/tests/endpoint_sharing.test.tsx` | `ui/e2e/live/all-endpoints.spec.ts` › "a viewer sees the endpoints of the projects they may read, and of no other" | `jc_endpoint_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/ops/verdict.rs` | `tests/propose_refused_before_parsed_tests.rs` | `ui/tests/endpoint_proposal_card.test.tsx` | `ui/e2e/live/one-change-at-a-time.spec.ts` › "a second change on the same resource is refused by the name of the first, and lands once that one is decided" | `jc_endpoint_propose` |

### 3.12 Policies and grants (`policy`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/agents/grant.rs` | `tests/access_escalation_tests.rs` | `ui/tests/policy_form.test.tsx` | `ui/e2e/live/change.spec.ts` › "the assistant drafts a role grant into the Members form, and the person proposes it as a red change" | `jc_resource_propose` |
| `edit` | `joinedcontext-portal/src/api/mutate.rs` | `tests/resource_mutate_tests.rs` | `ui/tests/form_role_bindings.test.tsx` | `ui/e2e/live/parity.spec.ts` › "RoleBinding stewards: the form, the REST route, the registry and the assistant plan the same change" | `jc_resource_propose` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9d. a grant on the walk's space is approved, then removed from the policies page" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/agents/grant.rs` | `tests/attack_grant_escalation_tests.rs` | `ui/tests/roles_matrix.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "a person without the role is refused an approval, in the page and at the door" | `jc_resource_propose` |
| `refused-red-verdict` | `joinedcontext-portal/src/agents/grant.rs` | `tests/access_escalation_tests.rs` | `ui/tests/access_forms.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "a grant wider than the proposer's own rights is refused, and a narrower control is not" | `jc_resource_propose` |

### 3.13 Subscriptions (`subscription`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/reconciler/subscriptions.rs` | `tests/subscription_reconciler_tests.rs` | `ui/tests/subscription_form.test.tsx` | `ui/e2e/live/kind-subscriptions.spec.ts` › "Subscription: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `assistant-opens-form` | `joinedcontext-portal/src/agents/change.rs` | `tests/assistant_access_tests.rs` | `ui/tests/form_asks_the_assistant.test.tsx` | `ui/e2e/live/kind-subscriptions.spec.ts` › "Subscription: the assistant opens the kind's form and proposes nothing" | `jc_ui_navigate` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/kind-subscriptions.spec.ts` › "Subscription: created, changed and removed through the page by a person" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/permissions_tests.rs` | `ui/tests/permission_guard.test.tsx` | `ui/e2e/live/kind-subscriptions.spec.ts` › "Subscription: a viewer finds every write control disabled with its reason, and the door answers 403" | `jc_resource_propose` |

### 3.14 Sync sources (`syncsource`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/sync/guard.rs` | `tests/sync_source_routes_tests.rs` | `ui/tests/page_sync_sources_page.test.tsx` | `ui/e2e/live/kind-syncsources.spec.ts` › "SyncSource: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `sync-now` | `joinedcontext-portal/src/sync/driver.rs` | `tests/sync_source_routes_tests.rs` | `ui/tests/sync_sources_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9b. a sync source syncs, pauses and resumes, refuses an unsigned webhook, and is detached" | `jc_syncsource_sync` |
| `pause` | `joinedcontext-portal/src/sync/state.rs` | `tests/ops_sync_sources_tests.rs` | `ui/tests/sync_sources_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9b. a sync source syncs, pauses and resumes, refuses an unsigned webhook, and is detached" | `jc_syncsource_pause` |
| `detach` | `joinedcontext-portal/src/sync/state.rs` | `tests/edge_sync_detach_webhook_tests.rs` | `ui/tests/sync_sources_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9b. a sync source syncs, pauses and resumes, refuses an unsigned webhook, and is detached" | `jc_syncsource_detach` |
| `webhook` | `joinedcontext-portal/src/sync/webhook_secrets.rs` | `tests/sync_webhook_secrets_tests.rs` | `ui/tests/sync_sources_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9b. a sync source syncs, pauses and resumes, refuses an unsigned webhook, and is detached" | person only: a webhook is the remote repository calling in with its signature; no person or agent takes this step by hand |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/kind-syncsources.spec.ts` › "SyncSource: created, changed and removed through the page by a person" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/edge_keys_sync_tests.rs` | `ui/tests/sync_sources_view.test.tsx` | `ui/e2e/live/kind-syncsources.spec.ts` › "SyncSource: a viewer finds every write control disabled with its reason, and the door answers 403" | `jc_syncsource_sync` |
| `refused-secret` | `joinedcontext-portal/src/sync/webhook_secrets.rs` | `tests/sync_webhook_secrets_tests.rs` | `ui/tests/secret_ref_name.test.ts` | `ui/e2e/live/secrets.spec.ts` › "a token pasted into the secret name is refused by the name of the field" | `jc_resource_propose` |

### 3.15 Dashboards, layers and KPIs (`dashboard`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/agents/kpi.rs` | `tests/dashboards_tests.rs` | `ui/tests/dashboard_editors.test.tsx` | `ui/e2e/live/kind-dashboards.spec.ts` › "Dashboard: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `layer` | `joinedcontext-portal/src/api/resources.rs` | `tests/dashboards_tests.rs` | `ui/tests/deck_layer_for.test.ts` | `ui/e2e/live/kind-layers.spec.ts` › "Layer: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `kpi-pipeline` | `joinedcontext-portal/src/agents/kpi_pipeline.rs` | `tests/assistant_kpi_tests.rs` | `ui/tests/kpi_pipeline_card.test.tsx` | `ui/e2e/live/analyse.spec.ts` › "a KPI pipeline configured with the preset, tested on endpoint, proposed, and verified in Explore" | `jc_kpi_compute` |
| `read` | `joinedcontext-portal/src/agents/kpi.rs` | `tests/dashboards_tests.rs` | `ui/tests/page_dashboards_page.test.tsx` | `ui/e2e/live/bystrica-kpi.spec.ts` › "one application shows both bodies, each number the number in its own space" | `jc_kpi_compute` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/kind-dashboards.spec.ts` › "Dashboard: created, changed and removed through the page by a person" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/permissions_tests.rs` | `ui/tests/dashboard_pages.test.tsx` | `ui/e2e/live/kind-dashboards.spec.ts` › "Dashboard: a viewer finds every write control disabled with its reason, and the door answers 403" | `jc_resource_propose` |

### 3.16 Shared spaces and registrations (`sharing`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `share-space` | `joinedcontext-portal/src/references.rs` | `tests/foreign_model_mirror_tests.rs` | `ui/e2e/sharing.spec.ts` | `ui/e2e/live/kind-shared.spec.ts` › "SharedSpaceReference: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `read-shared` | `joinedcontext-portal/src/reconciler/foreign.rs` | `tests/foreign_model_mirror_tests.rs` | `ui/e2e/sharing.spec.ts` | `ui/e2e/live/shared.spec.ts` › "the old address lands on what other projects share with this one, and the list follows the audience rule" | `jc_federation_graph` |
| `register-source` | `joinedcontext-portal/src/reconciler/registrations.rs` | `tests/csrs_api_tests.rs` | `ui/tests/contextsourceregistration_form.test.tsx` | `ui/e2e/live/kind-csrs.spec.ts` › "ContextSourceRegistration: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/attack_cross_project_tests.rs` | `ui/e2e/sharing.spec.ts` | `ui/e2e/live/kind-shared.spec.ts` › "SharedSpaceReference: a viewer finds every write control disabled with its reason, and the door answers 403" | `jc_resource_propose` |

### 3.17 Service accounts (`serviceaccount`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `create` | `joinedcontext-portal/src/api/service_accounts.rs` | `tests/service_account_api_tests.rs` | `ui/tests/serviceaccount_form.test.tsx` | `ui/e2e/live/kind-serviceaccounts.spec.ts` › "ServiceAccount: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `mint-key` | `joinedcontext-portal/src/api/service_accounts.rs` | `tests/ops_service_account_keys_tests.rs` | `ui/tests/service_accounts_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9a. a service account's API key is minted, rotated and revoked" | person only: a key is a credential shown once to the person who minted it; an agent never receives one (AG-11) |
| `rotate-key` | `joinedcontext-portal/src/api/service_accounts.rs` | `tests/ops_service_account_keys_tests.rs` | `ui/tests/service_accounts_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9a. a service account's API key is minted, rotated and revoked" | person only: a rotated key is a new credential shown once to a person, never to an agent (AG-11) |
| `revoke-key` | `joinedcontext-portal/src/api/service_accounts.rs` | `tests/edge_key_store_tests.rs` | `ui/tests/service_accounts_view.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9a. a service account's API key is minted, rotated and revoked" | `jc_service_account_key_revoke` |
| `retire` | `joinedcontext-portal/src/api/delete.rs` | `tests/resource_delete_tests.rs` | `ui/tests/resource_delete.test.tsx` | `ui/e2e/live/kind-serviceaccounts.spec.ts` › "ServiceAccount: created, changed and removed through the page by a person" | `jc_resource_delete` |
| `refused-no-permission` | `joinedcontext-portal/src/api/service_accounts.rs` | `tests/attack_person_only_operations_tests.rs` | `ui/tests/service_accounts_view.test.tsx` | `ui/e2e/live/kind-serviceaccounts.spec.ts` › "ServiceAccount: a viewer finds every write control disabled with its reason, and the door answers 403" | `jc_service_account_key_mint` |

### 3.18 Open data on CKAN (`ckan`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `connect-instance` | `joinedcontext-portal/src/api/resources.rs` | `tests/ckan_api_tests.rs` | `ui/tests/form_ckan_page.test.tsx` | `ui/e2e/live/kind-ckaninstances.spec.ts` › "CkanInstance: created, changed and removed through the page by a person" | `jc_resource_propose` |
| `status` | `joinedcontext-portal/src/api/resources.rs` | `tests/ckan_reconciler_tests.rs` | `ui/tests/ckan_view.test.tsx` | `ui/e2e/live/ckan.spec.ts` › "ckan/status: a steward reads each catalogue and each published endpoint the status names" | `jc_ckan_status` |
| `publish-dataset` | `joinedcontext-portal/src/agents/endpoints.rs` | `tests/ckan_reconciler_tests.rs` | `ui/tests/endpoint_open_data.test.tsx` | owed: T-2726 | owed: T-2726 |
| `refused-no-permission` | `joinedcontext-portal/src/permissions.rs` | `tests/ckan_api_tests.rs` | `ui/tests/ckan_view.test.tsx` | `ui/e2e/live/kind-ckaninstances.spec.ts` › "CkanInstance: a viewer finds every write control disabled with its reason, and the door answers 403" | `jc_resource_propose` |

### 3.19 Apps (`app`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `build-by-conversation` | `joinedcontext-portal/src/agents/oneshot/mod.rs` | `tests/agent_runs_tests.rs` | `ui/tests/app_generator.test.tsx` | `ui/e2e/live/app-generated-full.spec.ts` › "a prompt becomes a React + functions application that opens, reads and answers on dev" | `jc_run_create` |
| `answer-question` | `joinedcontext-portal/src/api/agent_runs.rs` | `tests/ops_runs_tests.rs` | `ui/tests/question_options.test.tsx` | `ui/e2e/live/readiness-app.spec.ts` › "the assistant's Build an app path makes an app that opens in the Portal and on its own, behind a login" | person only: the run asks the person, and an agent answering its own question would decide for them (AG-11) |
| `message` | `joinedcontext-portal/src/api/agent_runs.rs` | `tests/edge_run_writes_tests.rs` | `ui/tests/conversation_panel.test.tsx` | `ui/e2e/live/app-generated-full.spec.ts` › "a prompt becomes a React + functions application that opens, reads and answers on dev" | `jc_run_message` |
| `preview` | `joinedcontext-portal/src/agents/preview.rs` | `tests/edge_preview_apps_tests.rs` | `ui/tests/preview_bridge.test.ts` | `ui/e2e/live/build-samples.spec.ts` › "a build on helsinki-news reads its samples and the preview shows rows" | `jc_run_get` |
| `publish` | `joinedcontext-portal/src/api/agent_runs.rs` | `tests/app_build_tests.rs` | `ui/tests/part_run_publication.test.tsx` | `ui/e2e/live/app-generated-full.spec.ts` › "a prompt becomes a React + functions application that opens, reads and answers on dev" | `jc_run_publish` |
| `cancel` | `joinedcontext-portal/src/api/agent_runs.rs` | `tests/ops_runs_tests.rs` | `ui/tests/agent_run.test.tsx` | `ui/e2e/live/readiness-app.spec.ts` › "a person stops an app run the assistant started, and the run says it was stopped" | `jc_run_cancel` |
| `rebuild` | `joinedcontext-portal/src/apps/built.rs` | `tests/app_build_lane_tests.rs` | `ui/tests/app_build_panel.test.tsx` | `ui/e2e/live/apps-samples.spec.ts` › "each sample application is built from its own repository and the catalog says which commit" | person only: a person asks the forge to run the App's reviewed build.yml again; the assistant changes an application by a run, which the workflow builds on merge (AP-103) |
| `open-signed-in` | `joinedcontext-portal/src/apps/static_host.rs` | `tests/static_host_tests.rs` | `ui/tests/page_app_page.test.tsx` | `ui/e2e/live/apps-samples.spec.ts` › "the bikes application opens after the login with the stations of the space" | `jc_ui_navigate` |
| `write-through-form` | `joinedcontext-portal/src/apps/functions.rs` | `tests/apps_functions_tests.rs` | `ui/tests/app_form.test.tsx` | `ui/e2e/live/apps-fullstack.spec.ts` › "a steward adds, corrects and removes a station, and the viewer sees it" | person only: an App's form is used inside the App by a person signed in to it; the assistant prepares the same entity writes with `write_entities`, which the person applies (AG-78) |
| `refused-no-permission` | `joinedcontext-portal/src/apps/roles.rs` | `tests/attack_generated_app_tests.rs` | `ui/tests/app_roles_members.test.tsx` | `ui/e2e/live/apps-fullstack.spec.ts` › "a viewer reads the air-quality stations, gets no form and is refused a write" | `jc_run_publish` |
| `refused-preview-limit` | `joinedcontext-portal/src/ops/previews.rs` | `tests/edge_preview_start_tests.rs` | `ui/tests/agent_run.test.tsx` | `ui/e2e/live/preview-limit.spec.ts` › "the third preview on the node is refused, and the refusal names the two that hold the slots" | `jc_workspace_preview_start` |

### 3.20 Workspace copy and compare (`workspace`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `copy` | `joinedcontext-portal/src/store.rs` | `tests/workspace_api_tests.rs` | `ui/tests/form_work_on_copy_dialog.test.tsx` | `ui/e2e/live/copy-employee.spec.ts` › "an employee copies the project, edits in the copy, and brings it back as one change" | `jc_workspace_open` |
| `compare` | `joinedcontext-portal/src/plan.rs` | `tests/workspace_change_tests.rs` | `ui/e2e/workspaces.spec.ts` | `ui/e2e/live/copy-employee.spec.ts` › "an employee copies the project, edits in the copy, and brings it back as one change" | `jc_workspace_compare` |
| `update-from-main` | `joinedcontext-portal/src/plan.rs` | `tests/workspace_api_tests.rs` | `ui/tests/part_workspace_bar.test.tsx` | `ui/e2e/live/copy-lifecycle.spec.ts` › "the owner updates a copy from the project and discards it from the list" | `jc_workspace_update_from_main` |
| `preview` | `joinedcontext-portal/src/ops/previews.rs` | `tests/workspace_preview_tests.rs` | `ui/e2e/workspaces.spec.ts` | `ui/e2e/live/workspace-preview.spec.ts` › "a copy's preview answers on its own addresses and stops answering when stopped" | `jc_workspace_preview_start` |
| `stop-preview` | `joinedcontext-portal/src/ops/previews.rs` | `tests/ops_workspace_previews_tests.rs` | `ui/tests/page_try_it_page.test.tsx` | `ui/e2e/live/workspace-preview.spec.ts` › "a copy's preview answers on its own addresses and stops answering when stopped" | `jc_workspace_preview_stop` |
| `bring-back` | `joinedcontext-portal/src/plan.rs` | `tests/workspace_propose_tests.rs` | `ui/tests/page_bring_back_page.test.tsx` | `ui/e2e/live/copy-employee.spec.ts` › "an employee copies the project, edits in the copy, and brings it back as one change" | person only: bringing a copy back proposes every change of it at once and is left to a person (AG-11) |
| `discard` | `joinedcontext-portal/src/store.rs` | `tests/workspace_api_tests.rs` | `ui/e2e/workspaces.spec.ts` | `ui/e2e/live/copy-lifecycle.spec.ts` › "the owner updates a copy from the project and discards it from the list" | person only: throwing a copy away loses the work in it, and an agent never does (AG-11) |
| `refused-agent-way-out` | `joinedcontext-portal/src/ops/workspaces.rs` | `tests/workspace_bypass_tests.rs` | `ui/tests/workspaces_ui.test.tsx` | `ui/e2e/live/copy-agent.spec.ts` › "the assistant works in a copy and leaves both ways out to a person" | `jc_workspace_propose` |
| `refused-no-permission` | `joinedcontext-portal/src/ops/workspaces.rs` | `tests/workspace_security_tests.rs` | `ui/tests/page_workspaces_page.test.tsx` | `ui/e2e/live/copy-lifecycle.spec.ts` › "a viewer is refused a copy with the reason, and the API refuses the same" | `jc_workspace_open` |

### 3.21 Changes and approvals (`change`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `read` | `joinedcontext-portal/src/change.rs` | `tests/ops_changes_tests.rs` | `ui/tests/page_approvals_page.test.tsx` | `ui/e2e/live/assistant-reads.spec.ts` › "the assistant answers about changes and pipelines from the platform's own operations" | `jc_change_list` |
| `approve` | `joinedcontext-portal/src/change.rs` | `tests/changes_tests.rs` | `ui/tests/approval_actions.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "an administrator of the kind approves their own change, and the space is created" | person only: a person approves a change and an agent never does (AG-11, PF-58) |
| `reject` | `joinedcontext-portal/src/change.rs` | `tests/changes_tests.rs` | `ui/tests/approval_actions.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9c. a blueprint proposes a flow from its form, and the approver rejects it" | person only: rejecting decides a change as approving does, and only a person decides one (AG-11) |
| `drift-adopt` | `joinedcontext-portal/src/reconciler/drift.rs` | `tests/drift_api_tests.rs` | `ui/tests/drift_modal.test.tsx` | owed: T-2867 | person only: which side of a drift wins is a resolution a person picks, held to propose on Entity |
| `drift-revert` | `joinedcontext-portal/src/reconciler/drift.rs` | `tests/drift_api_tests.rs` | `ui/tests/drift_modal.test.tsx` | owed: T-2867 | person only: a revert writes the repository's entity into the live space at once, with no Change to approve, so a person picks it |
| `blueprint` | `joinedcontext-portal/src/plan.rs` | `tests/ops_flows_tests.rs` | `ui/tests/blueprint_wizard.test.tsx` | `ui/e2e/live/readiness.spec.ts` › "9c. a blueprint proposes a flow from its form, and the approver rejects it" | `jc_flow_start` |
| `refused-own-approval` | `joinedcontext-portal/src/change.rs` | `tests/auto_approve_tests.rs` | `ui/tests/approval_actions.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "a person who proposes and does not administer cannot approve their own change" | person only: the refusal is of a person's approval; an agent is refused every approval before that (AG-11) |
| `refused-agent-approval` | `joinedcontext-portal/src/ops/changes.rs` | `tests/attack_person_only_operations_tests.rs` | `ui/tests/assistant_permissions.test.tsx` | `ui/e2e/live/roles-refusals.spec.ts` › "the assistant never approves, however it is asked" | `jc_change_approve` |
| `refused-second-change` | `joinedcontext-portal/src/change.rs` | `tests/edge_change_lane_tests.rs` | `ui/tests/change_follow_card.test.tsx` | `ui/e2e/live/one-change-at-a-time.spec.ts` › "a second change on the same resource is refused by the name of the first, and lands once that one is decided" | `jc_resource_propose` |

### 3.22 Shared drafts (`draft`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `save` | `joinedcontext-portal/src/ops/drafts.rs` | `tests/drafts_tests.rs` | `ui/tests/draft_form.test.tsx` | `ui/e2e/live/drafts.spec.ts` › "drafts shared across windows: typing in window A syncs to window B, check verdict syncs, propose drops draft" | `jc_draft_put` |
| `drop` | `joinedcontext-portal/src/ops/drafts.rs` | `tests/ops_draft_writes_tests.rs` | `ui/tests/draft_elsewhere.test.tsx` | `ui/e2e/live/drafts.spec.ts` › "drafts shared across windows: typing in window A syncs to window B, check verdict syncs, propose drops draft" | `jc_draft_drop` |
| `refused-secret` | `joinedcontext-portal/src/ops/drafts.rs` | `tests/edge_delete_drafts_tests.rs` | `ui/tests/draft_form.test.tsx` | `ui/e2e/live/secrets.spec.ts` › "a secret written into the YAML view is refused by its field, and the value is never echoed" | `jc_draft_put` |

### 3.23 Assistant paths (`assistant`)

| step | unit | API | mocked UI | live journey | assistant |
|---|---|---|---|---|---|
| `open-and-ask` | `joinedcontext-portal/src/agents/oneshot/conversation.rs` | `tests/assistant_ask_tests.rs` | `ui/e2e/assistant_page.spec.ts` | `ui/e2e/live/assistant-page.spec.ts` › "a steward asks from the assistant page, gets an answer, and finds the conversation listed" | `jc_ask` |
| `integrate-pipeline` | `joinedcontext-portal/src/agents/oneshot/integrate.rs` | `tests/assistant_paths_tests.rs` | `ui/tests/assistant_capabilities.test.tsx` | `ui/e2e/live/assistant-paths.spec.ts` › "Integrate a pipeline from a CSV and its feed stays within its budgets (T-2695, T-2697)" | `jc_switch_path` |
| `open-a-form` | `joinedcontext-portal/src/agents/change.rs` | `tests/assistant_access_tests.rs` | `ui/tests/form_assistant_dock.test.tsx` | `ui/e2e/live/assistant-creates.spec.ts` › "the assistant opens the form for a data source, filled from one sentence" | `jc_ui_navigate` |
| `propose-endpoint` | `joinedcontext-portal/src/agents/share.rs` | `tests/assistant_share_tests.rs` | `ui/tests/assistant_endpoints.test.tsx` | `ui/e2e/live/share.spec.ts` › "an endpoint proposed and approved through the UI: Live, the hidden attribute absent, the viewer refused on the organization one" | `jc_endpoint_propose` |
| `refused-no-permission` | `joinedcontext-portal/src/agents/access.rs` | `tests/attack_assistant_tests.rs` | `ui/tests/assistant_permissions.test.tsx` | `ui/e2e/live/viewer-refused.spec.ts` › "a viewer is refused with a reason on every page, and at the door" | `jc_resource_propose` |

## 4. Routes

Every mutating operation of the Portal's OpenAPI document (`ui/openapi.json`), with the steps that send it. A route the table leaves out, or that no step claims and no `none:` explains, turns `gate_workflows` red.

| route | steps |
|---|---|
| `POST /api/v1/activity` | none: the browser's own activity log, sent as a side effect of every page and never a step a person takes |
| `POST /api/v1/auth/backchannel-logout` | `session/sign-out` |
| `POST /api/v1/auth/logout` | `session/sign-out` |
| `POST /api/v1/mcp` | none: the MCP door carries every registered operation, and each operation is claimed by the step whose tool it is |
| `POST /api/v1/organization/people` | `people/create` |
| `DELETE /api/v1/organization/people/{id}` | `people/remove` |
| `PATCH /api/v1/organization/people/{id}` | `people/edit` |
| `POST /api/v1/organization/people/{id}/disable` | `people/disable` |
| `POST /api/v1/organization/people/{id}/enable` | `people/enable` |
| `POST /api/v1/organization/people/{id}/remove-second-factor` | `people/remove-second-factor` |
| `POST /api/v1/organization/people/{id}/reset-password` | `people/reset-password` |
| `POST /api/v1/organization/people/{id}/sign-out` | `people/sign-out-everywhere` |
| `PUT /api/v1/preferences` | none: a person's own language, theme and last project, stored for them and never a workflow step |
| `POST /api/v1/projects` | `project/create` |
| `DELETE /api/v1/projects/{project}` | `project/retire` |
| `POST /api/v1/projects/{project}/agent-runs` | `app/build-by-conversation` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/answers` | `app/answer-question` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/cancel` | `app/cancel` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/functions/{fn}` | `app/preview` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/messages` | `app/message` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/preview-errors` | `app/preview` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/preview-observations` | `app/preview` |
| `POST /api/v1/projects/{project}/agent-runs/{id}/publish` | `app/publish` |
| `POST /api/v1/projects/{project}/apps/{name}/rebuild` | `app/rebuild` |
| `POST /api/v1/projects/{project}/assistant/conversations` | `assistant/open-and-ask` |
| `POST /api/v1/projects/{project}/assistant/propose-endpoint` | `assistant/propose-endpoint` |
| `POST /api/v1/projects/{project}/catalogue/drafts` | `ckan/publish-dataset` |
| `POST /api/v1/projects/{project}/changes/{id}/approve` | `change/approve`, `space/approve` |
| `POST /api/v1/projects/{project}/changes/{id}/reject` | `change/reject` |
| `POST /api/v1/projects/{project}/datamodels/{name}/share` | `datamodel/share-with-organization` |
| `PUT /api/v1/projects/{project}/datamodels/{name}/source` | `datamodel/edit-source`, `datamodel/add-class-enum-relation` |
| `PUT /api/v1/projects/{project}/drafts/{kind}/{name}` | `draft/save` |
| `DELETE /api/v1/projects/{project}/drafts/{kind}/{name}` | `draft/drop` |
| `POST /api/v1/projects/{project}/drift/{space}/{id}/adopt` | `change/drift-adopt` |
| `POST /api/v1/projects/{project}/drift/{space}/{id}/revert` | `change/drift-revert` |
| `POST /api/v1/projects/{project}/duplicate` | `project/copy` |
| `POST /api/v1/projects/{project}/flows` | `change/blueprint` |
| `POST /api/v1/projects/{project}/import` | `import/upload`, `import/from-git` |
| `POST /api/v1/projects/{project}/ops/{name}` | none: the registry's door runs every operation by name, and each operation is claimed by the step whose tool it is |
| `POST /api/v1/projects/{project}/pipelines/test` | `pipeline/test` |
| `POST /api/v1/projects/{project}/pipelines/{name}/rejected/retry` | `pipeline/retry-rejected` |
| `POST /api/v1/projects/{project}/serviceaccounts/{name}/keys` | `serviceaccount/mint-key` |
| `DELETE /api/v1/projects/{project}/serviceaccounts/{name}/keys/{keyId}` | `serviceaccount/revoke-key` |
| `POST /api/v1/projects/{project}/serviceaccounts/{name}/keys/{keyId}/rotate` | `serviceaccount/rotate-key` |
| `POST /api/v1/projects/{project}/syncsources/{name}/detach` | `syncsource/detach` |
| `POST /api/v1/projects/{project}/syncsources/{name}/pause` | `syncsource/pause` |
| `POST /api/v1/projects/{project}/syncsources/{name}/sync` | `syncsource/sync-now` |
| `POST /api/v1/projects/{project}/workspaces` | `workspace/copy` |
| `DELETE /api/v1/projects/{project}/workspaces/{name}` | `workspace/discard` |
| `POST /api/v1/projects/{project}/workspaces/{name}/preview` | `workspace/preview` |
| `DELETE /api/v1/projects/{project}/workspaces/{name}/preview` | `workspace/stop-preview` |
| `POST /api/v1/projects/{project}/workspaces/{name}/propose` | `workspace/bring-back` |
| `POST /api/v1/projects/{project}/workspaces/{name}/update` | `workspace/update-from-main` |
| `POST /api/v1/projects/{project}/{plural}` | `space/create`, `datasource/create`, `pipeline/create`, `endpoint/create`, `policy/create`, `subscription/create`, `syncsource/create`, `dashboard/create`, `dashboard/layer`, `sharing/share-space`, `sharing/register-source`, `serviceaccount/create`, `ckan/connect-instance`, `groups/create`, `groups/grant-role` |
| `PUT /api/v1/projects/{project}/{plural}/{name}` | `space/edit`, `datasource/edit`, `pipeline/edit`, `endpoint/edit`, `policy/edit`, `groups/edit`, `organization/edit-settings` |
| `DELETE /api/v1/projects/{project}/{plural}/{name}` | `space/retire`, `datamodel/retire`, `datasource/retire`, `pipeline/retire`, `endpoint/retire`, `policy/retire`, `subscription/retire`, `syncsource/retire`, `dashboard/retire`, `serviceaccount/retire`, `groups/retire` |
| `PATCH /api/v1/projects/{project}/{plural}/{name}` | `space/edit`, `endpoint/edit` |
| `POST /api/v1/tools/generate` | `datamodel/validate` |
| `POST /api/v1/tools/import-sdm` | `datamodel/import-smart-data-model` |
| `POST /api/v1/tools/infer-schema` | `datamodel/infer-from-sample` |
| `POST /api/v1/webhooks/gitea` | none: Gitea calls it with its signature after a push to a project repository; no person or agent sends it |
| `POST /api/v1/webhooks/sync/{project}/{name}` | `syncsource/webhook` |

## 5. What is owed

The owed cells name open tasks, and `gate_workflows` holds their count: it may shrink and never grow.

- **T-2849**: the CKAN journeys, mocked and live, once T-2726 rebuilds the page.
- **T-2732**: assistant tools for people, organization settings, project copy, a pipeline's rejected rows, an app rebuild and write, and drift.
- **T-2867**: drift adopt and revert, once a page mounts the drift modal and dev holds a seed that can drift.
- **T-2726**: the one-step Publish dataset from an endpoint, its live journey and its tool.
- **T-2885**: the live share of a project model with the organization, walked with the export and import round trip of the models a project uses (DM-77, MF-49, MF-50).

## 6. Assistant evals

The assistant cell names the tool; the evals show the assistant reaches for it when a person asks in words (TS-26, T-2733). Each workflow of §3 has one conversation in `tests/assistant_evals/<workflow>.yaml` of `joinedcontext-portal`:

- `says`: the steward's message, then the answers to the questions the run asks, in order.
- `expect.calls`: the tools the run calls, each with the fields its input must carry. A change opens the kind's draft with `change_resource` and the person proposes it (AG-77); a kind with its own create form is opened with `jc_ui_navigate`.
- `expect.outcome`: `change`, `form`, `answer`, or `person-only` with `why`.
- `refusal`: what a viewer asks; a viewer may not propose an App, so the conversation itself answers 403 (AG-70).

The nightly batch runs `ui/e2e/live/assistant-evals.spec.ts` on `dev` with the real model and real logins: at most 10 conversations a night, the never recorded first, announced in `AI_shared_folder.md`, drafts named `eval-…` removed after. A run that makes every expected call is written to `tests/assistant_evals/recordings/<workflow>.json`: its events, without what the tools answered. `tests/assistant_evals_tests.rs` rebuilds the model's answers from those events and plays them against every build, with no spend, and fails when a workflow has no conversation, when a recording shows a call that failed on `dev`, or when the build no longer makes the call. A recording is refreshed by a live run, never written by hand; the count of workflows still unrecorded may only fall.

## Related

- [00-strategy.md](00-strategy.md) — the lanes these layers run in.
- [03-frontend-and-e2e-tests.md](03-frontend-and-e2e-tests.md) — the mocked and live Playwright suites the matrix names.
- [06-security-tests.md](06-security-tests.md) — the attack register behind the refusal rows.
- [testing.md](../Requirements/testing.md) — TS-26, the rule this page makes checkable.
- [agents.md](../Requirements/agents.md) — AG-11 and AG-77, which decide what only a person may do.
