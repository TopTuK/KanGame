# 🎮 KanGame

An interactive web simulation of Kanban methodology, inspired by [getKanban®](https://www.agile42.com/en/get-kanban/) — the Lean/Agile board game. Manage flow, limit WIP, assign team resources, handle different classes of service, and deliver value from Day 9 through Day 35 to maximize revenue.

> 🤖 **Built with AI assistance** — This project was created with help from [Claude Code](https://claude.ai/code) and [Cursor](https://cursor.com). Architecture, game logic, UI components, and infrastructure were developed through human–AI collaboration.

---

## ✨ Features

- 🎯 **Pull system** — Work is pulled from backlog and between ready/done buffers based on available capacity
- 🚧 **WIP limits** — Enforce constraints per column (Analysis, Development, Test)
- 👥 **Resource assignment** — Click or drag workers onto active tasks; distribute the team across different cards or assign several workers to one card; specialists roll 2d6, cross-role workers roll 1d6
- ⚡ **Classes of service** — Standard, expedite, fixed-date, and intangible cards with distinct economic effects
- 📅 **Daily gameplay loop** — Pull cards, assign resources, start work, review the work log, and end the day
- 📊 **Metrics** — Track throughput, WIP, deployed work, daily revenue, and cumulative revenue
- 🔐 **Authentication** — Sign in with your organization's OIDC account before starting or resuming a game
- 💾 **Persistent, per-user games** — Save and resume your own games via PostgreSQL; each player only sees their own
- 🌐 **Localization** — Russian and English UI; Russian is the default; switch language from the header selector (preference saved in the browser)

---

## 🏗️ Architectural Decomposition

The system follows a **classic three-tier layout** with a clear split between presentation, application logic, and persistence. Game rules live exclusively on the backend; the frontend is a thin, reactive client.

```
┌─────────────────────────────────────────────────────────────────┐
│  🌐 Presentation (Vue 3 SPA)                                    │
│  Views → Components → Pinia Store → API Client                  │
│  vue-i18n (UI strings + client-side content translation)        │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST / JSON
┌────────────────────────────▼────────────────────────────────────┐
│  ⚙️ Application (FastAPI)                                       │
│  Routes → Schemas → Game Engine → Models                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ SQLAlchemy async
┌────────────────────────────▼────────────────────────────────────┐
│  🗄️ Persistence (PostgreSQL)                                    │
│  games · cards · events · metrics                               │
└─────────────────────────────────────────────────────────────────┘
```

### 🖥️ Frontend — Presentation Layer

| Layer | Responsibility |
|-------|----------------|
| **Views** (`HomeView`, `GameView`) | Page-level layout and routing entry points |
| **Components** | UI building blocks — board, columns, cards, modals, panels |
| **Pinia store** (`gameStore`) | Client state, derived WIP counts, worker selection, API orchestration |
| **i18n** (`i18n/`, `useGameContent`) | UI strings and translated card/event text keyed by `card_key` / `event_key` |
| **API service** (`api.js`) | Axios client; all server communication goes through `/api` |

The UI never encodes game rules. It renders server state and sends player actions (pull, assign resources, start work, end day) back to the API.

**Key components:**

- `GameHeader` — day progress, revenue, WIP badges, End Day control
- `KanbanBoard` / `KanbanColumn` / `KanbanCard` — board layout, per-card pull buttons, worker drop targets
- `ResourcePanel` — draggable worker pool, multi-select click assignment, Start Work
- `MetricsPanel` — throughput, WIP, deployed work, and revenue history
- `HelpModal` / `WorkLogModal` / `EndDayModal` / `ScoreModal` — onboarding, daily work log, day events, and end-game summary
- `LanguageSelector` — in-app locale switcher (top-right)

### ⚙️ Backend — Application Layer

| Layer | Responsibility |
|-------|----------------|
| **API routes** (`api/routes/games.py`) | HTTP endpoints, validation, error handling — every route requires a signed-in user and is scoped to their own games |
| **Auth routes** (`api/routes/auth.py`) | OIDC login redirect, provider callback, current-user lookup, logout |
| **Schemas** (`schemas/game.py`, `schemas/user.py`) | Pydantic request/response DTOs |
| **Game engine** (`services/game_engine.py`) | All Kanban rules: pull, WIP, worker assignment, dice rolls, revenue, events; every game lookup is filtered by owner |
| **Data definitions** (`data/cards.py`) | Static card deck and daily event catalog |
| **Models** (`models/game.py`, `models/user.py`) | SQLAlchemy ORM entities |
| **Core** (`core/`) | Config, async DB session factory, OIDC client (`oauth.py`), `get_current_user` dependency (`auth.py`) |

### 🔐 Authentication

KanGame uses a **backend-driven OIDC Authorization Code flow** (via [Authlib](https://authlib.org/)) against your organization's identity provider — the client secret never reaches the browser:

1. The frontend sends the user to `GET /auth/login`, which redirects to the provider's authorize endpoint.
2. The provider redirects back to `GET /auth/signin-oidc`; the backend exchanges the code, upserts a `User` row keyed by the OIDC `sub` claim, and stores `user_id` in a signed, `HttpOnly` session cookie (Starlette `SessionMiddleware`).
3. The browser is redirected back to the SPA. Every subsequent `/api/*` call is authenticated via that cookie through `get_current_user`.
4. `GET /api/auth/me` reports the current user to the frontend; `POST /api/auth/logout` clears the session.

Configure the provider in `.env` (see Quick Start and Local Development below) — `AuthClientId`, `AuthClientSecret`, `AuthAuthority`, `AuthCallbackUrl`, plus `SESSION_SECRET_KEY`, `FRONTEND_URL`, and `BACKEND_PUBLIC_URL`.

A separate, **test-only** login path (`POST /api/dev/test-login`) bypasses OIDC entirely; it 404s unless `ENABLE_TEST_LOGIN=true` and exists solely so the e2e suite can authenticate without a real identity provider — see [🧪 Testing](#-testing).

The **game engine** is the single source of truth for mechanics:

- Column flow: Backlog → Ready → Analysis → Analysis Done → Development → Dev Done → Test → Deployed
- Separate expedite track with its own ready/WIP handling
- Pull rules and WIP enforcement for ready, active, and done-buffer columns
- Worker assignment stored in `team_config.workers` (one worker → one card; many workers → same card allowed)
- Specialist/cross-role dice rolls at work time, blockers, Carlos/lockdown event flags, buffs
- Revenue, penalties, overdue removals, and metric snapshots at end of day

### 🗄️ Data Layer

PostgreSQL stores the full game snapshot:

| Entity | Purpose |
|--------|---------|
| `User` | OIDC identity (`sub`, email, name) — owns games |
| `Game` | Session metadata, day/phase, team config, WIP limits, revenue; belongs to a `User` |
| `Card` | Work items with story points, column, type, due dates |
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
| 🎨 Frontend | Vue 3, Vite, Pinia, Vue Router, vue-i18n, Tailwind CSS |
| 🐍 Backend | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic |
| 🔐 Auth | Authlib (OIDC client), Starlette `SessionMiddleware` (signed session cookies) |
| 🗄️ Database | PostgreSQL 16 |
| 🐳 Infra | Docker Compose, Nginx |

---

## 📁 Project Structure

```
KanGame2/
├── backend/              # FastAPI API and game engine
│   ├── certs/            # Local self-signed TLS cert (gitignored, generated — see Quick Start)
│   └── app/
│       ├── api/routes/   # REST routes (games.py, auth.py)
│       ├── core/         # Config, database, OIDC client (oauth.py), get_current_user (auth.py)
│       ├── data/         # Card and event definitions
│       ├── models/       # SQLAlchemy models (game.py, user.py)
│       ├── schemas/      # Pydantic DTOs (game.py, user.py)
│       └── services/     # Game engine logic
├── frontend/             # Vue 3 SPA
│   ├── e2e/               # Playwright end-to-end tests (+ playwright.config.js)
│   └── src/
│       ├── components/   # Board, cards, panels, modals, language selector
│       ├── composables/  # Shared logic (e.g. content translation)
│       ├── i18n/         # Locale files (ru, en) and vue-i18n setup
│       ├── stores/       # Pinia state (gameStore.js, authStore.js)
│       ├── services/     # API client
│       └── views/        # Home and game pages
├── nginx/                # Reverse proxy config
├── LICENSE               # MIT license
├── docker-compose.yml
└── docker-compose.test.yml  # Test overlay: enables /api/dev/test-login, isolated ports
```

---

## 🚀 Quick Start (Docker)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/), Docker Compose, and OpenSSL

1. Create `.env` in the repo root (copy `.env.example`) with your OIDC provider's `AuthClientId`, `AuthClientSecret`, `AuthAuthority`, `AuthCallbackUrl=/auth/signin-oidc`, a random `SESSION_SECRET_KEY` (e.g. `openssl rand -hex 32`), and `FRONTEND_URL` / `BACKEND_PUBLIC_URL` (defaults `http://localhost` / `https://localhost:8000` work for local dev).
2. Generate a local self-signed TLS cert for the backend — the OIDC provider redirects to `https://localhost:8000`, so the backend must serve HTTPS there:
   ```bash
   mkdir -p backend/certs
   openssl req -x509 -newkey rsa:2048 -nodes -keyout backend/certs/localhost.key -out backend/certs/localhost.crt -days 365 -subj "/CN=localhost"
   ```
3. Start the stack:
   ```bash
   docker compose up --build
   ```
4. Visit `https://localhost:8000/health` once and accept the browser's self-signed-certificate warning — otherwise the provider's redirect back to the backend will fail silently.

Open [http://localhost](http://localhost) in your browser and sign in to start a game.

| Service | URL |
|---------|-----|
| 🌐 App | http://localhost |
| 📖 API docs | http://localhost/api/docs |
| ❤️ Health | http://localhost/health |
| 🔐 Backend (HTTPS, OIDC callback only) | https://localhost:8000 |

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
FRONTEND_URL=http://localhost
BACKEND_PUBLIC_URL=https://localhost:8000
SESSION_COOKIE_SECURE=false
```

Start the API — the registered OIDC callback is `https://localhost:8000`, so it must run over HTTPS using the self-signed cert generated in the Quick Start section above:

```bash
uvicorn app.main:app --reload --port 8000 --ssl-certfile certs/localhost.crt --ssl-keyfile certs/localhost.key
```

📖 API docs: http://localhost:8000/api/docs

### 🎨 Frontend

**Prerequisites:** Node.js 20+

```bash
cd frontend
npm install
npm run dev
```

When running outside Docker, update the API proxy in `frontend/vite.config.js`:

```js
proxy: {
  '/api': {
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

### End-to-end (Playwright)

`frontend/e2e/` drives the real app in a browser against a running stack. Sign-in normally goes through an external OIDC provider that automated tests can't complete, so the suite authenticates via the test-only `POST /api/dev/test-login` endpoint described in [🔐 Authentication](#-authentication) — it's gated by `ENABLE_TEST_LOGIN` and 404s unless that flag is set.

1. Start an isolated test stack — `docker-compose.test.yml` enables the test-login endpoint and remaps ports so it can run alongside a normal dev stack; give it its own project name so it gets its own network/volumes instead of reusing your dev database:
   ```bash
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

Tests target `http://localhost:8080` by default (the port `docker-compose.test.yml` maps nginx to); override with the `E2E_BASE_URL` env var if needed.

Current coverage (`backlog-pull.spec.js`): the Backlog column's per-type pull buttons render with live counts, a pull is rejected with the WIP-limit error while Ready is full, and a pull succeeds and moves a card into Ready once a slot is freed.

---

## 🕹️ How to Play

0. 🔐 **Sign in** — Authenticate with your organization's OIDC account; the new-game form only appears once you're signed in
1. 🆕 **Start a game** — Enter your name and a game name on the home screen
2. ↔️ **Pull cards** — Use **Pull →** on cards in Ready and Done-buffer columns to move work forward, respecting WIP limits
3. 👥 **Assign resources** — Drag a worker onto an Analysis/Development/Test card, or click one or more workers then click a card; assign each worker to a different task or stack several workers on one task; click an assigned badge to unassign
4. ▶️ **Start Work** — Roll worker output, reduce remaining analysis/development/test work, and automatically advance completed stages
5. 🌙 **End the day** — Apply daily events, remove overdue fixed-date/expedite work, record metrics, and advance the calendar
6. 🏆 **Win condition** — Maximize total revenue from Day 9 through Day 35 while meeting fixed-date commitments and handling expedites

### 🃏 Card Types

| Type | Behavior |
|------|----------|
| 🔵 Standard | Regular features; earn revenue when deployed |
| 🟡 Fixed date | Must deploy by due day or incur penalties |
| 🔴 Expedite | Uses the expedite track and has its own WIP limit |
| ⚪ Intangible | Tech debt; no direct revenue |

---

## 🔌 API Endpoints

All `/api/games*` routes require a signed-in session and only operate on games owned by the current user (others 404, not 403, to avoid leaking existence).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/login` | Redirect to the OIDC provider's authorize endpoint |
| `GET` | `/auth/signin-oidc` | OIDC provider callback — exchanges the code, establishes the session |
| `GET` | `/api/auth/me` | Current authenticated user (401 if not signed in) |
| `POST` | `/api/auth/logout` | Clear the session |
| `POST` | `/api/dev/test-login` | **Test-only.** Disabled by default (404) unless `ENABLE_TEST_LOGIN=true`; bypasses OIDC for e2e tests — see [🧪 Testing](#-testing) |
| `POST` | `/api/games` | Create a new game, owned by the current user |
| `GET` | `/api/games` | List the current user's games |
| `GET` | `/api/games/{id}` | Get game state |
| `POST` | `/api/games/{id}/assign-worker` | Assign or unassign one worker to/from a card |
| `POST` | `/api/games/{id}/pull-card` | Pull a card from Ready/Done buffer into the next active stage |
| `POST` | `/api/games/{id}/pull-backlog` | Pull a standard, fixed-date, or intangible card from Backlog into Ready |
| `POST` | `/api/games/{id}/pull-expedite` | Pull the next available expedite card into Exp. Ready |
| `POST` | `/api/games/{id}/start-work` | Resolve assigned worker output for the day and return the work log |
| `POST` | `/api/games/{id}/end-day` | Apply day-end events, metrics, overdue checks, and advance the day |

---

## 🙏 Attribution

This project is a digital adaptation inspired by **getKanban®** by agile42. Game mechanics and card data are ported from the reference implementation [shtaked32-code/kanbangame](https://github.com/shtaked32-code/kanbangame). getKanban is a registered trademark of agile42. This repository is an independent educational project and is not affiliated with or endorsed by agile42.

Developed with 🤖 AI coding assistants ([Claude Code](https://claude.ai/code), [Cursor](https://cursor.com)) under human direction.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
