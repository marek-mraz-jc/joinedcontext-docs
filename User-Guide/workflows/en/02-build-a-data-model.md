---
sidebar_position: 2
title: Build a data model
description: Add classes, a list of allowed values and a relationship, check the model and propose it.
---

# Build a data model

A data model says which types of things a space holds and what each one carries. This page builds one by hand: two classes, a list of allowed values, and a one-to-many relationship. It is for data stewards and modellers.

## 1. Add classes and a relationship

Open **Data models** and choose **New blank model**. Give it a **Name** and pick the **Space** it belongs to. Add each class with **Add class**. For a list of allowed values, type it into the enum field and click **Add enum**, then add its values. Select a class to give it attributes with **Add slot**, and pick each attribute's **Range**. To link two classes, choose **One to many**, pick the **Target class** and click **Add relationship**; the **Relationships** table shows both ends.

![The model editor with two classes, an enum and a one-to-many relationship](../../img/en/model-1-classes-and-relationship.png)

## 2. Check it

Anything the form has no control for, you write on the **Source** tab. Click **Check**: the Portal validates the whole model and tells you the version it will save as.

![The model checked, with the version it saves as](../../img/en/model-2-checked.png)

## 3. Save and propose

Click **Save model**. The model goes to **Approvals** as a proposed change; it is used only once someone approves it.

![The model proposed as a change](../../img/en/model-3-proposed.png)

## Related

- [Data models](../../03-data-models.md) — attributes, ranges and versions in full.
- [Build a pipeline](04-build-a-pipeline.md) — fill the model with data.
