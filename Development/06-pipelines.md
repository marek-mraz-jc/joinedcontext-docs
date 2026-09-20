---
sidebar_position: 7
title: "Bento Pipelines Guide"
---

# Bento Pipelines Guide

Pipelines ingest data from external systems, normalize payloads to standard data models, and publish updates to Context Spaces. The platform uses **Bento** (`warpstreamlabs/bento`, MIT license).

## 1. Pipeline Manifest Envelope

Pipelines are stored as native Bento configurations wrapped in a platform metadata envelope:

```yaml title="projects/mobility/pipelines/parking-mqtt/pipeline.yaml"
kind: Pipeline
apiVersion: joinedcontext.com/v1alpha1
metadata:
  name: parking-mqtt-ingest
  namespace: banskabystrica
  title:
    en: "Parking MQTT Telemetry Feed"
spec:
  class: resident # 'resident' (streams mode) or 'scheduled' (CronJob)
  enabled: true   # optional; false pauses the pipeline without deleting it (PL-40)
  targetEndpoint: urn:ngsi-ld:Endpoint:hel.fi:mobility-live:ep-parking # writes go through an Endpoint, never straight into a space (PL-02, PL-18)
  secretRefs:
    - name: parking-broker-credentials
      key: mqtt_password
```

The accompanying `bento.yaml` sits alongside the envelope, unwrapped and standard:

```yaml title="projects/mobility/pipelines/parking-mqtt/bento.yaml"
input:
  mqtt:
    urls: ["tcp://mqtt.external.example.com:1883"]
    topics: ["parking/+/status"]
    client_id: "joinedcontext-bento-runner"
    user: "city-ingest"
    password: "${PARKING_BROKER_CREDENTIALS_MQTT_PASSWORD}"

pipeline:
  processors:
    - mapping: |
        let domain = env("JC_ORG_DOMAIN")   # injected by the reconciler (PF-44, Architecture/03 section 3)
        root.id = "urn:ngsi-ld:%v:%v:%v:%v".format("ParkingSpot", $domain, "parking", this.spot_id)
        root.type = "ParkingSpot"
        root.status = {
          "type": "Property",
          "value": if this.occupied { "occupied" } else { "free" }
        }
        root.observedAt = {
          "type": "Property",
          "value": now()
        }

output:
  http_client:
    url: "http://context-gateway:8080/cs/mobility-live/ngsi-ld/v1/entities"
    verb: "POST"
    headers:
      Content-Type: "application/ld+json"
```

## 2. Using a LinkML-Map Mapping

Keep the pipeline's Bloblang to the last mile and let a `kind: Mapping` produce the target entity (DM-33…DM-42, PL-29):

```yaml title="projects/mobility/pipelines/parking-mqtt/pipeline.yaml"
spec:
  class: resident
  mappingRef: { kind: Mapping, name: vendorx-parking-to-parkingspot }
```

```yaml title="projects/mobility/pipelines/parking-mqtt/bento.yaml"
pipeline:
  processors:
    - mapping: |                       # last mile only: unpack the vendor frame
        root = this.payload.parse_json()
        root.receivedAt = now()
    # the reconciler appends: - mapping: <generated/vendorx-parking-to-parkingspot.blobl>
```

The compiler is Model Tools, not `jcctl`: `src/compile_bloblang.py` and `src/compile_mapping_ir.py` in `joinedcontext-platform/tools/model-tools` turn a `kind: Mapping` into Bloblang and the gateway IR, and the reconciler runs them. (`jcctl model` has three verbs, `generate`, `diff` and `validate`, plus `import` and `infer`; there is no `compile-mapping`.) `bento test` runs the Mapping's golden tests against the compiled output.

## 2a. Derived pipelines (entities in, entities out)

Set `spec.source` (endpoint read grant plus a `query` or a `trigger.subscription`) and `spec.compute` (`bloblang`, `mapping`, `wasm`, `container`); the reconciler renders the Bento input and processor. A `bloblang` step keeps its mapping in the manifest as `spec.compute.bloblang: |` (rendered as the last `mapping` processor, PL-41), which is what the Portal's pipeline editor edits; leave the field out to keep the mapping in `bento.yaml` instead. `source.query.ids` pins the read to a list of entity URNs (PL-42); the Portal's pipeline studio fills it from the rows you tick in a live sample. For `wasm`, put a Rust crate in `compute/` beside `pipeline.yaml` exporting one `process` function over a JSON message; CI builds it for `wasm32-wasip1`, runs `cargo test`, then the golden tests below. Details and an example in [Architecture/08 §3](../Architecture/08-pipelines.md#derived-pipelines-entities-in-entities-out).

## 3. Linting & Golden Output Testing

Every pipeline must pass syntax validation and deterministic output testing before merging to main:

```bash
# Lint pipeline configuration syntax
bento lint ./projects/mobility/pipelines/parking-mqtt/bento.yaml

# Execute golden-file test asserting input mocks produce expected NGSI-LD
bento test ./projects/mobility/pipelines/parking-mqtt/...
```

Bento pairs a test definition with the configuration of the same name in the same folder, so
the tests for `bento.yaml` live in `bento_bento_test.yaml` beside it.

## Related

- [06a-ingestion-examples](06a-ingestion-examples.md) — four worked recipes, from the connection manifest to the curl that proves the entities arrived.
- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
