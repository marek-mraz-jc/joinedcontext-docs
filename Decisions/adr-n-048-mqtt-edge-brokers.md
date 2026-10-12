---
sidebar_position: 49
title: "ADR-N-048: MQTT Edge Brokers per Project, RMQTT as Is, Keycloak Tokens Checked by the Gateway"
---

# ADR-N-048: MQTT Edge Brokers per Project, RMQTT as Is, Keycloak Tokens Checked by the Gateway

Date: 2026-10-12  
Status: Accepted  
Decision Makers: product owner (orders of 2026-10-11 ~19:15Z and ~19:35Z, T-3836); the choices of section 2 were delegated in the order and taken by worker-2 (owner may override)

## 1. Context

The owner, 2026-10-11: a Rust MQTT server with ACL, published on ports of its own so nothing collides, holding no state, with a Bento pipeline carrying its messages into the context broker. Cameras publishing to an address are the first use. In a second order the same evening: "there is already a Rust MQTT broker, just use that". A project may run **several** brokers, and each one is a manifest in the project's Git repository like every other kind ([Architecture/06](../Architecture/06-configuration-as-code.md)).

What exists today: a `DataSource` of `type: mqtt` (MF-35, PL-39) subscribes a pipeline to an **external** broker, with a password from a `secretRef`. Nothing in the platform accepts an MQTT connection itself.

Facts checked on 2026-10-12, each against the project's own repository:

