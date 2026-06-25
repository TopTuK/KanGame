# 🎮 KanGame

An interactive web simulation of Kanban methodology, inspired by [getKanban®](https://www.agile42.com/en/get-kanban/) — the Lean/Agile board game. Manage flow, limit WIP, handle different classes of service, and deliver value across 21 game days to maximize revenue.

> 🤖 **Built with AI assistance** — This project was created with help from [Claude Code](https://claude.ai/code) and [Cursor](https://cursor.com). Architecture, game logic, UI components, and infrastructure were developed through human–AI collaboration.

---

## ✨ Features

- 🎯 **Pull system** — Work flows right-to-left based on available capacity
- 🚧 **WIP limits** — Enforce constraints per column (Analysis, Development, Test)
- ⚡ **Classes of service** — Standard, expedite, fixed-date, intangible, and bug cards with distinct policies
- 📅 **Daily gameplay loop** — Resolve events, allocate team capacity, move cards, end the day
- 📊 **Metrics** — Track throughput, WIP, cycle time, and cumulative flow
- 💾 **Persistent games** — Save and resume games via PostgreSQL
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
| **Pinia store** (`gameStore`) | Client state, derived metrics (WIP counts, capacity), API orchestration |
| **i18n** (`i18n/`, `useGameContent`) | UI strings and translated card/event text keyed by `card_key` / `event_key` |
| **API service** (`api.js`) | Axios client; all server communication goes through `/api` |

The UI never encodes game rules. It renders server state and sends player actions (allocate, move, end day) back to the API.

**Key components:**

- `KanbanBoard` / `KanbanColumn` / `KanbanCard` — interactive board with drag-and-drop
- `ResourcePanel` / `CapacityPanel` — team members and daily capacity allocation
- `MetricsPanel` — throughput, cycle time, cumulative flow
- `EventModal` / `ScoreModal` — daily events and end-game summary
- `LanguageSelector` — in-app locale switcher (top-right)

### ⚙️ Backend — Application Layer

| Layer | Responsibility |
|-------|----------------|
| **API routes** (`api/routes/games.py`) | HTTP endpoints, validation, error handling |
| **Schemas** (`schemas/game.py`) | Pydantic request/response DTOs |
| **Game engine** (`services/game_engine.py`) | All Kanban rules: pull, WIP, capacity, revenue, events |
| **Data definitions** (`data/cards.py`) | Static card deck and daily event catalog |
| **Models** (`models/game.py`) | SQLAlchemy ORM entities |
| **Core** (`core/`) | Config, async DB session factory |

The **game engine** is the single source of truth for mechanics:

- Column flow: Options → Ready → Analysis → Development → Test → Deployed
- WIP enforcement per active column (expedite cards bypass limits)
- Per-role capacity allocation with randomized daily team output
- Revenue, penalties, and metric snapshots at end of day

### 🗄️ Data Layer

PostgreSQL stores the full game snapshot:

| Entity | Purpose |
|--------|---------|
| `Game` | Session metadata, day/phase, team config, WIP limits, revenue |
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
User drops card on column
    → KanbanCard emits move
    → gameStore.moveCard()
    → POST /api/games/{id}/move-card
    → game_engine.move_card()  (validates WIP, column rules)
    → DB update + refreshed GameResponse
    → store updates → UI re-renders
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| 🎨 Frontend | Vue 3, Vite, Pinia, Vue Router, vue-i18n, Tailwind CSS |
| 🐍 Backend | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic |
| 🗄️ Database | PostgreSQL 16 |
| 🐳 Infra | Docker Compose, Nginx |

---

## 📁 Project Structure

```
KanGame2/
├── backend/              # FastAPI API and game engine
│   └── app/
│       ├── api/          # REST routes
│       ├── core/         # Config and database
│       ├── data/         # Card and event definitions
│       ├── models/       # SQLAlchemy models
│       ├── schemas/      # Pydantic DTOs
│       └── services/     # Game engine logic
├── frontend/             # Vue 3 SPA
│   └── src/
│       ├── components/   # Board, cards, panels, modals, language selector
│       ├── composables/  # Shared logic (e.g. content translation)
│       ├── i18n/         # Locale files (ru, en) and vue-i18n setup
│       ├── stores/       # Pinia state
│       ├── services/     # API client
│       └── views/        # Home and game pages
├── nginx/                # Reverse proxy config
├── LICENSE               # MIT license
└── docker-compose.yml
```

---

## 🚀 Quick Start (Docker)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and Docker Compose

```bash
docker compose up --build
```

Open [http://localhost](http://localhost) in your browser.

| Service | URL |
|---------|-----|
| 🌐 App | http://localhost |
| 📖 API docs | http://localhost/api/docs |
| ❤️ Health | http://localhost/health |

To stop:

```bash
docker compose down
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

Create `backend/.env` (optional):

```env
DATABASE_URL=postgresql+asyncpg://kanban:kanban@localhost:5432/kanban
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

## 🕹️ How to Play

1. 🆕 **Start a game** — Enter your name and a game name on the home screen
2. 🃏 **Resolve the daily event** — Read and acknowledge the event card for the current day
3. 👥 **Allocate capacity** — Assign analyst, developer, and tester effort to cards in active columns
4. ↔️ **Move cards** — Pull work through the board (Options → Ready → Analysis → Development → Test → Deployed), respecting WIP limits
5. 🌙 **End the day** — Advance to the next day; deployed cards earn revenue
6. 🏆 **Win condition** — Maximize total revenue over 21 days while meeting fixed-date commitments and handling expedites

### 🃏 Card Types

| Type | Behavior |
|------|----------|
| 🔵 Standard | Regular features; earn revenue when deployed |
| 🟡 Fixed date | Must deploy by due day or incur penalties |
| 🔴 Expedite | Bypasses WIP limits; highest priority |
| ⚪ Intangible | Tech debt; no direct revenue |
| 🟠 Bug | Discovered during play; must be resolved |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/games` | Create a new game |
| `GET` | `/api/games` | List all games |
| `GET` | `/api/games/{id}` | Get game state |
| `POST` | `/api/games/{id}/resolve-event` | Resolve the current day's event |
| `POST` | `/api/games/{id}/allocate` | Allocate team capacity to cards |
| `POST` | `/api/games/{id}/move-card` | Move a card to a target column |
| `POST` | `/api/games/{id}/end-day` | End the current day |

---

## 🙏 Attribution

This project is a digital adaptation inspired by **getKanban®** by agile42. getKanban is a registered trademark of agile42. This repository is an independent educational project and is not affiliated with or endorsed by agile42.

Developed with 🤖 AI coding assistants ([Claude Code](https://claude.ai/code), [Cursor](https://cursor.com)) under human direction.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
