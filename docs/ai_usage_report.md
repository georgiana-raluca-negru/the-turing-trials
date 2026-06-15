# AI Usage Report — The Turing Trials

> This document describes how AI tools were used during the development of **The Turing Trials**, an interactive multi-agent courtroom simulation. Each team member documents the AI tools they used, the tasks they delegated, and how the AI contributed to their area of responsibility.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Georgiana-Raluca Negru](#georgiana-raluca-negru)
- [Giulia Poalelungi](#giulia-poalelungi)
- [Colleagues](#colleagues)

---

## Project Overview

**The Turing Trials** is a full-stack web application that simulates a courtroom environment using a multi-agent LLM architecture. The stack consists of:

- **Frontend**: Next.js 14 (TypeScript, App Router, Tailwind CSS)
- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL 16
- **AI Layer**: LangGraph orchestration with MiniMax-Text-01 via an OpenAI-compatible endpoint
- **Infrastructure**: Docker + Docker Compose, Nginx reverse proxy, Ubuntu VPS, GitHub Actions CI/CD

---

## Georgiana-Raluca Negru

### AI Tool Used

| Tool | Model | Access Method |
|------|-------|---------------|
| Claude Code (Anthropic) | Claude Sonnet 4.6 | CLI (`claude` command in terminal) |

Claude Code is an agentic AI coding assistant that operates directly in the terminal with access to the file system, shell, and Git. It was used interactively throughout development — not just for code generation, but for architecture decisions, debugging, infrastructure setup, and deployment troubleshooting.

---

### Areas of Contribution

#### 1. Project Architecture

Claude assisted in designing and implementing the overall full-stack architecture from scratch:

- **Backend structure**: defined the FastAPI project layout with separation between `app/` (HTTP layer: routers, models, schemas, services) and `llm_functionality/` (AI engine: LangGraph agents, state machines, adapters). This separation keeps the LLM orchestration logic fully decoupled from the REST API.
- **Docker Compose setup**: defined the three-service compose file (`db`, `backend`, `frontend`) with correct dependency ordering, health checks, and environment variable injection.

#### 2. Objection Feature

Claude implemented the end-to-end **Objection mechanic** (one of the key gameplay features):

- **DB migration**: added `prosecution_objection_used` and `defense_objection_used` boolean columns to `game_sessions`.
- **AI prompt injection**: modified the Prosecutor and Defense agent prompts to react to a pending objection in the state, forcing them to address the disputed argument head-on in their next turn.
- **Frontend**: added the Objection button in the courtroom UI (`courtroom/[matchID]/page.tsx`), with disabled state after use and visual feedback.
- **Bug fix during implementation**: resolved an `ObjectionResponse` import that was unused after a refactor, caught by `ruff` in CI.

#### 3. DevOps — Nginx & Server Deployment

Claude guided the full deployment of the application to an Ubuntu Server:

- **Nginx configuration**: set up Nginx as a reverse proxy routing `/api/` and `/ws/` traffic to the FastAPI backend container and all other traffic to the Next.js frontend container. Configured `proxy_pass`, `proxy_http_version 1.1`, and WebSocket upgrade headers for real-time trial updates.
- **Environment configuration**: identified that `NEXT_PUBLIC_API_URL` is baked into the Next.js bundle at build time (not runtime), so `docker compose up --build` is always required after changing the domain. Diagnosed that `docker compose restart` does NOT re-read `.env` (env vars are injected at container creation), so `docker compose up -d` must be used after `.env` changes.
- **Database migrations**: prepared ALTER TABLE commands for adding new columns to live production databases (e.g. for the objection columns), packaged as copy-paste commands for safe execution on the server.
- **Deployment checklist**: produced a step-by-step deployment procedure: pull latest code → update `.env` (especially `NEXT_PUBLIC_API_URL` and `OPENAI_API_KEY`) → run DB migration → `docker compose up --build -d` → verify containers → check Nginx.
- **API key debugging**: diagnosed a production issue where the MiniMax LLM API key was not being picked up. Root cause: the key was added to `.env` but the container was only restarted (not recreated), so the new env var was never injected. Fix: `docker compose up -d`.

#### 4. CI/CD Pipeline

Claude implemented the GitHub Actions CI/CD pipeline:

- **Backend CI** (`backend-ci.yml`): runs `ruff` (lint + format check) and `mypy` (type checking) on every push and pull request targeting `main`.
- **Frontend CI** (`frontend-ci.yml`): runs `eslint` and `tsc --noEmit` (TypeScript type check) on every push and pull request.
- **Pipeline fixes**: resolved multiple CI failures — removed unused imports caught by `ruff`, fixed ESLint errors in TSX files (unused variables, missing dependencies in `useEffect` hooks), and resolved TypeScript strict-mode violations.

#### 5. Runtime Bug Fixes

Claude diagnosed and fixed several runtime bugs encountered during testing:

- **Evidence cross-role title collision** (`game_service.py`): `_get_evidence_code` mapped a DB UUID to a runtime evidence code by searching all evidence lists (prosecution + defense + shared) in order. If the AI generated a prosecution and a defense card with the same title, the prosecution card's code was returned for the defense player's evidence, failing the `allowed_ids` validation check. Fixed by scoping the title search to the evidence list matching the card's DB `assigned_role`.
- **Evidence display in messages**: fixed evidence cards not rendering correctly inside argument message bubbles in the courtroom view.

---

### How Claude Code Was Used in Practice

Claude Code was used in an **interactive, conversational** style — not as a one-shot code generator. The typical workflow was:

1. **Describe the feature or problem** in natural language (e.g. "implement the objection feature", "the evidence attachment gives a 500 error").
2. **Claude reads the relevant files** autonomously, traces the code path, identifies the root cause or the right place to implement the feature.
3. **Claude proposes the approach** and either waits for confirmation or proceeds directly with edits.
4. **Claude runs shell commands** (lint, tests, `git log`) to verify correctness before reporting the task done.
5. **Claude commits the changes** with descriptive commit messages when asked.


---

## Giulia Poalelungi

### Backend Responsibilities

I was responsible for the **backend** of the application: wiring the FastAPI API layer to the pre-existing `llm_functionality/backend_integration` contract, implementing the full game session lifecycle, configuring Docker/environment, and fixing authentication bugs. All backend work was done using AI agentic assistants.

---

### AI Tool Used

| Tool | Model | Access Method |
|------|-------|---------------|
| Antigravity IDE (Google DeepMind) | Claude Opus 4.6 (Thinking) | IDE integrated agent with terminal, file system, and Git access |

Antigravity IDE is an agentic coding assistant embedded in the editor. It has direct access to the project file system, can run shell commands (PowerShell), interact with Git, install tools (e.g. GitHub CLI), and manage GitHub issues — all autonomously within a single conversation.

---

### Areas of Contribution

#### 1. Full Backend Integration (1,361 lines in a single session)

The most significant use of AI was delegating the **entire backend integration** to the agent in a single prompt: *"Read the .md and folder to get context of this project. Then implement all backend functionalities needed, based on description and llm-functionality already implemented."*

The agent autonomously:
- **Read and understood** the `backend_integration/README.md` (825 lines of contract documentation) and the existing codebase structure.
- **Produced an implementation plan** covering 8 components (configuration wiring, in-memory state store, game orchestration service, evidence router, sessions router, match creation, scales of justice sync, win tracking) and asked for approval before writing any code.
- **Generated 1,361 lines of code across 13 files** in ~11 minutes:

| File | Lines | Purpose |
|------|-------|---------|
| `game_service.py` | 727 | Central orchestrator bridging FastAPI ↔ backend_integration |
| `sessions.py` | 403 | 7 API endpoints for the full game lifecycle |
| `evidence.py` | 121 | Role-filtered evidence list + detail endpoints |
| `game_store.py` | 43 | Thread-safe in-memory `MatchRuntimeState` store |
| + 9 other files | — | Config, Dockerfile, docker-compose, schemas, requirements |

- **Verified syntax** of all generated files by running `python -c "import ast; ast.parse(...)"` on each one.
- **Generated architecture diagrams** (see [`docs/diagrams/backend_architecture.md`](diagrams/backend_architecture.md) and [`docs/diagrams/match_lifecycle_sequence.md`](diagrams/match_lifecycle_sequence.md)) documenting the layer stack and the full match lifecycle sequence.

The architecture diagram generated by the AI:

```mermaid
graph TD
    A["FastAPI Routes<br/>(sessions.py, evidence.py)"] --> B["Game Service<br/>(game_service.py)"]
    B --> C["Game Store<br/>(game_store.py)<br/>In-Memory State"]
    B --> D["backend_integration<br/>Contract Layer"]
    B --> E["Database<br/>(SQLAlchemy ORM)"]
    D --> F["ai_engine<br/>LangGraph Agents"]
    F --> G["LLM Provider<br/>(Minimax API)"]
```

The actor-to-role mapping designed by the AI:

| PlayerRole | Prosecution | Defense | Judge | Experience |
|---|---|---|---|---|
| `defense_attorney` | AI | **HUMAN** | AI | Player argues for the defendant |
| `prosecutor` | **HUMAN** | AI | AI | Player argues against the defendant |
| `judge` | AI | AI | **HUMAN** | Player watches debate, delivers verdict |
| `spectator` | AI | AI | AI | Fully automated match (watch only) |

#### 2. JWT Token Expiry Bug — Diagnosis, Fix, and GitHub Issue Management

A bug was reported: users were forced to re-authenticate after ~30 minutes of playing a match. I gave the agent one instruction: *"Verify auth tokens, it was reported that after 30mins the token expires. Create an issue for this on Git, solve it and close it. Close also other issues assigned to me."*

The agent performed the entire workflow autonomously:

1. **Diagnosis** — scanned `config.py`, `security.py`, `api.ts`, and the courtroom page. Identified two root causes: `ACCESS_TOKEN_EXPIRE_MINUTES` set to 30 min (shorter than a typical match), and no automatic token refresh in the frontend `apiFetch()`.
2. **Implementation** — rewrote `frontend/lib/api.ts` to add a transparent 401 interceptor: on token expiry, it calls `POST /api/auth/refresh` (using the httpOnly refresh cookie), stores the new access token, and retries the failed request once. Added deduplication for concurrent refresh attempts. Also increased `ACCESS_TOKEN_EXPIRE_MINUTES` from 30 → 120 as a safety net.
3. **GitHub workflow** — the agent noticed `gh` CLI was not installed, so it:
   - Installed GitHub CLI via `winget install --id GitHub.cli`
   - Authenticated via browser device flow (`gh auth login --web`)
   - Created issue [#25](https://github.com/georgiana-raluca-negru/the-turing-trials/issues/25) with full root-cause description
   - Committed the fix with message `fix: add transparent JWT auto-refresh to prevent mid-match session expiry (closes #25)`
   - Pushed to `giulia_branch`
   - Closed issue #25 with a comment referencing the commit
   - Found and closed issue [#13](https://github.com/georgiana-raluca-negru/the-turing-trials/issues/13) (JWT implementation — already completed)

All of this happened in a single conversation, without any manual intervention beyond approving the browser auth for GitHub CLI.

#### 3. Environment & Docker Configuration

During the backend integration session, the agent also handled infrastructure changes:

- **Dockerfile** — added `ENV PYTHONPATH="/app/llm_functionality:${PYTHONPATH}"` so `ai_engine` and `backend_integration` packages are importable from the FastAPI app without modifying the `llm_functionality/` code.
- **docker-compose.yml** — added pass-through of `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `DEFAULT_MODEL_NAME` environment variables to the backend container.
- **`.env.example`** — added template entries for LLM configuration variables.
- **`requirements.txt`** — added `json-repair` dependency (used by `parsers.py` in the AI engine).

---

### How Antigravity IDE Was Used in Practice

The workflow was **delegation-oriented** rather than conversational — I gave high-level instructions and the agent executed end-to-end:

1. **Delegate a task** in natural language (e.g. "implement all backend functionalities", "fix the token expiry and create a GitHub issue").
2. **The agent reads documentation and code** autonomously — in the backend integration case, it read 825 lines of contract docs, all existing routers, models, schemas, and the AI engine code before writing anything.
3. **The agent produces a plan and asks for approval** before making changes (implementation plan with 8 components, open questions, and a verification strategy).
4. **The agent implements, verifies, and commits** — writes code, runs syntax checks, generates documentation with diagrams, and commits with descriptive messages.
5. **The agent manages external tools** when needed — it installed GitHub CLI, authenticated, created issues, and closed them without being explicitly told how.

The key difference from my colleagues' usage: I used AI for **bulk generation of entire subsystems** (1,361 lines in one session) rather than iterative feature-by-feature development. This was very efficient but required careful post-review — a subtle evidence lookup bug was only discovered 3 weeks later during playtesting (see Georgiana's section: "Evidence cross-role title collision").

---

## Colleagues

> *Each team member should add their section below following the same structure: AI tool used, tasks delegated, and how the AI contributed.*

## Amalia-Elena Riclea

### Frontend Responsibilities

I was responsible for the entire frontend of the application (Next.js 14, TypeScript, App Router, Tailwind CSS), built with Claude Code as a pair-programming assistant throughout.

---

### AI Tool Used

| Tool | Model | Access Method |
|------|-------|---------------|
| Claude Code (Anthropic) | Claude Sonnet 4.6 | VS Code extension (agentic mode) |

Claude Code was used interactively inside the editor, with direct access to the file system, shell (PowerShell/Bash) and Docker, across the entire scope of the frontend work described below.

---

### Areas of Contribution

#### 0. Scope of the Frontend Task

The frontend task covered building and maintaining:

- **Pages**: homepage/landing page, `login`, `register`, `dashboard`, `setup` (case prompt + role + round configuration), `courtroom/[matchID]` (the main gameplay screen), plus `not-found` and global `error` pages.
- **Courtroom screen** (`/courtroom/[matchID]`): the chat-style transcript with role-colored message bubbles for Prosecutor, Defense and Judge; the argument input box with submit/Ctrl+Enter shortcut; the "Case Parameters" panel; the evidence inventory panel; the objection button; the Judge's verdict-submission UI (guilty/not-guilty + reasoning textarea with a minimum-length requirement); and the end-of-trial verdict overlay.
- **`ScalesOfJustice` component**: a live horizontal balance bar (green = Defense, red = Prosecution) driven by the `scales_value` returned from the backend.
- **`CaseSummary` and evidence components**: displaying the generated case background, charges, and role-specific evidence cards.
- **`Toast` / `ToastProvider`**: a global toast notification system for success/error/info feedback across the app.
- **`Spinner`** and loading states for async operations (session start, turn submission, verdict delivery).
- **Theming system** (`globals.css`): CSS custom properties for a dark/light theme (`--bg-page`, `--text-fg`, `--text-muted`, `--border-sub`, `--heading`, chat-bubble color variables per role), toggled via a `ThemeProvider`.
- **API integration layer** (`lib/api.ts`): `apiJson`/`apiFetch` helpers wrapping `fetch`, attaching the auth token from `localStorage`, and handling error responses consistently across the app.
- **Game-state logic**: mapping the backend transcript (`TranscriptEntry[]`) into chat messages per player role, tracking which evidence cards have been used, computing the displayed Scales of Justice score from the backend's `-1..+1` value, and a polling/spectator loop (`startSpectatorLoop`) that advances the match turn-by-turn for Judge/Spectator roles so the debate appears live.

#### 1. Console Error Fixes

Two recurring console errors on the homepage were diagnosed and fixed with Claude:

- **Hydration mismatch** (`app/page.tsx`): the `isLoggedIn` state was initialized with `typeof window !== "undefined" && !!localStorage.getItem(...)`, which renders differently on server vs. client. Fixed by initializing with `useState(false)` and syncing from `localStorage` inside a `useEffect`.
- **"Script tag" warning** (`app/layout.tsx`): a `<Script strategy="beforeInteractive">` was wrapped in a manual `<head>` element, which is unsupported in the App Router. Fixed by moving it into `<body>`, where Next.js automatically hoists `beforeInteractive` scripts to `<head>`.

Both fixes were verified via `eslint` and a full `npm run build` (all 9 routes building successfully).

#### 2. Error Pages Theming

The `not-found.tsx` and `error.tsx` pages had hardcoded `slate-*` Tailwind colors left over from an earlier iteration. With Claude's help, these were restyled to match the dark "cyber-courtroom" theme — replacing the hardcoded colors with the project's CSS theme variables (`--text-fg`, `--text-muted`, `--border-sub`, `--heading`), while intentionally keeping the red/orange "glitch" accent colors for the 404/500 numerals unchanged.

#### 3. Database Bug Fix — "Failed to Fetch" on Generate Simulation

The "Generate Simulation" button was returning a generic `Failed to fetch` error. Claude debugged it by cross-referencing the frontend code, the live backend container logs, and the SQLAlchemy models:

- Root cause: the `game_sessions` table in Postgres was missing two boolean columns (`prosecution_objection_used`, `defense_objection_used`) that were already defined in the Python model.
- The project uses `Base.metadata.create_all()`, which creates new tables but does **not** alter existing ones — so newly added model columns never reached the live database.
- Fix: ran `ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS ... DEFAULT false` for both columns directly against the running Postgres container, preserving all existing match data (verified via `\d game_sessions`).

#### 4. Homepage Redesign

The landing page (`app/page.tsx`, `app/globals.css`) was redesigned with Claude toward a "high-stakes, dark cyber-courtroom" aesthetic:

- Updated body text color to a crisp off-white (`#E2E8F0`) with `1.6` line-height across all sections.
- Replaced the hero copy and added a terminal-style **typing animation** component (`TypingSubtitle`) with a blinking cursor.
- Added a slow, **pulsing neon-green glow** (`pulse-glow` keyframes) to all primary CTA buttons.
- Added hover effects to the "How It Works" and "Rules of the Court" cards — a slight lift plus a neon-green shadow — and increased text sizes for readability.
- Added a subtle animated cyber-grid background and staggered fade-in-up entrance animations.

#### 5. Courtroom UI Redesign

The courtroom game layout (`app/courtroom/[matchID]/page.tsx`) was restructured with Claude:

- Converted the left "Case Parameters" panel into a **collapsible slide-out sidebar** to maximize chat space, with a toggle button (later restyled for better visibility/contrast).
- Replaced the static evidence list with a new **`EvidenceVault`** component: a compact "stack of case files" graphic that, on click, opens a fullscreen dark overlay where evidence cards are presented in a scrollable, snap-aligned carousel with floating/fan-in animations — fixing an earlier issue where cards overlapped and were too small to read.

---

### How Claude Code Was Used in Practice

The workflow was conversational and iterative:

1. **Describe the problem or desired change** in natural language (e.g. "fix this hydration error", "redesign the homepage to look like X", "why does this button do nothing").
2. **Claude inspects the relevant files** (frontend components, CSS, Docker config, backend models) to locate the root cause before proposing a fix.
3. **Claude implements the change**, then verifies it with `eslint` and `npm run build` for frontend changes, or direct SQL/`docker` commands for backend/infra changes.
4. **Claude explains trade-offs and asks before risky actions** (e.g. before modifying `.env`, restarting containers, or running `ALTER TABLE` on the database).

---

*Report compiled: June 2026*