| Question | RMQTT ([rmqtt/rmqtt](https://github.com/rmqtt/rmqtt)) | rumqttd ([bytebeamio/rumqtt](https://github.com/bytebeamio/rumqtt)) |
|---|---|---|
| License | MIT | Apache-2.0 |
| Last release | 0.24.0, 2026-09-19; last push 2026-10-11 | rumqttd-0.20.0, 2025-09-29 |
| Image | `rmqtt/rmqtt:0.24.0`, index digest `sha256:9d9496cfbe4c853d1246a4a151bab652898130b0a819ff69fbae9a786865a637` (amd64, arm64) | none published by the project |
| JWT authentication | `rmqtt-auth-jwt`: RS256/RS384/RS512/ES256/ES384 against **one PEM public key file**; **no JWKS URL** ([docs/en_US/auth-jwt.md](https://github.com/rmqtt/rmqtt/blob/master/docs/en_US/auth-jwt.md)) | none |
| HTTP authentication | `rmqtt-auth-http`: CONNECT posts `clientid`, `username`, `password`, `ipaddr`; the answer is `allow`/`deny`/`ignore` with an optional `acl` list and `expire_at`; `deny_if_error = true` denies on a transport failure ([docs/en_US/auth-http.md](https://github.com/rmqtt/rmqtt/blob/master/docs/en_US/auth-http.md)) | none |
| ACL | `rmqtt-acl` file rules (restart to change), plus the `acl` list an auth plugin returns per connection, topics with `${clientid}` and `${username}` placeholders, per-rule `qos` and `retain` ([docs/en_US/perm-list.md](https://github.com/rmqtt/rmqtt/blob/master/docs/en_US/perm-list.md)) | static config |
| Fail-closed | the stock final rule `["allow", "all"]` also allows CONNECT for every connection an auth plugin left undecided; `["deny", "all"]` closes it ([docs/en_US/acl.md](https://github.com/rmqtt/rmqtt/blob/master/docs/en_US/acl.md)) | n/a |
| State | retain, session and message storage are separate plugins (`rmqtt-retainer`, `rmqtt-session-storage`, `rmqtt-message-storage`) that can stay unloaded | in memory |
| Per-listener limits | `max_connections`, `max_packet_size`, `max_qos_allowed`, `mqueue_rate_limit`, `max_subscriptions`, `max_session_expiry_interval`, `proxy_protocol` ([rmqtt-conf/src/listener.rs](https://github.com/rmqtt/rmqtt/blob/master/rmqtt-conf/src/listener.rs)) | some |

The other half of the path is the pipeline, and it has one constraint. Bento's `mqtt` input reads its `password` once, as a plain string ([internal/impl/mqtt/client.go](https://github.com/warpstreamlabs/bento/blob/main/internal/impl/mqtt/client.go)). A Keycloak access token expires within minutes, and every reconnect would present the stale one. The pinned runner is upstream Bento, which we do not fork.

## 2. Decision

A project declares **MQTT edge brokers** as manifests, `kind: MqttBroker`. Each one is a release of its own of the unmodified RMQTT image. Devices authenticate with a Keycloak token that the **context gateway** checks for the broker, and a pipeline reads the broker on an internal listener that only the pipeline runner can reach.

1. **The kind.** `MqttBroker` lives in a project at `projects/{p}/mqttbrokers/{name}.yaml` and is served at `/api/v1/projects/{project}/mqttbrokers` (MF-11). Its name is a DNS label, unique in the project. `spec` holds:
   - `roles`: a list of `{name, serviceAccounts, publish, subscribe}`. `serviceAccounts` names ServiceAccounts of the same project. `publish` and `subscribe` are topic filters that may use `${clientid}`.
   - `limits`: `maxMessageBytes` (default 65536, at most 1 MiB), `messagesPerSecond` per client (default 10, at most 1000), `maxConnections` (default 1000, at most 10000).
   - `port`: optional, see item 5.

   A device role may hold `subscribe` filters only under its own `${clientid}`. The reconciler refuses a filter that is `#` or begins with `$`.
2. **The engine, as is.** RMQTT 0.24.0, pinned by the digest above and mirrored and signed by the deployment like every other third-party image. We write no broker code, only configuration: listener limits from `spec.limits`, `max_qos_allowed = 1`, `max_session_expiry_interval = 0`, no retainer, no session storage, no message storage, `rmqtt-auth-http` pointed at the gateway with `deny_if_error = true` and `disconnect_if_expiry = true`, `http_acl_req` off (the ACL comes back at CONNECT, so no publish costs an HTTP call), and `rmqtt-acl` holding the one rule `["deny", "all"]`. Clean sessions only, QoS 0 and 1 kept in memory: a restart loses the messages in flight and nothing else.
3. **Devices: a Keycloak token, checked by the gateway.** A camera is a `ServiceAccount` (PF-45, PF-47). It connects with the client id and username of its Keycloak client `{project}-{sa}` and an access token as the password. RMQTT's own JWT plugin would need the realm key as a static PEM and could not follow a key rotation, so the token is checked where tokens are already checked: `rmqtt-auth-http` posts the CONNECT to the gateway's internal route `POST /internal/mqtt/auth`. The gateway allows the connection only when every check below holds:
   - the token verifies against the realm JWKS;
   - its audience holds the broker's client `mqtt-{project}-{name}`;
   - its `azp` equals both the username and the client id;
   - the account holds a role of this broker.

   The device gets that token by its own key pair: its account's `oauth-client` credential carries the public JWKS, and the reconciler writes the client `{project}-{sa}` with `client-jwt` authentication. The device signs a client assertion and holds no secret ([Architecture/12 §3](../Architecture/12-identity-and-access.md#a-device-by-its-own-key-pair-pf-47-t-4015), T-4015).

   The answer carries the role's `publish` and `subscribe` filters as the RMQTT `acl` list (`retain: false`, `qos: [0, 1]`), `superuser: false`, and `expire_at` set to the token's `exp`, so the broker drops the connection when the token expires and the device reconnects with a new one. The gateway learns which broker is asking from the caller's mesh identity (Linkerd `l5d-client-id`, the broker's Kubernetes ServiceAccount `mqtt-{project}-{name}`), never from a request field, so no broker can ask with another broker's ACL. Only the broker pods reach the route; it is not on APISIX.
4. **Pipelines: the internal listener, by mesh identity.** A `DataSource` of `type: mqtt` may name a broker of its own project with `spec.mqtt.brokerRef: {kind: MqttBroker, name}` in place of `urls`. The reconciler renders the broker's internal Service URL on port 1883 and, as the username, the runner's identity name. The DataSource carries no password and no `passwordRef`. The internal listener admits the runner's Kubernetes ServiceAccount alone: a Linkerd `Server` with an `AuthorizationPolicy` (MeshTLSAuthentication) and a NetworkPolicy from the runner namespace. The gateway allows a CONNECT without a password only for that username and only from the address of one of the runner's pods: it resolves the runner's headless Service (`pipeline-runner-pods`, `JC_GATEWAY_MQTT_RUNNER_HOST`) per such CONNECT. Every connection to the public listener arrives through Traefik with the PROXY protocol, so its `ipaddr` is the client's own address, public, or a pod's for a cluster workload that dials the public host. Neither is a runner pod's, and such a CONNECT is refused there (T-4004: a private address alone let any cluster pod pass as the runner). The answer's `acl` grants `subscribe` on the topic filters of the DataSources that reference this broker and nothing else, with no `publish` and no `expire_at`. This is the ceiling the shared runner already sets for the token service ([Architecture/12 §One principal per pipeline](../Architecture/12-identity-and-access.md)): a stream on the runner can name what another stream may read. One runner per project lifts it later. The pipeline writes onward as every pipeline does, through an Endpoint and its Policy (CC-61).
5. **Addresses.** The default is TLS on 8883 through a Traefik TCP router matching `HostSNI(<name>.<project>.mqtt.<domain>)`. Traefik terminates TLS with a certificate cert-manager issues for that one hostname by HTTP-01, never a wildcard, and forwards plain TCP with the PROXY protocol to the broker's external listener. One port serves every broker and nothing collides. The hostname is derived from the name and the project, so it is unique across the platform by construction. `port: <n>` asks for a dedicated port from the reserved range 18830–18849: the reconciler refuses a port another broker holds, naming that broker, and RMQTT then terminates TLS itself on a LoadBalancer Service. Plain 1883 is never published outside the cluster.
6. **One release per broker.** Each broker has its own Keycloak client `mqtt-{project}-{name}` (the audience, no secret, bearer-only), its own Deployment, ConfigMap, Service and Kubernetes ServiceAccount in `{instance}-mqtt`, and its own metrics. Two brokers of one project share no client, no ACL and no credential, and a token minted for one broker's audience is refused by every other.
7. **Configuration as code.** The Portal edits the manifest through a commit, in the review lane where the project uses one. `jcctl apply` and a hand-edited file in Git do the same. The reconciler renders the release, the Keycloak client and the Traefik route, and deletes all three with the manifest. Secrets stay `secretRef` only: a broker needs none of its own.

## 3. Security Analysis

The build tasks (T-3837…T-3839) inherit each row as a failing test.

| Threat | Control |
|---|---|
| A stolen camera token | The token's lifetime bounds a stolen copy: it is worth one connection until `exp`, and the broker drops it at `exp` (`disconnect_if_expiry`). Disabling the ServiceAccount's client in Keycloak stops the next connection. Short access-token lifetimes for camera clients come from the realm (5 minutes by default). |
| Topic squatting | A device's ACL is its role's filters with `${clientid}` bound to its verified `azp`; the gateway refuses a CONNECT whose username or client id differs from `azp`. One camera cannot publish under another's topic. |
| A token for another broker or service | The audience must hold `mqtt-{project}-{name}` of the broker asking, and the gateway knows which broker asks from its mesh identity. A gateway or Endpoint token is refused here. |
| Floods | Per-listener `max_connections`, `max_packet_size` and `mqueue_rate_limit` from `spec.limits`, QoS at most 1, no retain, no persistent session; publish ACL decided at CONNECT, so a flood never turns into HTTP calls. Limits have platform ceilings the manifest cannot pass. |
| The auth service is down | `deny_if_error = true` and the single `["deny", "all"]` rule: every CONNECT is refused, and connections that are already open stay up until `exp`. |
| An outside client or a cluster pod posing as the runner | A CONNECT without a password is allowed only for the runner's name from the address of a runner pod. Traffic to the public listener carries its source address through the PROXY protocol, which Traefik writes; the public listener admits Traefik alone. The internal listener admits the runner's mesh identity alone. |
| Plain text from outside | TLS only from outside: Traefik terminates TLS on 8883 and a dedicated port terminates TLS in RMQTT; plain 1883 is a ClusterIP Service. |
| A secret typed into the manifest | The schema has no field that could hold a credential; the broker uses none, and a DataSource with `brokerRef` refuses `passwordRef`. |

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| RMQTT's `rmqtt-auth-jwt` with the realm key as a PEM | It reads one static key: a Keycloak key rotation breaks every device until a re-render. It also cannot bind the ACL to a ServiceAccount's role without carrying the ACL in the token. The gateway already verifies Keycloak tokens against JWKS. |
| The ACL as an `acl` claim minted into each token | Puts authorization in Keycloak mappers per client and per broker, invisible in the project's Git repository. |
| rumqttd | No published image, no HTTP or JWT authentication, last release more than a year older; kept as the fallback should RMQTT fail its build task. |
| A broker of our own | The owner asked for an existing one. |
| The pipeline authenticated by a token in the password | Bento's `mqtt` input reads the password once, so the first reconnect after `exp` fails. A refreshing stream would need a forked runner. |
| The pipeline authenticated by its client secret | A static key between cluster services, which the platform does not use. |
| One wildcard certificate for `*.mqtt.<domain>` | Needs a DNS API; certificates are issued per hostname by HTTP-01. |

## 5. Consequences

- **`jc-core`** gains `MqttBroker` (MF-54) and `DataSource.spec.mqtt.brokerRef`; `jcctl` places the kind, waves it after ServiceAccounts, and validates roles, limits and the port range.
- **The gateway** serves `POST /internal/mqtt/auth` for broker pods only (PL-75).
- **The reconciler** renders each broker's release, Keycloak client and Traefik route, refuses a duplicate port, and resolves `brokerRef` (T-3837).
- **The deployment** mirrors and signs the RMQTT image, adds the `{instance}-mqtt` namespace, the Traefik `mqtts` entrypoint on 8883, and the NetworkPolicies and Linkerd policies of section 2 (T-3837).
- **The Portal** lists, creates and edits brokers as Changes and shows each broker's address and a copy-ready client configuration (T-3838).
- **The camera demo** publishes through a broker into a space (T-3839).

## 6. Requirements

Landed with this decision:

- `Requirements/manifests.md`: **MF-54**.
- `Requirements/pipelines.md`: **PL-74**…**PL-77**.

## Related

- [ADR-N-043](adr-n-043-named-mcp-servers.md): a manifest kind that the reconciler renders into a Keycloak client of its own.
- [Architecture/08-pipelines.md](../Architecture/08-pipelines.md): DataSource and the pipeline runner.
- [Architecture/12-identity-and-access.md](../Architecture/12-identity-and-access.md): service identities and one principal per pipeline.
- [Requirements/manifests.md](../Requirements/manifests.md): MF-35, MF-54.
- [Requirements/pipelines.md](../Requirements/pipelines.md): PL-39, PL-74…PL-77.
