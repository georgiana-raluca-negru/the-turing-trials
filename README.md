# The Turing Trials

> **Interactive Multi-Agent Courtroom Simulation powered by LLMs**

[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [How to Play](#how-to-play)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Project Overview

**The Turing Trials** is a gamified web application that simulates a courtroom environment using a **multi-agent Large Language Model (LLM) architecture**. Rather than a simple chatbot, the platform orchestrates a turn-based legal battle where human players and autonomous AI agents take on the roles of **Defense Attorney**, **Prosecutor**, and **Judge**.

The core innovation is the **AI Clerk Agent**, which dynamically generates a complete, structured case file from a single 1–2 sentence prompt. To prevent hallucinations, the prosecution and defense agents are strictly constrained to argue using only the generated **Evidence Inventory**. Players strategically attach evidence cards to their arguments and can trigger a one-time **Objection** to challenge a flawed AI argument. Each match concludes with a motivated verdict from the AI Judge, and all results are persisted to the player's match history.

---

## Key Features

- **AI Clerk** — generates a complete structured case file (crime, charges, background story, evidence) from a 1–2 sentence prompt
- **Multi-role gameplay** — play as Defense Attorney, Prosecutor, Judge, or Spectator
- **Evidence Inventory** — role-specific evidence cards that must be attached to arguments; each card can only be used once
- **Objection Mechanic** — one-time challenge button that forces the opponent's AI to address a disputed argument head-on in their next turn
- **Scales of Justice** — visual progress bar that tilts toward prosecution or defense after the AI Judge scores each round
- **Spectator & Judge modes** — watch the full AI debate unfold turn-by-turn, or observe and then deliver your own verdict
- **Match History & Leaderboard** — persistent per-user record of roles, verdicts, win rate, and a global ranking board
- **Authentication** — secure email/password registration and login with JWT tokens

---

## How to Play

### 1. Create an account and log in

Register with your email and password. Your match history and win rate are saved to your profile.

### 2. Set up a trial

On the **Setup** page, provide:

- **Case prompt** — one or two sentences describing the scenario (e.g. *"An AI algorithm deleted a company's financial archive to prevent a simulated market collapse."*)
- **Your role** — choose how you want to participate (see roles below)
- **Number of rounds** — 3 (fast), 5 (standard), or 10 (deep analysis)

The AI Clerk generates the full case file — crime summary, charges, background story, and a set of evidence cards for each side — before the trial begins.

### 3. Choose your role

| Role | What you do |
|---|---|
| **Defense Attorney** | Argue that the defendant is not guilty. The prosecution is played by AI. |
| **Prosecutor** | Build the case for guilt. The defense is played by AI. |
| **Judge** | Watch the full AI debate, then deliver your own written verdict at the end. |
| **Spectator** | Watch the entire trial unfold automatically with no input required. |

### 4. The courtroom

The courtroom is a three-panel layout:

- **Left panel** — case summary (crime, charges, background story) and match status
- **Centre panel** — the debate chat, where arguments appear turn by turn
- **Right panel** — your Evidence Folder

Each side (prosecution / defense) argues in alternating turns. AI turns are generated automatically; when it is your turn the input area becomes active.

### 5. Evidence

Your Evidence Folder shows the cards assigned to your role. Each card has a title and a description. To submit a valid argument:

1. Click a card in the Evidence Folder to attach it
2. Write your argument in the text box
3. Submit — the card is marked as used and is no longer available

Each evidence card can only be used once per session. AI opponents follow the same rule.

### 6. Objection

Each side has **one objection** available per match. The **Objection!** button appears during your turn (after the opponent has just spoken). Use it when you believe the opponent's last argument is irrelevant or misleading.

When raised, the court logs the objection and the opponent's AI **must address it directly** before making any new points on their next turn. There is no text to write — it is a one-click action. The button permanently disappears after use.

### 7. Scales of Justice

After each round the AI Judge silently evaluates both sides and updates the **Scales of Justice** bar at the top of the screen. Green = defense advantage, red = prosecution advantage. The bar animates on every update so you can track momentum in real time.

### 8. Verdict

After all rounds are completed:

- If you are playing as **Defense Attorney or Prosecutor**, the AI Judge delivers a written verdict (Guilty / Not Guilty) with a reasoning summary and scores for both sides.
- If you are playing as **Judge**, you write your own verdict and reasoning after watching the debate. Your decision is saved as the official result.
- If you are a **Spectator**, the AI Judge delivers the verdict automatically.

The result is saved to your match history and counts toward your win rate on the leaderboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, TypeScript, Tailwind CSS |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async) |
| **Database** | PostgreSQL 16 |
| **AI / LLM** | MiniMax-Text-01 via OpenAI-compatible API; LangChain for multi-agent orchestration (AI Clerk, Prosecutor, Defense, Judge) |
| **Authentication** | JWT (python-jose / passlib), HTTP-only bearer tokens |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Server** | Ubuntu Server, Nginx (reverse proxy) |

---

## Project Structure

```
the-turing-trials/
├── .github/
│   └── workflows/              # CI/CD pipelines
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI route handlers
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── services/           # Business logic layer
│   └── llm_functionality/
│       ├── ai_engine/          # LLM agents (Clerk, Prosecutor, Defense, Judge)
│       └── backend_integration/# Runtime state machine and AI adapter
├── frontend/
│   ├── app/                    # Next.js App Router pages
│   └── components/             # Reusable UI components
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Local Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- [Git](https://git-scm.com/)
- An API key for an OpenAI-compatible LLM provider (the project ships configured for MiniMax-Text-01)

### 1. Clone the repository

```bash
git clone https://github.com/georgiana-raluca-negru/the-turing-trials.git
cd the-turing-trials
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
# Database
POSTGRES_USER=turing
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=turing

# Frontend — browser address for the backend API
NEXT_PUBLIC_API_URL=http://localhost:8001

# Auth
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>

# LLM provider (OpenAI-compatible)
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.minimax.io/v1
DEFAULT_MODEL_PROVIDER=minimax
DEFAULT_MODEL_NAME=MiniMax-Text-01
```

### 3. Start the application

```bash
docker compose up --build
```

This starts three containers:

| Container | Service | Port |
|---|---|---|
| `turing-db` | PostgreSQL 16 | internal only |
| `turing-backend` | FastAPI | `http://localhost:8001` |
| `turing-frontend` | Next.js | `http://localhost:3001` |

The database schema is created automatically on first startup.

### 4. Open the app

- **App:** [http://localhost:3001](http://localhost:3001)
- **API docs (Swagger):** [http://localhost:8001/docs](http://localhost:8001/docs)

### 5. Stop the application

```bash
docker compose down
```

To also delete the database volume (all data):

```bash
docker compose down -v
```

---

## Deployment

The application is deployed on an Ubuntu server with Nginx as a reverse proxy.

**Live URL:** [http://the-turing-trials.games](http://the-turing-trials.games)

### Nginx routing

- `GET /api/*` → FastAPI backend on `127.0.0.1:8001`
- Everything else → Next.js frontend on `127.0.0.1:3001`

### Production `.env`

```env
NEXT_PUBLIC_API_URL=http://the-turing-trials.games
JWT_SECRET_KEY=<strong random secret>
```

After editing `.env`, rebuild:

```bash
docker compose up --build -d
```

> `NEXT_PUBLIC_API_URL` is baked into the Next.js bundle at build time. A container restart alone is not enough — a full rebuild is required when this value changes.

---

## Contributing

Contributions, issues, and feature requests are welcome.

### 1. Open an issue

Before writing code, [open a GitHub Issue](https://github.com/georgiana-raluca-negru/the-turing-trials/issues/new) with a clear title and description. Add relevant labels (`bug`, `enhancement`, `documentation`) and wait for acknowledgement.

### 2. Fork and branch

```bash
git clone https://github.com/<your-username>/the-turing-trials.git
cd the-turing-trials
git checkout -b feature/42-short-description
```

Branch naming conventions:
- `feature/<N>-description` — new functionality
- `fix/<N>-description` — bug fixes
- `docs/<N>-description` — documentation
- `chore/<N>-description` — maintenance / refactoring

### 3. Commit and open a pull request

```bash
git commit -m 'feat: short description (closes #42)'
git push origin feature/42-short-description
```

Open a pull request against `main` and include `Closes #42` in the description so the issue closes automatically on merge.
