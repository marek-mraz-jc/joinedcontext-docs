---
sidebar_position: 66
title: "ADR-N-065: Hosting Decidim as a Deployment Component"
---

# ADR-N-065: Hosting Decidim as a Deployment Component

Date: 2026-11-01  
Status: Proposed  
Decision Makers: product owner (2026-11-01, supervisor session: "to host that [Decidim] internally on prod cluster. And integrate these data from there."); drafted by worker-t6316 (T-6316), owner may override

This record decides how the platform runs its own Decidim instance, which identity it signs people in with, what happens to the personal data it holds, and what is left open before it serves citizens on prod. [Deployment/18](../Deployment/18-decidim.md) carries the objects, the sizing and the measured run.

## 1. Context

Until now the platform only harvested public Decidim instances (T-5065: Tvorme spolu over its public GraphQL API into the `participacia` model). The owner chose to host an instance on the prod cluster and take its data from there (T-6317). Decidim is a Ruby on Rails application with PostgreSQL, Redis, Sidekiq and file storage. The platform's own code stays Rust and TypeScript; a third-party application image is allowed in the way Keycloak and CKAN are, as long as nothing of ours is written in Ruby beyond configuration.

## 2. Options

| Option | Cost | Verdict |
|---|---|---|
| A. Keep harvesting public instances only | none | refused by the owner's decision: no instance of the city's own |
| B. Build our own participation application | months of Portal work | refused: Decidim already covers processes, proposals, budgets, meetings and results |
| C. The stock `decidim/decidim` image as it is | no image of ours | refused: it has no OpenID Connect strategy, runs as root and ships the generator's `config/master.key` |
| D. The stock image plus one thin layer of ours, on the shared workload chart | one Dockerfile, one image workflow | **chosen** |

## 3. Decision

1. **The image.** `images/decidim/Dockerfile` in `joinedcontext-deployment` builds Decidim 0.32.2 itself, since the Decidim project publishes no image past 0.31.6 (T-6321): the `decidim` generator writes the application on `ruby:3.4.12-trixie` with Node.js 22, as the project's own image build does, and the result is copied onto `ruby:3.4.12-slim-trixie`, both by digest. It adds the `omniauth_openid_connect` 0.8.0 gem, `faker` (Decidim's seed classes require it when production eager-loads them), one initializer (`joinedcontext.rb`) and one bootstrap script (`bootstrap.rb`). It deletes the generated credentials file, updates every gem whose fixed release Decidim's version ranges allow, carries no compiler and no Node.js at runtime and runs as user 10001. `image-decidim.yml` builds, signs and scans it like the CKAN image.
2. **The workloads.** Three releases of `charts/workload`: `decidim-web` (puma, with a `migrate` init container that runs `db:migrate` and the bootstrap), `decidim-sidekiq` (the same image, started as Sidekiq) and `decidim-redis` (no persistence). The database is `decidim` in the shared CNPG cluster `postgres-cluster`. Attachments go on a 5 GiB ReadWriteOnce claim that both pods mount; object storage waits for the owner's S3 keys, and with it a second web replica.
3. **Identity.** Every person signs in through the instance's realm: client `decidim`, confidential, standard flow with PKCE, redirect `https://participacia.{domain}/users/auth/keycloak/callback`. The initializer registers it as the only enabled provider. Decidim links a sign-in to the account that holds the same e-mail address, so the initializer drops any address the realm has not verified (`email_verified` false), and Decidim then confirms it itself.
   - **No public sign-up form.** The bootstrap sets the organization's registration mode to `existing` on every rollout. Accounts come from the realm, whose registration is off, so the owner opens sign-up by opening the realm, never in Decidim.
   - **No local password anyone holds.** The bootstrap gives the organization's admin (`decidim.web.adminEmail`, a realm person) a random password it never stores. The edge refuses `/users/password`, `/users/invitation` and `/users/sign_up` (404), so no account gains a password the realm's MFA never sees. The admin console at `/admin` is reached only by signing in through the realm, where admins hold MFA (T-5567).
   - **The system console** (`/system`: organizations and system admins, Decidim's own login) is refused at the edge and has no account. An operator who needs it creates a system admin with `bin/rails decidim_system:create_admin` inside the pod and reaches it by `kubectl port-forward`.
4. **Known findings.** After the image's updates, trivy finds one HIGH and no CRITICAL entry: rubyzip 2.3.2 (CVE-2026-85396, fixed in 3.4.0), which decidim-core 0.32.2 holds at `~> 2.0` and doc2text 0.4.8 at `~> 2.3.0`. Decidim 0.32 lifted the 0.31.6 pins on puma, ransack, shakapacker and oauth (T-6321). omniauth-twitter stays, because decidim-core declares it as a runtime dependency; it resolves oauth 1.1.8 and stays disabled. The image workflow keeps its HIGH and CRITICAL gate and runs it on the built image before any push, so the image does not reach the registry while this one stands; until then the workflow runs only by hand (`workflow_dispatch`), its push and schedule triggers kept in a comment, so no merge and no monthly run turns the lane red. Publishing needs either a Decidim release that lifts the rubyzip pin or the owner's written acceptance of this one finding with an expiry; this record does neither.
5. **Network.** The web answers the edge alone, on `participacia.{domain}` with its own HTTP-01 certificate. Web and Sidekiq reach the database, Redis and SMTP (587 and 465 on public addresses); the web alone reaches the realm on its public host. Redis answers web and Sidekiq and nothing else. Every workload is meshed, with the four Linkerd halves per peer.
6. **Data into NGSI-LD.** The instance's public GraphQL API at `/api` is the harvester's source (T-5065, T-6317). The harvester reads only public, non-personal fields, as it does for public instances.

## 4. Security and personal data

- Citizen accounts are personal data under the GDPR. The request log is cut to warnings and errors, because request lines carry client addresses, and the initializer adds name, nickname, personal URL and about-text to the parameters Rails filters, beside the passwords and e-mail addresses Rails already filters.
- **Backups.** The `decidim` database is in the cluster's nightly local dump (the `postgres-cluster-local-backup` CronJob on prod), which is the only copy until the owner's S3 keys exist: no off-site copy and no point-in-time recovery. The attachments claim is not in that dump. Both hold for any personal data the instance takes, so prod serves citizens only after the owner accepts that state or the off-site backup exists.
- Secrets reach the pods by reference only: `db-decidim`, `decidim-secret-key-base`, `keycloak-client-decidim` and the operator's SMTP Secret. The image holds no key.

## 5. Consequences

- `joinedcontext-deployment` gains `components/decidim`, `images/decidim` and `.github/workflows/image-decidim.yml`; the addons environment renders the component, and no deploying environment lists it before T-6317.
- T-6317 pins the digest the workflow publishes, installs on dev, then on prod, and points the harvester at the in-cluster service.
- A Decidim upgrade is a Dockerfile edit and a rebuild; Decidim's migrations run in the init container of the first pod that starts.

## Related

- [Deployment/18](../Deployment/18-decidim.md): the component, its sizing and the kind run
- [ADR-N-062](adr-n-062-branch-previews-on-the-dev-node.md): the dev node budget
- [Deployment/07](../Deployment/07-backup-restore.md): backups
