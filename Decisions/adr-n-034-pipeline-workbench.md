---
sidebar_position: 35
title: "ADR-N-034: One Pipeline Workbench, and Only Validated Records Are Written"
---

# ADR-N-034: One Pipeline Workbench, and Only Validated Records Are Written

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner (direction of 2026-09-24)

## 1. Context

The owner's direction of 2026-09-24: pipelines "are cluttered, have too many options and no hints". A person, the AI agent and the assistant should take the same way: "pick a data source, see the output, write a mapping, see the output of the mapping, errors, everything, proper logs, and where it is saved, which context space; validated against LinkML/schema/RDF/SHACL, so only validated data is updated/created".

Today the Portal has three pages for one job (`PipelineStudio`, `PipelineEditor`, `PipelineTest`). The pipeline test (PL-43) checks a mapped record only for an `id` and a `type`, not against the target space's model. The runner writes whatever the mapping produced, and the gateway drops a whole batch on a `400` (T-1465). A record that breaks the model is either stored or lost without a trace, and a pipeline's page shows counters but no log.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | The runner validates with Bento's own `json_schema` processor; the schema is the one Model Tools renders from the LinkML (DM-43). |
| Technological consistency | **Full** | One validator in the Portal, one rendered schema in the runner, one operation per step for every actor (ADR-N-021). |
| Security by design | **Full** | A record that breaks the model never reaches the broker; samples and logs pass the same read guard as the run and never carry a secret. |
| Modular design | **Full** | Each step is an operation with its own input and output, testable alone. |
| Multi-tenancy | **Full** | A rejected list and a log belong to one pipeline and are read with read on that pipeline. |

## 3. Decision

1. **One workbench, six steps in order.** The Portal replaces the three pipeline pages with one workbench:
   1. **Source.** Pick a DataSource or an Endpoint (UI-84).
   2. **Sample.** See its raw output: the first records, their fields and the counts.
   3. **Mapping.** Write the Bloblang mapping, with a hint per target slot: its type, whether it is required, its enum values and an example.
   4. **Mapped output.** See each record as it would be written, with every error at its record and field.
   5. **Validation.** See a verdict per record against the target space's model.
   6. **Target and save.** See the target Context Space named. Save proposes the Change.

   Each step shows a one-line hint. The schedule, batching and retries sit behind "More options" with safe defaults.
2. **What "valid" means.** A record is valid when it is an NGSI-LD entity of a class the space's one model declares (DM-61), whose id follows the id rule (PF-42), and whose attributes satisfy the model's shape: no attribute the class does not declare unless the model is open (`sh:closed`), each required attribute present (`sh:minCount`), a single value where the slot is not multivalued (`sh:maxCount`), each value of its datatype (`sh:datatype`), within its enum (`sh:in`) and of its NGSI-LD attribute kind. Model Tools renders these constraints from one LinkML source twice (DM-43): as the SHACL shapes an RDF consumer reads, and as the JSON Schema the Portal compiles into a schema of the normalized entity. A rejected record names the constraint it broke by its SHACL component and its path, so a person and an RDF consumer read the same rule.
3. **Only valid records are written.** The reconciler renders a validation stage before the output of every pipeline whose target space has a model, from that model's artifacts at the version the space pins. An invalid record is not written: it goes to the pipeline's rejected list with the record, the rule it broke and the time. The gateway refuses a type the model does not declare again (DM-61), as defence in depth.
4. **Runs and a log per run.** The runner sends one outcome line per record to the Portal (pipeline, run, record id, step, outcome, message) beside its data output, through a sink that is dropped rather than retried when the Portal does not answer, so a log never holds back a write. A run is one tick of the pipeline's clock; for a source that never ends (MQTT, a socket, a broker) it is one UTC hour. The pipeline's page lists its runs with their counts and each run's log.
5. **The same steps for every actor.** Each step is an operation of the registry (ADR-N-021): `jc_pipeline_sample_source`, `jc_pipeline_try_mapping`, `jc_pipeline_validate` and `jc_pipeline_propose`. The workbench, the API, MCP and the assistant call the same code and see the same outputs.

## 4. Alternatives Considered

- **Validate in the gateway only.** The gateway answers a batch as one request and cannot keep the record that failed; the pipeline would lose it. The gateway keeps its type check as the second line.
- **Run a SHACL engine in the runner.** Bento has no RDF engine, and the constraints LinkML renders into SHACL are the ones its JSON Schema carries. One source, two renderings, one verdict.
- **Read the runner's pod log.** The Portal would need `pods/log` in the runner's namespace, which is every pipeline's output and whatever a workload printed (T-1129). An outcome sink carries only what the platform wrote about a record.

## 5. Consequences

- PL-43 extends: its `validation` checks the model's shape, not only the id. PL-58…PL-63 are new.
- A pipeline whose records break its space's model stops writing them the day the stage renders. The rejected list and "Retry after fix" are how a steward sees and recovers them.
- Work: T-2707…T-2712.

## Related

- [Requirements/pipelines](../Requirements/pipelines.md) — PL-43 and PL-58…PL-63.
- [ADR-N-033](adr-n-033-one-data-model-per-space.md) — the one model a pipeline validates against.
- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) — why each step is an operation.
- [Architecture/08-pipelines](../Architecture/08-pipelines.md#8-the-workbench-validation-and-the-log) — how the stage and the sink are rendered.
