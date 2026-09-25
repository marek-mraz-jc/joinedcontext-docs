---
sidebar_position: 8
title: "Ingestion Recipes"
description: "Four end-to-end ingestion pipelines, from the connection manifest to the curl that proves the entities arrived."
---

# Ingestion Recipes

Four pipelines that read the outside world and write NGSI-LD entities: an MQTT stream, an HTTP JSON poll, a CSV export on a schedule, and a GTFS-realtime protobuf feed. Each recipe is a `DataSource`, a `Pipeline` and the `Endpoint` the entities are written through, followed by the request that shows they arrived. Read [06-pipelines](06-pipelines.md) first for what Bento is and how a pipeline runs; this page is the copy-paste layer on top of it. Every recipe here is also a working folder in the platform repository under `examples/ingestion/`, with golden tests that CI runs.

## 1. What a recipe is made of

A pipeline lives in `projects/{project}/pipelines/{name}/` and holds two files (PL-01):

```text
projects/helsinki/
├── datasources/
│   └── hsl-hfp.yaml                    # DataSource: where the data comes from (MF-35)
├── spaces/
│   └── mobility/
│       └── endpoints/
│           └── ep-vehicles.yaml        # Endpoint: where the entities are written to (EP-01)
└── pipelines/
    └── hsl-hfp-vehicles/
        ├── pipeline.yaml               # envelope: class, cadence, target endpoint, references
        └── bento.yaml                  # native Bento: processors and output (PL-03)
```

The directory layout is the convention of [Architecture/06 §2](../Architecture/06-configuration-as-code.md), and it is worth following, but it is not what the loader reads: a resource is identified by its `kind`, `metadata.namespace` and `metadata.name`, wherever in the repository the file sits. A manifest in the wrong folder loads and then confuses the next person, which is why the layout is reviewed rather than parsed.

Each of the four recipes below is a working folder in `joinedcontext-platform/examples/ingestion/` — `hsl-hfp-mqtt`, `http-json-poll`, `csv-fetch` and `gtfs-rt` — each with its `datasource.yaml`, `pipeline.yaml`, `bento.yaml` and the `bento_bento_test.yaml` golden test CI runs.

The part that surprises people: **`bento.yaml` has no `input`**. A pipeline that names `spec.source.dataSourceRef` gets its input rendered by the reconciler from the referenced connection, and the author's processors and output are left exactly as written (PL-39). Each connection type becomes one Bento input, listed in [Architecture/08 §6](../Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39).

A credential never appears in any of the three files. A `DataSource` carries the name and key of a secret, the reconciler resolves it, and the generated config carries an environment variable interpolation derived from the source name, `${DS_AQ_OPENDATA_TOKEN}` for the `token` key of a source called `aq-opendata` (CC-06, PL-16).

## 2. MQTT: a vehicle stream

HSL publishes every bus, tram and ferry in the Helsinki region as high-frequency positioning frames on a public MQTT broker. The connection has no credential, which is the point of showing it first: a `DataSource` is a connection, not a login.

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: DataSource
metadata:
  name: hsl-hfp
  namespace: helsinki
  title:
    en: HSL high-frequency positioning
spec:
  type: mqtt
  mqtt:
    urls:
      - tls://mqtt.hsl.fi:8883
    topics:
      - /hfp/v2/journey/ongoing/vp/bus/#
    qos: 0
    cleanSession: true
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Pipeline
metadata:
  name: hsl-hfp-vehicles
  namespace: helsinki
spec:
  class: auto
  source:
    dataSourceRef: { kind: DataSource, name: hsl-hfp }
  targetEndpoint: urn:ngsi-ld:Endpoint:hel.fi:transport:ep-vehicles
  quotas:
    maxMemoryMb: 128
    cpuMillicores: 250
```

`class: auto` with no `period` means push-based, so the thirty-second rule keeps this pipeline in the project's resident runner rather than starting a pod (PL-26). The entities land through an ordinary Endpoint:

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Endpoint
metadata:
  name: ep-vehicles
  namespace: helsinki
spec:
  contextSpaceRef: transport
  slug: hs7v3k2mq4xd6bnr5tcf2aw3ye
  audience: public
  enabledRepresentations: [ngsi-ld, geojson]
```

The mapping is the whole of `bento.yaml`. One topic tree carries several frame kinds, so the first processor keeps position reports and drops the rest, and the last one turns a frame into an entity:

```yaml
pipeline:
  processors:
    - mapping: |
        root = if this.exists("VP") { this.VP } else { deleted() }
    - mapping: |
        root = {
          "id": "urn:ngsi-ld:Vehicle:hel.fi:transport:" + "%v-%v".format(this.oper, this.veh),
          "type": "Vehicle",
          "location": {
            "type": "GeoProperty",
            "value": { "type": "Point", "coordinates": [ this.long.number(), this.lat.number() ] },
            "observedAt": this.tst
          },
          "speed": { "type": "Property", "value": this.spd.number(), "unitCode": "MTS" },
          "heading": { "type": "Property", "value": this.hdg.number(), "unitCode": "DD" }
        }
```

