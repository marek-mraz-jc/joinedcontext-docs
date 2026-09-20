---
sidebar_position: 6
title: "Blueprint Authoring Guide"
---

# Blueprint Authoring Guide

Blueprints are parameterized templates that expand into concrete manifests. They are the only
authoring surface regular users see: a form, not YAML (CC-23). This guide is for the platform
engineers who write them.

## 1. One blueprint, one file

A blueprint lives at `blueprints/{name}/blueprint.yaml` and is an ordinary manifest, so it is
reviewed, versioned and validated like everything else in the repository. The parameter schema
and the templates are part of it: a blueprint version pins one file, and the Portal serves the
form from the same object the reconciler expands (CC-24, CC-26).

```yaml excerpt title="blueprints/threshold-alert/blueprint.yaml (metadata)"
apiVersion: joinedcontext.com/v1alpha1
kind: Blueprint
metadata:
  name: threshold-alert
  namespace: org
  title:
    en: "Threshold Alert Subscription"
    fi: "Raja-arvon ylitysilmoitus"
  description:
    en: "Watches a property and calls a webhook when it crosses a limit"
    fi: "Seuraa ominaisuutta ja kutsuu webhookia raja-arvon ylittyessä"
spec:
  version: 1.2.0
  category: alerting
  riskClass: green # green (auto-merge), yellow (domain review), red (admin review)
  allowedRoles:
    - domain-editor
    - approver
    - org-admin
```

`riskClass` and `allowedRoles` are what the gallery filters on and what CI re-validates on
every merge request, whether the change came from the Portal or from a hand-written branch
(CC-59, CC-63).

## 2. Parameter schema

`spec.parameterSchema` is JSON Schema draft-07 and is the complete user-facing surface: a
parameter set that validates MUST always render valid manifests (CC-24). Titles and
descriptions are what the generated form shows, so write them for the person filling it in.

```yaml excerpt title="blueprints/threshold-alert/blueprint.yaml (spec.parameterSchema)"
apiVersion: joinedcontext.com/v1alpha1
kind: Blueprint
metadata:
  name: threshold-alert
spec:
  parameterSchema:
    type: object
    required: [entityType, observedProperty, thresholdValue, webhookUrl]
    properties:
      entityType:
        type: string
        title: "Target entity type"
        enum: [AirQualityObserved, NoiseLevelObserved, TrafficFlowObserved]
      observedProperty:
        type: string
        title: "Property name"
        default: airQualityIndex
      thresholdValue:
        type: number
        title: "Alert threshold"
      webhookUrl:
        type: string
        format: uri
        title: "Notification target URL"
```

A parameter never carries a secret. Take the *name* of a secret instead and let the manifest
reference it (`secretRef`); values live in the secret store (CC-06). The Portal has a widget for
exactly that shape, so name it and the form asks for a name, a key and an environment variable
instead of offering a box somebody types a password into:

```yaml excerpt title="a parameter that points at a secret"
      apiToken:
        type: object
        title: "API token"
        x-jc-widget: secretRef
```

### 2.1 Choices the platform already knows (CC-24)

An `enum` is a fixed list, written when the blueprint was written. For a choice the platform
itself holds — a Context Space, an Endpoint, a sensor — name a picker instead, and the form
fills the list in when someone opens it:

```yaml excerpt title="blueprints/threshold-alert/blueprint.yaml (a picker)"
apiVersion: joinedcontext.com/v1alpha1
kind: Blueprint
metadata:
  name: threshold-alert
spec:
  parameterSchema:
    type: object
    properties:
      space:
        type: string
        title: "Context space"
        x-jc-widget: resourcePicker
        x-jc-options:
          plural: spaces
      sensor:
        type: string
        title: "Sensor"
        x-jc-widget: entityPicker
        x-jc-options:
          space: ovzdusie
          entityType: AirQualityObserved
```

Four widgets are registered, in `ui/src/components/forms/widgets/index.ts`. Two of them are
pickers: `resourcePicker` lists the project's manifests of one kind, by the plural segment of
`/api/v1/projects/{project}/{plural}`, and submits the chosen name; `entityPicker` searches a
space through the gateway and submits the chosen entity's id, and needs `space` and
`entityType`, which the blueprint's author writes as literals, because the form resolves no
hint from another field. The other two shape a value the platform has a form for: `secretRef`
asks for the name, key and environment variable of a secret, and `operations` offers the NGSI-LD
operation groups as checkboxes instead of a free-text list.

The widget name has to be one of those four; an unknown one leaves the parameter with its
default input rather than breaking the form. A picker is a convenience, not a control:
both lists come back narrowed to what the caller may read, and the value is validated against
the same schema on the server, where the decision is made (CC-60).

## 3. Templates

Each entry of `spec.templates` renders exactly one manifest. Templates are
[minijinja](https://docs.rs/minijinja) (Jinja2) in a sandbox: no filesystem, no environment,
no host access, and an undefined variable is an error rather than an empty string
(ADR-N-005).

```yaml excerpt title="blueprints/threshold-alert/blueprint.yaml (spec.templates)"
apiVersion: joinedcontext.com/v1alpha1
kind: Blueprint
metadata:
  name: threshold-alert
spec:
  templates:
    - name: subscription
      template: |
        apiVersion: joinedcontext.com/v1alpha1
        kind: Subscription
        metadata:
          name: "alert-{{ entityType | lower }}-{{ observedProperty }}"
        spec:
          description: "Automated alert for {{ entityType }}"
          entities:
            - type: "{{ entityType }}"
          q: "{{ observedProperty }} > {{ thresholdValue }}"
          notification:
            endpoint:
              uri: "{{ webhookUrl }}"
              accept: application/json
```

The `name` of a template is stable: it names the rendered file and appears in diagnostics, so
renaming one is a change to the blueprint, not a cosmetic edit.

## 4. What expansion produces

`jcctl` validates the parameters, renders every template and writes the manifests into the
repository — expansion happens at authoring time, never at apply time, so review and audit
always see the concrete resources (CC-25). Each rendered manifest carries its provenance, and
the Portal re-opens any flow as the form that created it (CC-27, CC-32):

```yaml
metadata:
  annotations:
    joinedcontext.com/blueprint: threshold-alert
    joinedcontext.com/blueprint-version: 1.2.0
    joinedcontext.com/blueprint-parameters: '{"entityType":"AirQualityObserved","observedProperty":"airQualityIndex","thresholdValue":50,"webhookUrl":"https://example.org/hook"}'
```

The parameter annotation is canonical JSON with sorted keys. Same blueprint version, same
parameters, byte-identical output — that is what makes a re-render a reviewable diff instead
of noise.

## Related

- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
- [city-as-code (CC-23…CC-28, CC-59)](../Requirements/city-as-code.md) — the blueprint requirements this guide implements.
