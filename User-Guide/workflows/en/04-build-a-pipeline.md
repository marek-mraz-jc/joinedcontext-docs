---
sidebar_position: 4
title: Build a pipeline
description: Pick a source and a target, write the mapping, and fix it until every record is valid.
---

# Build a pipeline

A pipeline reads a data source and writes its records into a context space, checked against the space's model. The workbench shows each step with real records, so you see a wrong field before anything runs. It is for data stewards and integration engineers.

## 1. Pick the source

Open **Pipelines** and click **New pipeline**. Pick the data source under **Source**. The **Sample** shows the records as the pipeline will read them.

![The pipeline workbench with a source picked and its sample records](../../img/en/pipeline-1-source-and-sample.png)

## 2. Pick the target

Give the pipeline a **Name** and pick the **Target**: the space the records land in, and the model they are checked against. **Mapping** then lists what that model takes.

![The target picked, and the mapping step listing what the model takes](../../img/en/pipeline-2-target-and-mapping.png)

## 3. Read the errors at each record

Write the mapping. **Mapped output** shows each record as it would be written, and a field the model refuses is marked at that record with the rule it breaks. **Validation** counts the records that break the model, and the propose button stays disabled while any do.

![A mapping with a field of the wrong type, the error shown at each record](../../img/en/pipeline-3-errors-at-each-record.png)

## 4. Fix it until all records are valid

Correct the mapping. When **Validation** says every record is valid, propose the pipeline. It runs after a second person approves it.

![Every record valid against the model](../../img/en/pipeline-4-all-valid.png)

## Related

- [Pipelines and ingestion](../../04-pipelines.md) — schedules, presets and stream health.
- [Connect a data source](03-connect-a-data-source.md) — the step before this one.
- [Share data through an endpoint](05-share-through-an-endpoint.md) — let others read what the pipeline wrote.