The full file adds the `@context`, the route, and a thirty-vehicle cap: thirty slot keys in a Bento memory cache, each taken with `add` by one bus and refreshed by every frame it sends, so the demo follows the same thirty buses instead of flickering between hundreds. A bus silent for the cache's ttl frees its slot for the next one. A slot handed out by `counter()` is never handed out again, and that feed went silent half an hour after a start (T-2961). `tests/test_hfp_fleet_cap.py` in the deployment repository asserts the cap and the reuse.

## 3. HTTP: polling a JSON API

A REST endpoint that returns an array of stations, behind a bearer token. The token is the first credential on this page, and it is a reference:

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: DataSource
metadata:
  name: aq-opendata
  namespace: helsinki
spec:
  type: http
  http:
    url: https://opendata.hel.fi/api/v1/air-quality/stations.json
    verb: GET
    headers:
      Accept: application/json
    authorization:
      scheme: Bearer
      headerRef: { name: aq-opendata, key: token }
    timeout: 10s
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Pipeline
metadata:
  name: aq-http-poll
  namespace: helsinki
spec:
  class: auto
  period: 5m
  source:
    dataSourceRef: { kind: DataSource, name: aq-opendata }
  targetEndpoint: urn:ngsi-ld:Endpoint:hel.fi:air-quality:ep-air
  quotas:
    maxMemoryMb: 64
    cpuMillicores: 100
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Endpoint
metadata:
  name: ep-air
  namespace: helsinki
spec:
  contextSpaceRef: air-quality
  slug: aq6r2m5ke7xd4bns3tcf2vw5yj
  audience: public
  enabledRepresentations: [ngsi-ld, geojson, csv]
```

Five minutes is past the thirty-second rule, so the reconciler renders a CronJob that scales to zero between runs (PL-26). One response carries the whole station list, so the pipeline splits it before mapping:

```yaml
pipeline:
  processors:
    - unarchive:
        format: json_array
    - mapping: |
        root = if this.exists("measurements") { this } else { deleted() }
    - mapping: |
        root = {
          "id": "urn:ngsi-ld:AirQualityObserved:hel.fi:air-quality:" + this.station_id.string(),
          "type": "AirQualityObserved",
          "dateObserved": { "type": "Property", "value": this.measured_at },
          "pm10": { "type": "Property", "value": this.measurements.pm10.number(), "unitCode": "GQ" }
        }
    - archive:
        format: json_array
```

The trailing `archive` turns the batch back into one request: a page of forty stations is one upsert, not forty.

## 4. CSV: a tabular export on a schedule

The same `http` connection type fetches a file rather than an API. Nothing about the source says CSV; the pipeline is what knows how to read it.

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: DataSource
metadata:
  name: parking-csv
  namespace: helsinki
spec:
  type: http
  http:
    url: https://opendata.hel.fi/parking/occupancy.csv
    verb: GET
    headers:
      Accept: text/csv
    timeout: 15s
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Pipeline
metadata:
  name: parking-csv-fetch
  namespace: helsinki
spec:
  class: auto
  period: 45s
  source:
    dataSourceRef: { kind: DataSource, name: parking-csv }
  targetEndpoint: urn:ngsi-ld:Endpoint:hel.fi:transport:ep-parking
  quotas:
    maxMemoryMb: 64
    cpuMillicores: 100
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Endpoint
metadata:
  name: ep-parking
  namespace: helsinki
spec:
  contextSpaceRef: transport
  slug: pk3v7m2qe5xd6bnr4tcf2aw6yh
  audience: public
  enabledRepresentations: [ngsi-ld, geojson, csv]
```

Forty-five seconds is the interesting cadence. It is past the thirty-second rule but under the minute cron can express, so the reconciler renders a CronJob on `* * * * *` whose Bento input fetches once per period inside the run (PL-27). One fetch is one file, so the first processor splits it into rows:

```yaml
pipeline:
  processors:
    - mapping: |
        let rows = content().string().parse_csv()
        root = if $rows.length() == 0 { deleted() } else { $rows }
    - unarchive:
        format: json_array
```

A CSV with a header and no rows is a file the source published early. It writes nothing rather than failing the run.

## 5. GTFS-realtime: a protobuf feed

The `gtfs-rt` type is the one connection that contributes a processor of its own. The feed arrives as protobuf, and every pipeline reading it would otherwise decode the same envelope in its own mapping, so the reconciler puts the decoder in front:

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: DataSource
metadata:
  name: hsl-gtfs-rt
  namespace: helsinki
spec:
  type: gtfs-rt
  gtfsRt:
    url: https://gtfs.hsl.fi/realtime/vehiclepositions.pb
    feed: vehiclePositions
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Pipeline
metadata:
  name: hsl-gtfs-rt-ingest
  namespace: helsinki
spec:
  class: auto
  period: 15s
  source:
    dataSourceRef: { kind: DataSource, name: hsl-gtfs-rt }
  targetEndpoint: urn:ngsi-ld:Endpoint:hel.fi:transport:ep-transit
  quotas:
    maxMemoryMb: 128
    cpuMillicores: 200
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Endpoint
metadata:
  name: ep-transit
  namespace: helsinki
