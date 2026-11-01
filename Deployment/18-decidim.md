---
sidebar_position: 19
title: "Decidim Participation Platform"
description: "The decidim component: its image, workloads, database, sign-in through the realm, network rules, sizing measured on a throwaway run, and what an operator sets before installing it."
---

# Decidim Participation Platform

The `decidim` component runs the city's own Decidim instance on `participacia.{domain}`: participatory processes, proposals, budgets, meetings and results, with every person signing in through the instance's realm. [ADR-N-065](../Decisions/adr-n-065-hosting-decidim.md) records why and what is left open; this page is what an operator needs to install and run it.

## 1. What it deploys

| Release | Runs | State |
|---|---|---|
| `decidim-web` | puma on port 3000; init container `migrate` runs `bin/rails db:migrate` and `db/joinedcontext_bootstrap.rb` | 5 GiB ReadWriteOnce claim `decidim-web-files` at `/code/storage` (attachments) |
| `decidim-sidekiq` | `bundle exec sidekiq -C config/sidekiq.yml`, the same image | mounts `decidim-web-files` |
| `decidim-redis` | Redis 7, `--save "" --appendonly no`, 96 MB `maxmemory`, `noeviction` | none: a Redis restart loses queued jobs |

The database `decidim` lives in the shared CNPG cluster `postgres-cluster` (`components/decidim/databases.yaml`), owned by role `decidim`. All three run as non-root users with a read-only root filesystem; Rails writes only to `/tmp`, `/code/tmp` and `/code/log` (emptyDirs) and to the claim.

The image is `ghcr.io/marek-mraz-jc/joinedcontext-decidim:0.31.6`, built from `images/decidim/` by `.github/workflows/image-decidim.yml`, which scans it before the push and refuses it on any fixed HIGH or CRITICAL finding, then signs it and attests its CycloneDX bill of materials; it runs by hand only while the findings of ADR-N-065 section 4 stand.

## 2. Configuration

Every value sits under `decidim.web` (`components/decidim/default-environment.yaml.gotmpl`):

| Value | Default | Meaning |
|---|---|---|
| `subDomain` | `participacia` | the host; the edge route and the certificate SAN list read it |
| `organization.name` | `Participácia` | the organization's name in the default locale |
| `organization.defaultLocale`, `organization.locales` | `sk`, `[sk, en]` | the locales the instance offers; the bootstrap refuses a default outside the list |
| `organization.referencePrefix` | `JC` | the prefix of every reference, e.g. `JC-PROP-2026-11-1` |
| `adminEmail` | empty | the verified realm address of the organization's admin; empty: no admin yet |
| `smtp.address`, `port`, `username`, `from`, `passwordSecret` | empty, 587 | outgoing mail; with `address` empty Decidim sends none. The password is key `password` of the Secret `passwordSecret` names |

The bootstrap runs on every rollout and is idempotent: it creates the organization on the first one, then sets the registration mode back to `existing` and the locales to the configured ones on each later one, and gives `adminEmail` its admin flag. It prints no personal field.

## 3. Sign-in

The realm client `decidim` (`components/decidim/keycloak-clients.yaml`) is confidential, standard flow only, PKCE S256, redirect `https://participacia.{domain}/users/auth/keycloak/callback`; its secret reaches the pods as `keycloak-client-decidim`. Decidim shows one button, "Keycloak", and no sign-up form. A first sign-in creates the Decidim account from the realm's name and verified e-mail address after the person accepts the terms of service; an address the realm has not verified is dropped, and Decidim confirms one itself.

The edge answers 404 on `/system`, `/users/password`, `/users/invitation` and `/users/sign_up` (`uri-blocker` in `components/decidim/apisix-plugins.yaml`), so no account gains a local password and the system console is reached only by `kubectl port-forward`.

## 4. Network

| From | To | Port |
|---|---|---|
| APISIX | `decidim-web` | 3000 (4143 meshed) |
| `decidim-web`, `decidim-sidekiq` | `postgres-cluster` | 5432 (4143 meshed) |
| `decidim-web`, `decidim-sidekiq` | `decidim-redis` | 6379 (4143 meshed) |
| `decidim-web` | the realm's public host, or the ingress controller it is rewritten to | 443, 8443 |
| `decidim-web`, `decidim-sidekiq` | SMTP on public addresses | 587, 465 |

Everything else is refused by the namespace default-deny. Each meshed workload also reaches the Linkerd control plane on 8080, 8086 and 8090.

## 5. Sizing

Measured on 2026-11-01 (T-6316) on a throwaway Docker network, because kind cannot start inside the per-task sandbox (its node container gets no mount permission in a user namespace). The run used the image above, the environment the chart renders for `decidim-web`, PostgreSQL 16 over TLS, Redis with the chart's arguments and Keycloak 26.8.1. Each container ran with a read-only root, user 10001 and every capability dropped. The numbers are `docker stats` after about 240 page requests, one Keycloak sign-in per test person, one process and one proposal:

| Workload | Measured | dev request / limit | production request / limit |
|---|---|---|---|
| `decidim-web` (5 threads measured; dev runs 3) | 611 MiB | 640 Mi / 1 Gi | 900 Mi / 1.5 Gi |
| `decidim-sidekiq` (3 workers; dev runs 2) | 353 MiB | 448 Mi / 768 Mi | 640 Mi / 1 Gi |
| `decidim-redis` | 4 MiB | 64 Mi / 160 Mi | 64 Mi / 160 Mi |
| PostgreSQL connections | 8 backends, database 16 MB | in the shared cluster | in the shared cluster |

The production profile asks about 1.6 GiB of requests, and the shared cluster's 8 more backends add about 150 MiB at the roughly 19 MiB per backend dev measured. That fits prod's 24 GB node at 61 % requested (about 8 GiB free on 2026-11-01). The development profile asks about 1.15 GiB, which the dev node does not have today: T-6317 checks headroom before the install. The connection budget tests (`tests/test_postgres_connection_budget.py`) count Decidim's pools once an environment lists the component.

## 6. Install and operate

1. Pin the digest `image-decidim.yml` printed in its run summary in `components/decidim/images.yaml` (`web` and `sidekiq` carry the same one).
2. Add `decidim` to the environment's `components` list, set `decidim.web.adminEmail` and, for mail, `decidim.web.smtp`, and regenerate `gitops/<env>.yaml`.
3. Apply the component's releases with a scoped apply, then open `https://participacia.{domain}/up` (200) and sign in as the admin.
4. The harvester reads the public GraphQL API at `https://participacia.{domain}/api` (T-6317).

The database is in the nightly local dump with the rest of the cluster ([Deployment/07](07-backup-restore.md)); the attachments claim is not, and prod has no off-site copy until the owner's S3 keys exist (ADR-N-065 section 4).

## Related

- [ADR-N-065](../Decisions/adr-n-065-hosting-decidim.md): the decision
- [Deployment/04](04-components-and-addons.md): components and add-ons
- [Deployment/10](10-edge-routing-apisix.md): edge routing
