# Tech Stack Decision

## Context

The product (see [plan.md](plan.md)) is a weekly Start/Stop/Continue retro tool:
multi-user card submission, per-card anonymity, facilitator-controlled board lifecycle,
a synchronized reveal, collaborative clustering, dot voting (3 stackable votes/person),
plain-text decision notes, and post-meeting upload of audio/video/transcript.

### Constraints

| Dimension | Decision |
|---|---|
| Language / framework | Python / Django |
| Infrastructure | Single self-hosted box, minimal external dependencies |
| Frontend style | Implementer's choice |
| Auth | Standalone accounts now; Google Workspace SSO deferred |

### What the product demands technically

- **Real-time multiplayer** — the reveal is a synchronized moment; clustering is
  collaborative drag; dot voting updates live. WebSockets fit better than SSE/polling.
- **Server-enforced authorization** — pre-reveal, a contributor sees *only their own
  cards*; the realtime layer must respect this (no broadcasting card creations to the
  whole board before the reveal).
- **Roles** — facilitator vs contributor, per board.
- **Object storage** for meeting recordings (files can be hundreds of MB).
- **Relational data** — boards, cards, clusters, votes, notes, attachments map cleanly
  to Postgres.
- **Low concurrency** — one team (~5–15 people) per active board; a single stateful
  process is sufficient.

## Chosen stack

A **Django server-rendered app with Postgres as the only backing service, HTMX for
interactivity, a small JS island for the clustering board, and WebSockets via Django
Channels using the in-memory channel layer** (no Redis).

| Layer | Choice | Notes |
|---|---|---|
| Framework | Django 5.x (ASGI) | Batteries included: auth, ORM, migrations, admin |
| Database | PostgreSQL 16 | On the same box. SQLite + WAL is a viable fallback for a single team |
| Web/API | Server-rendered templates + HTMX (`django-htmx`) | Card entry, board list, notes, voting, uploads |
| Realtime | Django Channels + `InMemoryChannelLayer` | Reveal broadcast, live vote tallies, cluster moves, presence |
| Realtime fallback | HTMX polling (`hx-trigger="every 2s"`) on the board view | Drop-in if WebSockets are deferred |
| Clustering UI | SortableJS island (optional Alpine.js glue), no build step | Drag cards between clusters; persist via POST; broadcast over the Channels group |
| Auth | Django auth + `django-allauth` (email/password + magic link) | Social providers installed but unconfigured; Google SSO is a later settings change |
| Roles | `BoardMembership.role` (`facilitator` / `contributor`) | Enforced in views and WS consumers |
| Pre-reveal visibility | Server-side queryset filter by `board.phase` + `request.user`; WS consumer joins a user only to groups they may see | Security-sensitive — covered by tests |
| File storage | `FileSystemStorage` on local disk (`MEDIA_ROOT`), served by nginx | Swap to `django-storages` + S3/R2 later via the `STORAGES` setting |
| Static assets | WhiteNoise (or nginx) | No separate frontend build pipeline |
| Process model | `gunicorn` + `UvicornWorker`, **1 worker**, nginx in front for TLS + static/media | Single worker is required by the in-memory channel layer |
| Deploy | `docker compose`: `app` + `postgres` on one host, `.env` for secrets | `uv` for dependency pinning |
| Background work | None in v1 | If transcript processing is added later, use `django-tasks` / a cron management command, not Celery |

### Why this fits the constraints

- **One box, minimal dependencies:** Postgres is the only service besides the app — no
  Redis, no Node build step, no external SaaS.
- **Python / Django:** matches the team's background; the admin site is a free
  facilitator/ops console on day one.
- **The one hard UI problem** (collaborative clustering) is isolated to a single JS
  island rather than forcing a full SPA.
- **Realtime is real but scoped:** in-memory Channels gives a live reveal/voting feel
  with zero extra infrastructure.

### Accepted tradeoffs / risks

- Single ASGI process → no horizontal scaling; a restart drops WebSocket connections
  (clients reconnect and refetch). Acceptable for an internal single-team tool.
- The in-memory channel layer loses ephemeral state on restart; all durable state lives
  in Postgres, so a reconnect + refetch fully recovers.
- Local-disk media needs a backup story — include `MEDIA_ROOT` in the box's backups.
- HTMX + SortableJS clustering is less polished than a React/Liveblocks canvas; if the
  UX proves too limited, promote just that view to a React island later.

### Documented upgrade paths

- **Scale past one process:** replace `InMemoryChannelLayer` with `channels-redis` (adds
  Redis) or `channels_postgres`.
- **Object storage:** `django-storages` + S3 / Cloudflare R2, switched via `STORAGES`.
- **SSO:** configure the already-installed `django-allauth` Google provider.

## Alternatives considered and set aside

| Option | Summary | Why not |
|---|---|---|
| Next.js + Supabase | Hosted Postgres + Auth + Realtime + Storage + row-level security; least code; RLS fits the pre-reveal rule well | Not Python; hard dependency on a hosted platform |
| Full-stack TypeScript (Remix/Next + Prisma + Postgres + Liveblocks/Ably) | One TS codebase; Liveblocks makes collaborative clustering very smooth | Not Python; adds a paid realtime SaaS |
| Django + DRF + Channels + React SPA + Redis | Powerful, explicit authz, free admin console | Redis + a separate SPA build conflict with "single box, minimal dependencies"; kept as the fallback if scale outgrows one process |
| Django + HTMX, Postgres-only, no WebSockets | Simplest possible | Chosen design, plus a live board view — voting/clustering feel noticeably better over a socket than polling |
| FastAPI + React | Async-native, lightweight WebSockets | You assemble auth, admin, permissions, and migrations — more upfront work than Django for this feature set |
