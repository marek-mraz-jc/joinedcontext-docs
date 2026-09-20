---
sidebar_position: 24
title: "ADR-N-023: A Pipeline Is Bento's Own Shape: Sources, Steps, Outputs"
---

# ADR-N-023: A Pipeline Is Bento's Own Shape: Sources, Steps, Outputs

Date: 2026-09-18  
Status: Accepted  
Decision Makers: product owner

## 1. Context

The owner asked for a pipeline studio that reads like Node-RED or NiFi: a palette of processors, steps inserted between the nodes, and two inputs merged into one flow (T-1126, T-1127, T-1128, T-1130). The `Pipeline` kind could not carry any of it. `PipelineSpec` held one `source`, one `compute` and one `output`, the studio drew exactly those three nodes, and there was no second input to merge, no place to insert a step and no per-node identity to paint or to show YAML for (T-1208).

Two shapes were on the table. The first kept one source, one compute and one output, and merged two feeds by running two pipelines into the same endpoint. The second stored a free-form graph with nodes and edges, the Node-RED shape. The owner chose neither: the kind takes the shape Bento itself runs. One Bento stream is always inputs, then an ordered list of processors, then outputs. Several inputs merge through the `broker` input. `branch`, `switch` and `workflow` give branching inside a processor, and the `broker` and `switch` outputs fan out. Everything the studio needs is in that shape, and none of it needs edges.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | The manifest mirrors the Bento stream the runner executes; the renderer maps lists to lists and adds no graph engine. |
| Technological consistency | **Full** | Bento stays the only pipeline runtime (ADR-N-006); the processors are the ones the pinned runner image ships. |
| Security by design | **Full** | Every source is read through its own Endpoint and every output is written through its own Endpoint and Policy (PL-18…PL-20); a merge does not let one source's credential reach another. |
| Modular design | **Full** | A step is one processor; adding a capability is naming a processor the runner already has. |
| Multi-tenancy | **Full** | Unchanged: the pipeline's ServiceAccount and the Endpoints it names are the grant (PF-39). |

## 3. Decision

1. **The shape.** A `Pipeline` at `joinedcontext.com/v1alpha2` carries `spec.sources` (one or more), `spec.steps` (an ordered list, possibly empty) and `spec.outputs` (one or more). A source is what `spec.source` was: a `dataSourceRef`, or an `endpointRef` with a `query` or a `trigger`. A step is one processor: a compute kind of PL-33, or a processor the pinned runner image ships, with its configuration verbatim. An output is a `targetEndpoint` with its write `mode`. Order is the list order; no edges are stored (PL-52).
2. **Rendering.** One source renders as its input and several as a Bento `broker` input over them. The steps render as `pipeline.processors` in order. One output renders as its output and several as a `broker` output with `pattern: fan_out` (PL-53).
3. **Branching stays inside a step.** `branch`, `switch` and `workflow` are processors like any other, so a conditional path is a step whose configuration holds it. The studio draws the lane left to right with steps inserted between nodes, and never free wiring (PL-56).
4. **Only Pipeline changes version.** The envelope accepts `joinedcontext.com/v1alpha2` for `Pipeline` alone; every other kind stays at `v1alpha1`. jc-core reads a `v1alpha1` Pipeline as the `v1alpha2` one it means: `sources: [source]`, `steps: [compute]`, `outputs: [{ targetEndpoint, mode }]`. The stream rendered from either is the same, byte for byte, and the golden files of the reconciler prove it (PL-54).
5. **Migration by editing.** A `v1alpha1` Pipeline keeps running unchanged. The Portal writes `v1alpha2` whenever a pipeline is created or edited, so a pipeline migrates in the Change a person approves anyway. No bulk rewrite of the repositories happens.
6. **The guard applies per source and per output.** Admission checks the pipeline's ServiceAccount against each source's Endpoint for the read and each output's Endpoint for the write. Each source's secrets are injected under its own names, and a `container` step stays the only step of a `scheduled` pipeline, because it runs as a Job and not inside a Bento stream (PL-55).

## 4. Consequences

- T-1126, T-1127, T-1128 and T-1130 become buildable: the merge is two sources, the palette inserts steps, each node has its own block to show as YAML, and the trace paints a step by its processor index.
- The envelope check becomes per kind. A second version of another kind later follows the same rule: read the old one as the new one, write the new one on edit.
- A reader of a `v1alpha1` Pipeline in Git still understands it; the Portal shows it in the new lane without changing the file until someone edits it.

## Related

- [Requirements/pipelines.md](../Requirements/pipelines.md) — PL-52…PL-56.
- [Architecture/08-pipelines.md](../Architecture/08-pipelines.md) — §3, sources, steps and outputs.
- [ADR-N-006](adr-n-006-bento-pipelines-supersede-nifi.md) — Bento as the pipeline runtime.
