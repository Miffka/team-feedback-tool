# Weekly Team Feedback Tool — v1 Backlog

Each task is sized for one session and written to be handed to someone who has not read
the other tasks. Tasks after #1 assume the repo is already at the state the earlier
tasks produce, but each description carries the context needed to do it standalone.
The board detail page is built as phase-specific template partials so the card,
reveal, clustering, voting, and notes tasks each own a separate include.

See [stack.md](stack.md) for the chosen technology and why. See [plan.md](plan.md) for
the product scope these tasks implement.

## 1. Project skeleton with a passing test
Goal: An empty, runnable Django project with one green test.
Description: Create the Django project layout, a `pyproject.toml` (managed with `uv`) pinning Django and `pytest-django`, a `docker compose` file with `app` and `postgres` services, and a `.env.example`. Add a single trivial test (e.g. asserting the home URL returns 200 or a health view returns "ok") and confirm `pytest` passes inside the container.

## 2. Base settings, ASGI, HTMX and static assets
Goal: Production-shaped settings split plus HTMX and static-file plumbing.
Description: Split settings into `base` / `dev` / `prod`, read secrets from environment, and add an ASGI entrypoint. Install and wire `django-htmx`, WhiteNoise, and a base template with the HTMX script tag and a content block. Add a `health/` view and a site-wide 404/500 template.

## 3. Accounts and authentication
Goal: Users can sign up, log in, and log out.
Description: Add `django-allauth` configured for email + password and passwordless magic-link login; leave social providers installed but unconfigured. Provide a `Profile` (or custom user) carrying a `display_name` used everywhere a name is shown. Include login, logout, signup, and "edit display name" pages plus tests for the core flows.

## 4. Core data models
Goal: All v1 persistence in place, admin-registered, no views.
Description: Define `Board` (with a `phase` field), `BoardMembership` (`board`, `user`, `role` in {facilitator, contributor}), `Card` (`board`, `author`, `kind` in {start, stop, continue}, `text`, `is_anonymous`), `Cluster` (`board`, `title`), `CardCluster` (`card`, `cluster`), `Vote` (`board`, `voter`, `cluster`, `weight`), `Note` (`board`, `author`, `text`, `order`), and `MeetingRecord` (`board`, `file`, `kind`, `uploaded_by`). Generate migrations and register each model in the Django admin.

## 5. Board lifecycle and phase state machine
Goal: Facilitators create boards and move them through phases.
Description: Implement the phase flow `draft → collecting → revealed → clustering → voting → discussion → closed` with a helper that validates transitions and permits them for facilitators only. Add "create board" (creator becomes facilitator), a board list showing the viewer's boards, and a board detail shell that renders a different partial per phase. Cover valid and invalid transitions with tests.

## 6. Membership and role enforcement
Goal: Controlled join and reusable permission checks.
Description: Add a way for a user to join an existing board as a contributor (via a shareable link or code) and for a facilitator to promote another member. Provide `is_facilitator(user, board)` / `is_member(user, board)` helpers and a view mixin/decorator that returns 403 for non-members. Add tests asserting non-members cannot open a board and contributors cannot perform facilitator actions.

## 7. Card submission with pre-reveal isolation
Goal: Contributors add their own Start/Stop/Continue cards and see only those before the reveal.
Description: Build an HTMX form to create a card (kind + text + "post anonymously" checkbox), plus inline edit and delete for the author's own cards, with no per-person limit. The card list queryset must return only `request.user`'s cards while the board phase is `collecting`. Add tests proving one contributor cannot see another's cards pre-reveal via the view.

## 8. Reveal
Goal: The facilitator reveals all cards at once.
Description: Add a facilitator-only action that transitions the board from `collecting` to `revealed` and makes every card visible to all members. Render each card with its author's `display_name`, except cards where `is_anonymous` is true, which show as "Anonymous". Add a test that the pre-reveal isolation from task 7 no longer applies after reveal.

## 9. Realtime board updates
Goal: Board changes appear for everyone without a manual refresh.
Description: Configure Django Channels with the in-memory channel layer and a per-board consumer that a user may join only if they are a member and the phase allows it. Provide a `broadcast_board_event(board, event)` helper and wire the reveal action to push an event that triggers the clients to refresh the card area. Document the HTMX-polling fallback in a comment for when Channels is disabled.

## 10. Clustering board
Goal: The team drags similar cards into shared groups after the reveal.
Description: In the `clustering` phase, render cards and cluster containers and use SortableJS to drag cards between them, persisting each move with a POST that creates/updates a `CardCluster`. Support create, rename, and delete cluster (deleting returns its cards to the unclustered pool). Broadcast each change over the task 9 channel so other participants' boards update live.

## 11. Dot voting
Goal: Each person spends three stackable votes across clusters.
Description: In the `voting` phase, show clusters with a control to add or remove a vote; enforce that a voter's total `Vote.weight` for the board never exceeds 3 while allowing multiple votes on one cluster. Show a live per-cluster tally (broadcast over the channel) and, when voting closes, order clusters by total weight. Add tests for the 3-vote cap and stacking.

## 12. Discussion notes
Goal: Capture decisions and action items as plain notes.
Description: In the `discussion` phase, provide add / edit / delete / reorder for `Note` rows attached to the board, each shown with its author and free-form text (no owner or due-date fields). Notes are visible to all members and persist with the board. Keep the editor HTMX-driven with no page reload.

## 13. Meeting record upload
Goal: The facilitator attaches the meeting's audio, video, or transcript afterward.
Description: Add a facilitator-only upload form on a closed (or discussion-phase) board that accepts an audio, video, or transcript file into a `MeetingRecord` via `FileSystemStorage`, with the upload size limit raised to accommodate large media. List uploaded records with type and uploader and provide a download link. No in-app recording or playback controls beyond the browser default.

## 14. Past boards archive
Goal: Browse and read closed boards.
Description: Add a list of the viewer's closed boards and a read-only board view that renders the final cards, clusters, vote totals, notes, and meeting records with all editing controls removed. This is the record teams refer back to in later weeks.

## 15. Deployment configuration
Goal: One-command deploy on a single box.
Description: Finalize the `prod` settings, a `gunicorn` + `UvicornWorker` command with a single worker (required by the in-memory channel layer), a sample nginx config for TLS plus `/static/` and `/media/`, and a `.env.example` listing every required variable. Add a README section with run, migrate, and backup steps, noting that `MEDIA_ROOT` must be included in backups.
