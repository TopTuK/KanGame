# 🎮 KanGame

[![Tests](https://github.com/TopTuK/KanGame/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/TopTuK/KanGame/actions/workflows/backend-tests.yml)

🌐 **Live at [kangame.pmi.moscow](https://kangame.pmi.moscow)** — try it instantly in **demo mode**, no registration required.

An interactive web simulation of Kanban methodology, inspired by [getKanban®](https://www.agile42.com/en/get-kanban/) — the Lean/Agile board game. Manage flow, limit WIP, assign team resources, handle different classes of service, and deliver value from Day 9 through Day 35 to maximize revenue.

> 🤖 **Built with AI assistance** — This project was created with help from [Claude Code](https://claude.ai/code) and [Cursor](https://cursor.com). Architecture, game logic, UI components, and infrastructure were developed through human–AI collaboration.

![KanGame board](kan_scr.png)

---

## ✨ Features

- 🎯 **Pull system** — Work is pulled from backlog and between ready/done buffers based on available capacity
- 🚧 **WIP limits** — Enforce constraints per column (Analysis, Development, Test)
- 👥 **Resource assignment** — Click or drag workers onto active tasks; distribute the team across different cards or assign several workers to one card; each role has its own productivity range per stage (see [📜 Rules of the Game](#-rules-of-the-game))
- ⚡ **Classes of service** — Standard, expedite, fixed-date, and intangible cards with distinct economic effects
- 📅 **Daily gameplay loop** — Pull cards, assign resources, start work, review the work log, and end the day
- 📊 **Metrics** — Track throughput, WIP, deployed work, daily revenue, and cumulative revenue
- 📈 **Analytics diagrams** — Cumulative Flow Diagram, Lead Time distribution, Cycle Time distribution, and a Kanban flow-metrics summary (avg lead/cycle time, avg throughput, avg WIP, Little's Law check, on-time delivery rate), viewable mid-game or after the game ends
- 🔐 **Authentication** — Sign in with your organization's OIDC account before starting or resuming a game
- 💾 **Persistent, per-user games** — Save and resume your own games via PostgreSQL; each player only sees their own
- 🎬 **Demo mode** — Try a shortened Day 9–15 simulation from the home page with no account needed; not saved, not resumable, and excluded from the leaderboard (see [🎬 Demo Mode](#-demo-mode))
- 🏆 **Public leaderboard** — Top 5 users by best completed-game revenue, viewable at `/leaderboard` without signing in; demo games never count. A separate **AI agents** table ranks finished agent runs and shows which LLM model each one used
- 📜 **Rules page** — Public `/rules` page: step-by-step daily routine, card types, the full card catalog with estimates, team capacity and scoring, with numbers served live from the engine (see [📜 Rules of the Game](#-rules-of-the-game))
- 🤖 **AI agent player** — Let an LLM play a full game in the background with the same actions as a human, every action logged with its reason (see [🤖 AI Agent Mode](#-ai-agent-mode))
- 🌐 **Localization** — Russian and English UI; Russian is the default; switch language from the header selector (preference saved in the browser)

---

## 🏗️ Architectural Decomposition

The system follows a **classic three-tier layout** with a clear split between presentation, application logic, and persistence. Game rules live exclusively on the backend; the frontend is a thin, reactive client.

```
┌─────────────────────────────────────────────────────────────────┐
   🌐 Presentation (Vue 3 SPA)                                    
   Views → Components → Pinia Store → API Client                  
   vue-i18n (UI strings + client-side content translation)        
└────────────────────────────┬────────────────────────────────────┘
                             │ REST / JSON
┌────────────────────────────▼────────────────────────────────────┐
   ⚙️ Application (FastAPI)                                       
   Routes → Schemas → Game Engine → Models                        
└────────────────────────────┬────────────────────────────────────┘
                             │ SQLAlchemy async
┌────────────────────────────▼────────────────────────────────────┐
   🗄️ Persistence (PostgreSQL)                                    
   games · cards · events · metrics                               
└─────────────────────────────────────────────────────────────────┘
```

### 🖥️ Frontend — Presentation Layer

| Layer | Responsibility |
|-------|----------------|
| **Views** (`HomeView`, `GameView`, `DemoGameView`, `LeaderboardView`, `RulesView`, `AgentView`) | Page-level layout and routing entry points — `LeaderboardView`, `RulesView` and `DemoGameView` are reachable without signing in |
| **Components** | UI building blocks — board, columns, cards, modals, panels |
| **Pinia store** (`gameStore`) | Client state, derived WIP counts, worker selection, API orchestration |
| **i18n** (`i18n/`, `useGameContent`) | UI strings and translated card/event text keyed by `card_key` / `event_key` |
| **API service** (`api.js`) | Axios client; all server communication goes through `/api` |

The UI never encodes game rules. It renders server state and sends player actions (pull, assign resources, start work, end day) back to the API.

**Key components:**

- `GameHeader` — day progress, revenue, WIP badges, End Day control
- `KanbanBoard` / `KanbanColumn` / `KanbanCard` — board layout, drag-and-drop card movement, a "Pull to Ready" button on Backlog cards, worker drop targets
- `ResourcePanel` — draggable worker pool, multi-select click assignment, Start Work
- `MetricsPanel` — throughput, WIP, deployed work, and revenue history
- `AnalyticsModal` (with `CumulativeFlowChart` and `DistributionHistogram`, built on Chart.js/vue-chartjs) — Cumulative Flow Diagram, Lead/Cycle Time distributions, and Kanban flow metrics; opened from the header's 📈 Analytics button or from the end-game screen
- `HelpModal` / `WorkLogModal` / `EndDayModal` / `ScoreModal` — onboarding, daily work log, day events, and end-game summary
- `LanguageSelector` — in-app locale switcher (top-right)

### ⚙️ Backend — Application Layer

| Layer | Responsibility |
|-------|----------------|
| **API routes** (`api/routes/games.py`) | HTTP endpoints, validation, error handling — every route requires a signed-in user and is scoped to their own games |
| **Auth routes** (`api/routes/auth.py`) | OIDC login redirect, provider callback, current-user lookup, logout |
| **Leaderboard route** (`api/routes/leaderboard.py`) | Public, unauthenticated endpoint — no route dependency requires a session |
| **Rules route** (`api/routes/rules.py`) | Public `GET /api/rules`: productivity ranges, WIP limits, roster, card catalog and rank thresholds, built from the engine constants by `services/rules.py` |
| **Demo route** (`api/routes/demo.py`) | Public, unauthenticated endpoints for demo games — no `GET`, so a demo can never be re-fetched or resumed (see [🎬 Demo Mode](#-demo-mode)) |
| **Schemas** (`schemas/game.py`, `schemas/user.py`, `schemas/leaderboard.py`) | Pydantic request/response DTOs |
| **Game engine** (`services/game_engine.py`) | All Kanban rules: pull, WIP, worker assignment, work rolls, revenue, events; every game lookup is filtered by owner. Also computes the leaderboard (best completed-game revenue per user, excluding demo games) and creates/purges demo games |
| **Data definitions** (`data/cards.py`) | Static card deck and daily event catalog |
| **Models** (`models/game.py`, `models/user.py`) | SQLAlchemy ORM entities — `Game.is_demo` flags demo games |
| **Core** (`core/`) | Config, async DB session factory, OIDC client (`oauth.py`), `get_current_user` dependency (`auth.py`) |

### 🔐 Authentication

KanGame uses a **backend-driven OIDC Authorization Code flow** (via [Authlib](https://authlib.org/)) against your organization's identity provider — the client secret never reaches the browser:

1. The frontend sends the user to `GET /auth/login`, which redirects to the provider's authorize endpoint.
2. The provider redirects back to `GET /auth/signin-oidc`; the backend exchanges the code, upserts a `User` row keyed by the OIDC `sub` claim, and stores `user_id` in a signed, `HttpOnly` session cookie (Starlette `SessionMiddleware`).
3. The browser is redirected back to the SPA. Every subsequent `/api/*` call is authenticated via that cookie through `get_current_user`.
4. `GET /api/auth/me` reports the current user to the frontend; `POST /api/auth/logout` clears the session.

Configure the provider in `.env` (see Quick Start and Local Development below) — `AuthClientId`, `AuthClientSecret`, `AuthAuthority`, `AuthCallbackUrl`, plus `SESSION_SECRET_KEY` and `BASE_URL`.

A separate, **test-only** login path (`POST /api/dev/test-login`) bypasses OIDC entirely; it 404s unless `ENABLE_TEST_LOGIN=true` and exists solely so the e2e suite can authenticate without a real identity provider — see [🧪 Testing](#-testing).

The **game engine** is the single source of truth for mechanics:

- Column flow: Backlog → Ready → Analysis → Analysis Done → Development → Dev Done → Test → Deployed
- Separate expedite track with its own ready/WIP handling
- Pull rules and WIP enforcement for ready, active, and done-buffer columns
- Worker assignment stored in `team_config.workers` (one worker → one card; many workers → same card allowed)
- Role- and stage-specific productivity ranges at work time, blockers, Carlos/lockdown event flags, buffs
- Revenue, penalties, overdue removals, and metric snapshots at end of day

### 🎬 Demo Mode

Visitors who aren't signed in can click **Try a demo instead** on the home page to play a shortened Day 9–15 slice of the game with no account:

- All demo games are owned by a single system `User` row (created automatically on backend startup) and flagged `is_demo=True`, with `total_days=15` instead of 35 — the same `game_engine` functions (`assign_worker`, `pull_card`, `start_work`, `end_day`) run unchanged, so demo games follow the identical rules and day events as a real game.
- `api/routes/demo.py` exposes `POST /api/demo`, `/assign-worker`, `/pull-card`, `/start-work`, `/end-day` — none of them require a session. There is deliberately **no `GET /api/demo/{id}`**: every action already returns the fresh game state directly, so nothing needs to re-fetch one, which is what makes a demo impossible to resume — reloading the page or navigating away always lands back on the warning screen instead of restoring the game.
- `get_top_leaderboard` filters out `is_demo` games, so demo scores never appear on `/leaderboard`.
- A background task started at app startup purges demo games (and their cards/events/metrics) older than 24 hours once a day, so demo data never accumulates in the database.

### 🤖 AI Agent Mode

Signed-in users can open **🤖 Run AI agent** on the home page (`/agent`) and let an LLM play a full Day 9–35 game exactly like a human player. The agent is built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) (`agent-framework-openai`, Chat Completions client), so any OpenAI-compatible endpoint works (OpenAI, RouterAI, OpenRouter, vLLM, Ollama, Azure `…/openai/v1`). The user supplies an agent name, base URL, model and API key.

- **Same actions as a human.** The agent's function tools map 1:1 to the player's UI actions and call the same `game_engine` functions: `get_game_state` (look at the board), `pull_card`, `assign_worker`, `start_work`, `end_day`. Each mutating tool requires a one-sentence `reason`. Engine errors (e.g. `WIP limit reached for test`) are returned to the model so it can correct itself.
- **Knows the rules.** The agent's instructions (`services/agent_prompts.py`) are generated from the engine constants: the board and pull rules, WIP limits, the productivity table, the team roster with the starting team's daily capacity, all four card types and exactly how each pays, and the card catalog with every card's value and A/D/T estimate. It is told only what a human player can know (future events and unannounced expedite cards stay hidden).
- **Runs in the background.** `services/agent_runner.py` runs one asyncio task per run on the server, independent of the browser: the user can close the page and come back later; the home page shows a banner while a run is active and the agent page pauses polling while hidden. A backend restart ends active runs (they are marked `failed`), because the API key lives only in memory.
- **Day loop with memory.** The whole game is one conversation: each day appends a day prompt (yesterday's end-of-day event — the same dialog a human reads — open deadlines, the agent's last note and the current board) and the agent's tool calls, results and note. If the model stops without starting work or ending the day, a **system safety net** does it and logs that it did, so every game finishes.
- **Context summarization** (`services/agent_memory.py`). The context window is `AGENT_CONTEXT_WINDOW_TOKENS` (default 200,000). Before each day, if the estimated context would pass `AGENT_CONTEXT_SUMMARY_THRESHOLD` × window (default 0.3, i.e. ~60k tokens — lower is cheaper), all but the last `AGENT_CONTEXT_KEEP_RECENT_DAYS` days are condensed by the model into a "Game memory" summary (revenue trend, deadlines, team changes, lessons, plan); cuts happen only at day boundaries so tool calls stay paired with their results. If summarization fails, a deterministic summary from the daily journal is used — memory pressure never fails a run. Within a day, the Agent Framework's `ContextWindowCompactionStrategy` collapses older tool results if a single day nears the window. Each summarization is logged as a `context_summarized` run event.
- **Timeouts and retries.** Every model request has a timeout (`AGENT_LLM_TIMEOUT_SECONDS`, default 120 s) and the OpenAI client's own quick retries (`AGENT_LLM_REQUEST_RETRIES`, default 2); a whole day has a hang guard (`AGENT_DAY_TIMEOUT_SECONDS`, default 900 s). A day that fails with a transient error (timeout, connection error, rate limit, 5xx) is retried up to `AGENT_LLM_RETRIES` times (default 4) with exponential backoff and jitter, honouring `Retry-After`; each retry rebuilds the prompt from the **current** board, since the interrupted attempt may already have moved cards. Authentication and bad-request errors fail immediately; an error after the day already ended only loses the note and the run continues. Every retry is logged as an `llm_retry` run event.
- **Guardrails.** One active run per user, a per-day tool-call cap (`AGENT_DAY_TOOL_CALL_LIMIT`, default 40), a global run timeout (`AGENT_MAX_RUN_MINUTES`, default 120), repeated board looks without changes answered with a short "unchanged" reply instead of the whole board, cancel at any time, and runs interrupted by a restart are marked `failed` at startup. `AGENT_ENABLED=false` turns the feature off.
- **Default provider.** The form is pre-filled with [RouterAI](https://routerai.ru), an OpenAI-compatible gateway (`AGENT_DEFAULT_BASE_URL=https://routerai.ru/api/v1`), and OpenAI's fast, low-cost `openai/gpt-4.1-nano` (`AGENT_DEFAULT_MODEL`). If `AGENT_DEFAULT_API_KEY` is set in `.env` (a RouterAI key), users can leave the key field blank. The server key is only ever sent to the default base URL and is never returned by `GET /api/agent/config`. In production it comes from the `AGENT_DEFAULT_API_KEY` GitHub secret.
- **API key handling.** The key is kept in memory only (request → background task → client), is never written to the database or logs, and is redacted from error messages.
- **Games.** Agent games are owned by the user, appear in their games list with an **AI** badge, are excluded from the human leaderboard (`is_agent`, like `is_demo`) but ranked in its separate **AI agents** table with their model, and are read-only for humans (the game routes return 409).

#### 📝 Action log (human and agent)

Every player action — by a human through the game routes or by the agent through its tools — is written to the shared `game_actions` table in the same shape, so the two can be compared directly:

| Column | Meaning |
|---|---|
| `actor` | `human`, `agent`, or `system` (the runner's safety net acting for the agent) |
| `seq`, `day` | Order within the game, and the game day of the action |
| `action` | `day_start` (board snapshot in `state`), `get_game_state`, `pull_card`, `assign_worker`, `start_work`, `end_day`, `day_summary` (the agent's daily note in `reason`, tokens and estimated context size in `result`), `run_event` (`started`, `llm_retry`, `llm_error_after_day_end`, `context_summarized`, `completed`, `failed`, `cancelled`) |
| `arguments` | Card keys / worker ids, never UUIDs: `{card_key, from_col}`, `{worker_id, worker_type, card_key, card_col}`, `{assignments, idle_workers}` |
| `result` | `{ok, error?}` plus the outcome: destination column, assign toggle outcome, work-log dice rolls, end-of-day event and overdue cards |
| `reason` | The agent's rationale for the action |

Failed attempts are logged too (`result.ok = false`). Fetch a game's log with `GET /api/games/{id}/actions`, or download an agent run's log, with run metadata and daily metrics, from the agent page. Example comparison query:

```sql
SELECT g.is_agent, a.day,
       count(*) FILTER (WHERE a.action = 'pull_card' AND (a.result->>'ok')::bool)  AS pulls,
       count(*) FILTER (WHERE a.action = 'pull_card' AND NOT (a.result->>'ok')::bool) AS rejected_pulls,
       avg(json_array_length(a.arguments->'idle_workers')) FILTER (WHERE a.action = 'start_work') AS idle_workers
FROM game_actions a JOIN games g ON g.id = a.game_id
WHERE a.actor IN ('human', 'agent')
GROUP BY g.is_agent, a.day ORDER BY a.day, g.is_agent;
```

### 🗄️ Data Layer

PostgreSQL stores the full game snapshot:

| Entity | Purpose |
|--------|---------|
| `User` | OIDC identity (`sub`, email, name) — owns games; a single system row also owns all demo games |
| `Game` | Session metadata, day/phase, team config, WIP limits, revenue; belongs to a `User`; `is_demo` flags demo games (excluded from the leaderboard, purged daily) |
| `Card` | Work items with story points, column, type, due dates; `stage_days` records the first day each card reached every pipeline stage, feeding the analytics diagrams |
| `GameEvent` | Daily event cards and resolution state |
| `GameMetric` | Time-series snapshots for charts |

### 🐳 Infrastructure Layer

Docker Compose orchestrates four services:

| Service | Role |
|---------|------|
| **nginx** | Reverse proxy — serves frontend, forwards `/api` to backend |
| **frontend** | Multi-stage build: Vite → static assets in Nginx |
| **backend** | FastAPI + Uvicorn with hot reload in dev |
| **db** | PostgreSQL 16 with health checks and persistent volume |

### 🔄 Request Flow (one player action)

```
User drags a worker onto a task (or selects workers, then clicks a task)
    → KanbanCard / gameStore.assignWorker() or assignToCard()
    → POST /api/games/{id}/assign-worker
    → game_engine.assign_worker()  (validates planning phase and active lane)
    → team_config persisted in PostgreSQL
    → refreshed GameResponse → UI re-renders

User clicks Start Work
    → ResourcePanel calls gameStore.startWork()
    → POST /api/games/{id}/start-work
    → game_engine.start_work()  (rolls work, advances completed stages)
    → refreshed game + work log
    → UI shows WorkLogModal
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| 🎨 Frontend | Vue 3, Vite, Pinia, Vue Router, vue-i18n, Tailwind CSS, Chart.js / vue-chartjs |
| 🐍 Backend | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic |
| 🔐 Auth | Authlib (OIDC client), Starlette `SessionMiddleware` (signed session cookies) |
| 🗄️ Database | PostgreSQL 16 |
| 🐳 Infra | Docker Compose, Nginx |
| 🧪 Testing | pytest (backend business logic), Vitest (frontend business logic), Playwright (e2e), GitHub Actions (CI) |

---

## 📁 Project Structure

```
KanGame2/
├── .github/workflows/
│   ├── backend-tests.yml       # CI: pytest + Vitest on PRs into main
│   └── deploy-production.yml   # Manual (workflow_dispatch) build-and-deploy to PROD
├── backend/              # FastAPI API and game engine
│   ├── tests/            # pytest suite for the game engine (unit + Postgres-backed integration)
│   └── app/
│       ├── api/routes/   # REST routes (games.py, auth.py, leaderboard.py, demo.py, agent.py, rules.py)
│       ├── core/         # Config, database, OIDC client (oauth.py), get_current_user (auth.py)
│       ├── data/         # Card and event definitions, rank thresholds
│       ├── models/       # SQLAlchemy models (game.py, user.py)
│       ├── schemas/      # Pydantic DTOs (game.py, user.py, leaderboard.py)
│       └── services/     # Game engine, rules data, action log, AI agent (runner, tools, prompts, memory)
├── frontend/             # Vue 3 SPA
│   ├── e2e/               # Playwright end-to-end tests (+ playwright.config.js)
│   └── src/
│       ├── components/   # Board, cards, panels, modals, language selector
│       ├── composables/  # Shared logic (e.g. content translation)
│       ├── i18n/         # Locale files (ru, en) and vue-i18n setup
│       ├── stores/       # Pinia state (gameStore.js, authStore.js) + __tests__/ (Vitest)
│       ├── services/     # API client
│       └── views/        # Home, game, demo game, leaderboard, rules, and AI agent pages
├── nginx/                # Dev reverse proxy config (docker-compose.yml only)
├── deploy/vhost.d/       # nginx-proxy vhost snippets for kangame.pmi.moscow (copied onto the PROD host manually)
├── LICENSE               # MIT license
├── Dockerfile                      # PROD image: builds frontend, backend serves it as static files on one port
├── docker-compose.yml
├── docker-compose.production.yml   # PROD stack: single `app` container + `db`, joins the shared reverse-proxy network
├── docker-compose.test.yml         # Test overlay: enables /api/dev/test-login
└── .env.production.example         # Template for the PROD host's .env (see Production Deployment)
```

---

## 🚀 Quick Start (Docker)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/), Docker Compose, and OpenSSL

1. Create `.env` in the repo root (copy `.env.example`) with your OIDC provider's `AuthClientId`, `AuthClientSecret`, `AuthAuthority`, `AuthCallbackUrl=/auth/signin-oidc`, a random `SESSION_SECRET_KEY` (e.g. `openssl rand -hex 32`), and `BASE_URL` (default `http://localhost` works for local dev). Register `http://localhost/auth/signin-oidc` as the redirect URI with your OIDC provider.
2. Start the stack:
   ```bash
   docker compose up --build
   ```

Open [http://localhost](http://localhost) in your browser and sign in to start a game.

| Service | URL |
|---------|-----|
| 🌐 App | http://localhost |
| 📖 API docs | http://localhost/api/docs |
| ❤️ Health | http://localhost/health |
| 🔧 Backend (direct, debug only) | http://localhost:8000 |

To stop:

```bash
docker compose down
```

To rebuild images from scratch (e.g. after backend/frontend changes):

```bash
docker compose down --rmi all --remove-orphans
docker compose build --no-cache
docker compose up -d --force-recreate
```

---

## 🚢 Production Deployment

Production runs as a **single container**: the root [`Dockerfile`](Dockerfile) builds the Vue frontend, then bakes the resulting static assets into the FastAPI image, which serves both the API and the SPA (with client-side-routing fallback) on one port. There's no separate frontend/nginx container in prod — TLS and the public domain (`https://kangame.pmi.moscow`) are handled by an external shared [`nginx-proxy`](https://github.com/nginx-proxy/nginx-proxy) reverse proxy that isn't part of this repo.

- [`docker-compose.production.yml`](docker-compose.production.yml) — the `app` service (image `kangame:latest`) plus `db` (Postgres). `app` joins the external `pmi_network` so `nginx-proxy` can discover it via `VIRTUAL_HOST`/`VIRTUAL_PORT`; `db` stays on the internal network only.
- [`.github/workflows/deploy-production.yml`](.github/workflows/deploy-production.yml) — manual (`workflow_dispatch`) pipeline: builds and pushes the image to `ghcr.io/toptuk/kangame:latest`, then SSHes into the host to pull the image, sync `docker-compose.production.yml`, and recreate the stack.
- [`deploy/vhost.d/`](deploy/vhost.d/) — `nginx-proxy` vhost config for `kangame.pmi.moscow` (TLS settings + security/gzip headers), copied onto the host's `rproxy/vhost.d/` directory by hand — this repo's pipeline never touches the shared reverse-proxy config.
- [`.env.production.example`](.env.production.example) — template for the real secrets file that must exist at `/home/toptuk/kangame/.env` on the host **before the first deploy** (the pipeline never creates or overwrites it).

Required one-time setup on the host, none of which the pipeline does for you: create `/home/toptuk/kangame/.env` from the example above with real OIDC/session secrets, and place the `deploy/vhost.d/` files into the reverse proxy's `vhost.d/`. After that, running the workflow builds, pushes, and redeploys the app.

---

## 💻 Local Development

### 🐍 Backend

**Prerequisites:** Python 3.12+, PostgreSQL 16

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env` (or reuse the repo-root `.env` from Quick Start):

```env
DATABASE_URL=postgresql+asyncpg://kanban:kanban@localhost:5432/kanban
AuthClientId=...
AuthClientSecret=...
AuthAuthority=https://your-oidc-provider/
AuthCallbackUrl=/auth/signin-oidc
SESSION_SECRET_KEY=...
BASE_URL=http://localhost
SESSION_COOKIE_SECURE=false
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

📖 API docs: http://localhost:8000/api/docs

### 🎨 Frontend

**Prerequisites:** Node.js 20+

```bash
cd frontend
npm install
npm run dev
```

When running outside Docker, update the proxy targets in `frontend/vite.config.js`:

```js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/auth': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
},
```

🔧 Dev server: http://localhost:5173

### 🌐 Localization

The UI defaults to **Russian** (`ru`). Use the **🌐** selector in the top-right corner to switch to **English** (`en`). The choice is stored in `localStorage` under `kangame-locale`.

- UI copy lives in `frontend/src/i18n/locales/`
- Card titles and event text are translated on the client using stable keys from the API (`card_key`, `event_key`)
- To add a language: create a new locale JSON file, register it in `frontend/src/i18n/index.js`, and add it to `availableLocales`

### 📦 Production build

```bash
cd frontend
npm run build
```

---

## 🧪 Testing

### Backend business logic (pytest)

`backend/tests/` exercises the game engine directly (no browser, no running server): WIP limits, worker/card eligibility rules, deploy bonuses & penalties, day-event effects, blockers, overdue handling, the full create → assign → pull → work → end-day lifecycle against a real Postgres instance, and demo-mode specifics (Day 9–15 scope, leaderboard exclusion, ownership isolation from real users' games, and the age-cutoff cleanup query).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
```

Point `DATABASE_URL` at a scratch Postgres database (tests create/drop tables and delete all rows on every run — never point it at your dev database):

```bash
export DATABASE_URL=postgresql+asyncpg://kanban:kanban@localhost:5432/kanban_test
pytest -v
```

### Frontend business logic (Vitest)

`frontend/src/stores/__tests__/gameStore.spec.js` unit-tests the Pinia game store — the client-side mirror of the backend's rules: WIP-limit gating for pulling/dropping cards, planning-phase guards, worker selection/assignment, how each API call (assign worker, pull card, start work, end day) updates local state, and — for demo games — that those same actions route through the unauthenticated `demoApi` instead of `gamesApi`. The API layer is mocked, so no backend or browser is required.

```bash
cd frontend
npm install
npm run test:unit         # single run
npm run test:unit:watch   # watch mode
```

### End-to-end (Playwright)

`frontend/e2e/` drives the real app in a browser against a running stack. Sign-in normally goes through an external OIDC provider that automated tests can't complete, so the suite authenticates via the test-only `POST /api/dev/test-login` endpoint described in [🔐 Authentication](#-authentication) — it's gated by `ENABLE_TEST_LOGIN` and 404s unless that flag is set.

1. Start an isolated test stack — `docker-compose.test.yml` enables the test-login endpoint; give it its own project name (`-p`) so it gets its own network/volumes instead of reusing your dev database, and its own host ports (`BACKEND_PORT` / `NGINX_PORT`) so it can run alongside a normal dev stack:
   ```bash
   # bash
   BACKEND_PORT=8001 NGINX_PORT=8080 docker compose -f docker-compose.yml -f docker-compose.test.yml -p kangame-test up -d --build
   ```
   ```powershell
   # PowerShell
   $env:BACKEND_PORT=8001; $env:NGINX_PORT=8080
   docker compose -f docker-compose.yml -f docker-compose.test.yml -p kangame-test up -d --build
   ```
2. Install Playwright's browser binary once:
   ```bash
   cd frontend
   npx playwright install chromium
   ```
3. Run the tests:
   ```bash
   npm run test:e2e       # headless
   npm run test:e2e:ui    # interactive UI mode
   ```
4. Tear down the test stack, including its volume, so test games don't pile up:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.test.yml -p kangame-test down -v
   ```

Tests target `http://localhost:8080` by default; override with the `E2E_BASE_URL` env var if you chose different ports.

Current coverage (`card-drag.spec.js`): dragging a card into a column that's already at its WIP limit is rejected and the card stays put; dragging a card into its next column moves it forward once WIP allows; and dragging a specific Backlog card moves exactly that card rather than the oldest card of its type.

### Continuous Integration

[`.github/workflows/backend-tests.yml`](.github/workflows/backend-tests.yml) runs on every pull request into `main` (and on push to `main`) that touches `backend/**` or `frontend/**`, as two parallel jobs:

- **backend-tests** — the pytest suite above, against a Postgres 16 service container
- **frontend-tests** — the Vitest suite above, via `npm ci && npm run test:unit`

Mark both as required status checks in the branch protection settings for `main` if PRs shouldn't merge on a red build.

---

## 🕹️ How to Play

0. 🔐 **Sign in** — Authenticate with your organization's OIDC account; the **New Game** button only appears once you're signed in. Not ready to sign in? Click **Try a demo instead** on the home page for a no-account, Day 9–15 preview — it isn't saved and can't be resumed (see [🎬 Demo Mode](#-demo-mode))
1. 🆕 **Start a game** — Click **New Game** on the home screen; your player name and a random game name are assigned automatically
2. 📅 **Play each day** — follow the daily routine below, from Day 9 to Day 35
3. 📈 **Check your flow** — Click the 📈 Analytics button in the header at any point during the game, or on the end-game summary screen, to see the Cumulative Flow Diagram, Lead/Cycle Time distributions, and Kanban flow metrics

The full rules, with the live card catalog and team numbers, are also in the app at **`/rules`** (📜 **Rules of the Game** on the home page; public, no sign-in needed).

### 📅 Your day, step by step

Pulls and assignments are only possible **before** Start Work; after it the board is frozen until the next day.

1. 📰 **Read the event** — the dialog shown when the previous day ended: someone falls ill or comes back, a defect blocks a card, a WIP limit changes, an urgent request arrives.
2. 🚀 **Deploy** — drag every card from **Test Done** to **Deployed** (and Exp. Test Done → Exp. Deployed). No WIP limit; cards deployed before Start Work already earn money today.
3. ⬅️ **Pull right to left** — drag cards one column forward: Dev Done → Test, then Analysis Done → Development, then Ready → Analysis. Each pull frees a slot in the stage the card leaves, which makes the next pull to the left possible.
4. ↑ **Refill Ready** — click **↑ Pull to Ready** on a Backlog card (or drag it) to commit to it; choose by value per day, size and deadlines.
5. 👥 **Assign the team** — drag a worker onto a card in Analysis/Development/Test, or click one or more workers and then a card. Several workers may stack on one card; click an assigned badge to unassign. Every idle worker is lost capacity.
6. ▶️ **Start Work** — every assigned worker rolls their points, finished stages move to their Done column, daily revenue from deployed cards is added; assignments are cleared.
7. 📋 **Review the work log** — who rolled what, which cards advanced or deployed.
8. 🌙 **End Day** — the day's event is applied, overdue deadline cards are removed (with a fine where one applies), metrics are recorded, the calendar advances.

### 🃏 Card Types

| Type | Behavior |
|------|----------|
| 🔵 Standard (S1–S50) | Regular features; once deployed, earn their value **every day** until the game ends |
| 🟡 Fixed date (F1–F5) | Deadline card: one-off bonus if deployed on time (positive value) or a fine if not deployed on time (negative value) |
| 🔴 Expedite (E1–E4) | Urgent request announced by a day event; own lane and WIP limit; large one-off payment if delivered on time, or a fine if not |
| ⚪ Intangible (I1–I5) | Tech work; no revenue, but a permanent +1 to every future roll of one role |

---

## 📜 Rules of the Game

The numbers below come from `backend/app/data/cards.py` and `services/game_engine.py`; `GET /api/rules` serves the same numbers to the in-app rules page, and the AI agent's instructions are generated from them too.

### 🎯 Goal

Run a software team's Kanban board from **Day 9 to Day 35** and finish with the highest total revenue. Money comes **only** from cards that reach Deployed — a card stuck anywhere else earns nothing, however far along it is.

### 🔄 Columns, Pulling & WIP

Flow: **Backlog → Ready → Analysis → Analysis Done → Development → Dev Done → Test → Test Done → Deployed**, with a parallel Expedite track (**Exp. Backlog → Exp. Ready → Exp. Analysis → … → Exp. Deployed**) that appears once an expedite card is announced.

- **Analysis, Development and Test** are *working* columns — only there can people work on a card. Each has a *Done* column where a finished card waits.
- A card moves in exactly two ways: **automatically** into its stage's Done column when the stage's remaining points reach 0 during Start Work, or **by your pull** — one column at a time — for every other move. Nobody moves cards for you.
- **WIP limits** count a stage's working and Done columns together (Analysis = Analysis + Analysis Done, etc.). Starting limits: **Ready 5 · Analysis 3 · Development 5 · Test 3 · Expedite 1** (Exp. Ready). A pull into a full stage is rejected, so you free a stage by pulling its finished cards onward — always right to left. Day events change limits mid-game (e.g. Ready drops to 3).

### 👥 Team & Capacity

Three roles — **Analyst**, **Developer**, **Tester** — share a roster of 12 workers (`a1–a4`, `d1–d4`, `t1–t4`). A game starts with 7 active: **a1, a2, d1, d2, t1, t2, t3**. The others join, and active workers leave or return, only through day events (hiring, illness, vacation, conference, resignation, restructuring). Inactive workers can't be assigned.

Each Start Work, every assigned worker rolls a uniform random whole number of points in their range for the card's **current stage**, plus any buff:

| Stage | Analyst | Developer | Tester |
|---|---|---|---|
| Analysis | **1–6** (avg 3.5) | 1–4 (avg 2.5) | 1–4 (avg 2.5) |
| Development | 1–3 (avg 2) | **3–7** (avg 5) | 2–4 (avg 3) |
| Testing | 2–5 (avg 3.5) | 2–5 (avg 3.5) | **3–7** (avg 5) |

- Expected daily capacity of the starting team with everyone in their own stage: **Analysis ≈ 7, Development ≈ 10, Test ≈ 15 points**.
- Days to finish a stage ≈ points left ÷ the sum of the assigned workers' averages. One worker works one card per day; several workers on one card add up; points beyond what a stage needs are lost.
- **Blockers** (day events): each worker assigned to a blocked card rolls 1d6 against the blocker (5–7 points) instead of working; once it's cleared, leftover points go into the card. Anyone can clear a blocker.
- **Buffs**: each deployed intangible card adds +1 to every future roll of one role.

### 📏 Card Estimates

Every card has an Analysis / Development / Test estimate in points (3–10 per stage). Standard cards are worth **4,200–9,100 ₽ per day**; S1–S13 start on the board already partly done (S1–S3 in Test, S4–S5 in Dev Done, S6–S7 in Development, S8 in Analysis Done, S9–S10 in Analysis, S11–S13 with F1 and I1 in Ready), and later backlog cards are smaller (≈ 3–8 points per stage). Special cards:

| Card | A / D / T | Value | Due |
|---|---|---|---|
| F1 | 3 / 3 / 3 | +10,500 ₽ bonus | end of Day 15 |
| F2 | 4 / 5 / 3 | −35,000 ₽ fine | end of Day 20 |
| F3 | 8 / 9 / 8 | +7,000 ₽ bonus | end of Day 25 |
| F4 | 6 / 7 / 5 | +14,000 ₽ bonus | end of Day 30 |
| F5 | 5 / 6 / 4 | −21,000 ₽ fine | end of Day 28 |
| I1–I5 | 3–6 / 4–9 / 3–7 | +1 buff: developer (I1, I3), analyst (I2), tester (I4, I5) | — |

The complete catalog is in [`backend/app/data/cards.py`](backend/app/data/cards.py) and on the `/rules` page. Expedite cards are revealed only when a day event announces them.

### 💰 Revenue, Bonuses & Penalties

- **Standard** cards pay their value **every day** once deployed, counted at each Start Work — so a card deployed before Start Work earns that same day, and earlier deployment means more paying days.
- **Fixed-date** cards pay nothing daily. Positive value: one-off bonus if deployed by the end of the due day, nothing if late. Negative value: a fine if the card is not deployed on time.
- **Expedite** cards: positive value = payment if deployed on time; negative value = a fine if *not* deployed on time (delivering on time costs nothing).
- **Intangible** cards earn no revenue; they grant the permanent +1 buff.
- **Overdue rule**: a fixed-date or expedite card still on the board (Ready or further, or anywhere in the expedite lane) at the end of its due day is removed; a negative-value card then charges its fine. Fixed-date cards never pulled out of the Backlog are not removed.

### 🎲 Day Events

Ending a day (Day 9 through Day 35) triggers that day's scripted event, the same in every game: a worker leaving or returning, a blocker on the first card in Test or Development, a WIP-limit change, the "Carlos" testing-quality policy toggling on/off, a late-game "specialization lockdown" notice, and the four Expedite cards being announced with their own deadlines and payouts. Event notifications are shown in your selected UI language (see [🌐 Localization](#-localization)).

### 🏆 Scoring

The game ends after Day 35. Your final rank is based on total revenue earned:

| Total revenue | Rank |
|---|---|
| ≥ ₽700,000 | 🏆 Kanban Master |
| ≥ ₽500,000 | 🥇 Flow Expert |
| ≥ ₽300,000 | 🥈 Lean Practitioner |
| ≥ ₽150,000 | 🥉 Agile Starter |
| below ₽150,000 | 📚 Keep Learning |

### 💡 Tips

- Stop starting, start finishing: deploy first, then pull right to left.
- Swarm: put two or three people on one card so it finishes its stage today.
- Never leave anyone idle — a specialist with nothing in their stage helps the nearest stage downstream.
- Pull fixed-date and expedite cards early enough to make it through every stage.
- Intangible cards pay off only if many days remain to use the buff.

---

## 🔌 API Endpoints

All `/api/games*` routes require a signed-in session and only operate on games owned by the current user (others 404, not 403, to avoid leaking existence). `GET /api/leaderboard`, `GET /api/rules` and all `/api/demo*` routes are the exceptions — they're public and require no session.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/login` | Redirect to the OIDC provider's authorize endpoint |
| `GET` | `/auth/signin-oidc` | OIDC provider callback — exchanges the code, establishes the session |
| `GET` | `/api/auth/me` | Current authenticated user (401 if not signed in) |
| `POST` | `/api/auth/logout` | Clear the session |
| `POST` | `/api/dev/test-login` | **Test-only.** Disabled by default (404) unless `ENABLE_TEST_LOGIN=true`; bypasses OIDC for e2e tests — see [🧪 Testing](#-testing) |
| `GET` | `/api/leaderboard` | **Public, no auth required.** Top 5 users by their best completed game's revenue |
| `GET` | `/api/leaderboard/agents` | **Public, no auth required.** Top 10 finished AI agent runs: agent name, LLM model, who launched it, revenue (base URLs are never exposed) |
| `GET` | `/api/rules` | **Public, no auth required.** Rule numbers from the engine: productivity ranges, WIP limits, roster, card catalog (without expedite cards), rank thresholds |
| `POST` | `/api/games` | Create a new game, owned by the current user |
| `GET` | `/api/games` | List the current user's games |
| `GET` | `/api/games/{id}` | Get game state |
| `POST` | `/api/games/{id}/assign-worker` | Assign or unassign one worker to/from a card |
| `POST` | `/api/games/{id}/pull-card` | Pull one card forward by exactly one column (Backlog→Ready, Ready→Analysis, Analysis Done→Development, Dev Done→Test), subject to the destination's WIP limit |
| `POST` | `/api/games/{id}/start-work` | Resolve assigned worker output for the day and return the work log |
| `POST` | `/api/games/{id}/end-day` | Apply day-end events, metrics, overdue checks, and advance the day |
| `GET` | `/api/games/{id}/actions` | Player action log for the game (human or agent), oldest first; `?after_seq=` for incremental reads |
| `POST` | `/api/agent/runs` | Start an AI agent run (`name`, `base_url`, `model`, `api_key`); 409 if one is already active |
| `GET` | `/api/agent/runs` | List the current user's agent runs |
| `GET` | `/api/agent/runs/{id}` | Run status and latest actions; `?after_seq=` returns only newer actions (polling) |
| `GET` | `/api/agent/runs/{id}/actions` | Page back through older actions (`?before_seq=&limit=`) |
| `GET` | `/api/agent/runs/{id}/log` | Download the full run log as JSON |
| `POST` | `/api/agent/runs/{id}/cancel` | Stop an active run at the next tool call |
| `POST` | `/api/demo` | **Public, no auth required.** Create a new demo game (Day 9–15, excluded from the leaderboard) |
| `POST` | `/api/demo/{id}/assign-worker` | Same as the authenticated route, scoped to the demo game |
| `POST` | `/api/demo/{id}/pull-card` | Same as the authenticated route, scoped to the demo game |
| `POST` | `/api/demo/{id}/start-work` | Same as the authenticated route, scoped to the demo game |
| `POST` | `/api/demo/{id}/end-day` | Same as the authenticated route, scoped to the demo game; reaches `completed` status at Day 15 |

Note there's no `GET /api/demo/{id}` — see [🎬 Demo Mode](#-demo-mode) for why.

---

## 🙏 Attribution

This project is a digital adaptation inspired by **getKanban®** by agile42. Game mechanics and card data are ported from the reference implementation [shtaked32-code/kanbangame](https://github.com/shtaked32-code/kanbangame). getKanban is a registered trademark of agile42. This repository is an independent educational project and is not affiliated with or endorsed by agile42.

Developed with 🤖 AI coding assistants ([Claude Code](https://claude.ai/code), [Cursor](https://cursor.com)) under human direction.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
