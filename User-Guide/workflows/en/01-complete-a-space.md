---
sidebar_position: 1
title: Complete a space from a sample file
description: Give the Portal one sample file and let it draft the model, the space and what reads them.
---

# Complete a space from a sample file

You have a CSV or JSON file and want its data in the platform. This page walks you from the file to a proposed change in about a minute. It is for data stewards.

## 1. Name the space and add the file

Open **Context Spaces** in the project and choose **Complete this space**. Type a **Space name**, then drop your file on **Files** or browse for it.

![The Complete this space page with a space name typed and a CSV file added](../../img/en/space-1-name-and-file.png)

## 2. Read the drafts

Click **Complete**. The Portal reads the file and drafts what the space needs: a data model with one attribute per column, the context space itself, and, when the file allows it, a data source, a pipeline, an endpoint and a map layer. Each draft says what it is and whether its check passed. **Open** shows a draft in full before you send it.

![The drafts the Portal made from the file: a data model and a context space, each with its check](../../img/en/space-2-drafts.png)

## 3. Propose all

Click **Propose all**. The drafts travel together as one change, and nothing is created until a second person approves it in **Approvals**.

![The change proposed, waiting for approval](../../img/en/space-3-proposed.png)

## Related

- [Approve a change](09-approve-a-change.md) — what the approver sees next.
- [Organizations, projects and spaces](../../02-organizations-projects-spaces.md) — what a space holds and who may read it.
- [Build a data model](02-build-a-data-model.md) — when you want to shape the model by hand instead.