spec:
  contextSpaceRef: transport
  slug: md5r3k7qe2xv6bns4tcf3aw2yl
  audience: public
  enabledRepresentations: [ngsi-ld, geojson]
```

What the mapping sees is a decoded `FeedMessage` in protojson form, which matters for two reasons: field names are camelCase, so the proto's `trip_update` arrives as `tripUpdate`, and every 64-bit field including timestamps arrives as a string. A feed entity is a vehicle position, a trip update or a service alert, so the mapping switches on which one it is and produces a `Vehicle` or a `Trip`:

```yaml
pipeline:
  processors:
    - mapping: |
        root = this.entity.or([])
    - unarchive:
        format: json_array
    - switch:
        - check: this.exists("vehicle")
          processors:
            - mapping: |
                let v = this.vehicle
                root = {
                  "id": "urn:ngsi-ld:Vehicle:hel.fi:transport:" + $v.vehicle.id.string(),
                  "type": "Vehicle",
                  "location": {
                    "type": "GeoProperty",
                    "value": {
                      "type": "Point",
                      "coordinates": [ $v.position.longitude.number(), $v.position.latitude.number() ]
                    },
                    "observedAt": $v.timestamp.number().ts_format("2006-01-02T15:04:05Z", "UTC")
                  }
                }
        - check: this.exists("tripUpdate")
          processors:
            - mapping: |
                let u = this.tripUpdate
                root = {
                  "id": "urn:ngsi-ld:Trip:hel.fi:transport:" + $u.trip.tripId.string(),
                  "type": "Trip",
                  "route": { "type": "Property", "value": $u.trip.routeId }
                }
        - processors:
            - mapping: 'root = deleted()'
```

Fifteen seconds is inside the thirty-second rule, so this one stays resident even though it polls.

This recipe and the MQTT one are two views of the same fleet and mint the same ids, so a deployment runs one of them, not both.

## 6. Checking what arrived

Every recipe is verified the same way, through the Endpoint rather than the broker: what a pipeline wrote is what the Endpoint's Policy lets you read (EP-01). Replace `{host}` with the deployment and `{slug}` with the endpoint's slug.

The entities of one type:

```bash
curl -sS "https://{host}/api/endpoint/{slug}/ngsi-ld/v1/entities?type=Vehicle&limit=5" \
  -H 'Accept: application/ld+json'
```

One entity by the id the mapping minted, which is the fastest way to see whether the URN scheme came out right:

```bash
curl -sS "https://{host}/api/endpoint/{slug}/ngsi-ld/v1/entities/urn:ngsi-ld:Vehicle:hel.fi:transport:22-787" \
  -H 'Accept: application/ld+json'
```

The same data as a map layer, which is the quickest check that `location` is a GeoProperty and not a string:

```bash
curl -sS "https://{host}/api/endpoint/{slug}/file.geojson" | head -40
```

Whether the numbers are moving, on a private endpoint, with a ServiceAccount token:

```bash
curl -sS "https://{host}/api/endpoint/{slug}/ngsi-ld/v1/entities?type=AirQualityObserved&attrs=pm10&limit=3" \
  -H 'Accept: application/ld+json' \
  -H 'Authorization: Bearer eyJhbGciOi…'
```

If the count stays at zero, read the pipeline before the endpoint: Portal → Pipelines shows the stream's received and error counters, and a resident pipeline whose received counter is zero has an input problem rather than a mapping problem.

## 7. Running the golden tests

Every recipe on this page is a folder in `examples/ingestion/` of the platform repository, with the transformation under test (PL-22):

```bash
bento lint ./examples/ingestion/*/bento.yaml ./examples/ingestion/gtfs-rt/tests/decoder.yaml
bento test ./examples/ingestion/...
cargo test -p jcctl --test ingestion_examples_tests
```

Bento pairs a test file with the config of the same name in the same folder, so a config called `bento.yaml` is tested by `bento_bento_test.yaml` beside it. `bento lint` resolves environment interpolations, so export any value for `SERVICE_ACCOUNT_TOKEN` before running it.

The `cargo` test covers what Bento cannot see: both manifests parse through `jc-core`, the reference resolves inside the pipeline's own project, the declared cadence lands in the runtime the recipe claims, the rendered input matches the connection type, and no example writes a credential as a value.

## Related

- [06-pipelines](06-pipelines.md) — what Bento is, how a pipeline is deployed and how it is debugged.
- [Architecture/08 §6](../Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39) — the `DataSource` kind and the Bento input each type becomes.
- [04-manifest-kinds](04-manifest-kinds.md) — every kind, its plural and its path in the repository.
- [Testing/04](../Testing/04-configuration-and-pipeline-tests.md#5-bento-pipelines) — where pipeline tests live and what CI runs.
- [Requirements/pipelines](../Requirements/pipelines.md) — PL-01…PL-39, the normative statements behind these recipes.
