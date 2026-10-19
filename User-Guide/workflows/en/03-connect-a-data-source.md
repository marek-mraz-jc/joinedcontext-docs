---
sidebar_position: 3
title: Connect a data source
description: Start from a template, give the source's address and see its first records before you save anything.
---

# Connect a data source

A data source is where a pipeline reads from: a CSV file at an address, a REST API, a CKAN dataset, a WFS layer or a GTFS Realtime feed. This page connects one and proves it answers. It is for data stewards and integration engineers.

## 1. Pick a template

Open **Data sources** and click **New data source**. Under **Start from a template**, pick the kind of source you have.

![The data source templates: CSV file, REST API, CKAN dataset, WFS layer and GTFS Realtime](../../img/en/datasource-1-templates.png)

## 2. Give the address

Paste the source's address and give the data source a **Name**. A WFS source also asks for the **Layer name**.

![The template filled with a CSV address and a name](../../img/en/datasource-2-address.png)

## 3. Read the first records

Click **Fill the form and check**. The Portal fills the form from the template and reads the source once, so you see how many records it returned and what they look like before you propose it.

![The first records the source returned](../../img/en/datasource-3-first-records.png)

## Related

- [Pipelines and ingestion](../../04-pipelines.md#2-connecting-an-external-data-source) — every source kind and its options.
- [Build a pipeline](04-build-a-pipeline.md) — read the source into a space.
