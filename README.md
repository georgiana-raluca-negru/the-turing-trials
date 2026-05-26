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
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
- [Deployment](#deployment)
- [Product Backlog - User Stories](#product-backlog---user-stories)
- [Contributing](#contributing)

---

## Project Overview

**The Turing Trials** is a gamified web application that simulates a courtroom environment using a **multi-agent Large Language Model (LLM) architecture**. Rather than a simple chatbot, the platform orchestrates a turn-based legal battle where human players and autonomous AI agents take on the roles of **Defense Attorney**, **Prosecutor**, and **Judge**.

The core innovation is the **AI Clerk Agent**, which dynamically generates structured case files (JSON) from a short user prompt. To prevent hallucinations, the prosecuting and defending agents are strictly constrained to argue using only the generated **Evidence Inventory**. Players must strategically attach evidence cards to their arguments and can trigger an **Objection** mechanic to interrupt flawed AI reasoning in real-time. Each match concludes with an objective verdict from the AI Judge, and results are persisted to the user's match history.

---

## Key Features

- **AI Clerk** — generates complete, structured case files from a 1-2 sentence prompt
- **Multi-role gameplay** — play as Defense Attorney, Prosecutor, Judge, or Spectator
- **Evidence Inventory** — role-specific evidence cards that must be attached to arguments
- **Objection Mechanic** — interrupt opponent's AI text generation with a live counter-argument
- **Scales of Justice** — real-time visual progress bar updated after each round by the AI Judge
- **Match History** — persistent per-user record of roles, verdicts, and case summaries
- **Authentication** — email/password and OAuth (Google / GitHub)

---

## Tech Stack

### Current

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14+, React, TypeScript, CSS Modules |
| **Backend** | Python, FastAPI, SQLAlchemy (async) |
| **Database** | PostgreSQL 16 |
| **AI / LLM** | Multi-agent LLM orchestration (AI Clerk, Defense, Prosecution, Judge agents) |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Server** | Ubuntu Server, Nginx (reverse proxy) |

### Planned

| Layer | Technology | Purpose |
|---|---|---|
| **Authentication** | Auth.js (NextAuth.js), python-jose / passlib | Google & GitHub OAuth, JWT token handling |
| **Real-time Communication** | WebSockets (FastAPI native), Socket.IO | Live objection mechanic, Scales of Justice updates |
| **LLM Orchestration** | LangChain / LangGraph + Streaming API | Multi-agent turn management, streamed text generation |
| **LLM Provider** | OpenAI / Anthropic / Google Gemini | Powering all AI agents (Clerk, Defense, Prosecution, Judge) |
| **Database Migrations** | Alembic | Safe schema versioning for SQLAlchemy models |
| **Frontend State** | Zustand / Redux Toolkit, TanStack Query | Global courtroom state, server-state caching |
| **Testing** | pytest, pytest-asyncio, Jest, React Testing Library, Playwright | Unit, integration & end-to-end tests |

---

## Project Structure

```
the-turing-trials/
├── .github/
│   └── workflows/          # CI/CD pipelines
├── backend/                # FastAPI application (Python)
├── frontend/               # Next.js application (TypeScript)
├── docs/                   # Project documentation
├── docker-compose.yml      # Multi-service orchestration
├── .env.example            # Environment variable template
└── README.md
```

---

## Local Setup

### Prerequisites

Make sure you have the following installed on your machine:

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- [Git](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/georgiana-raluca-negru/the-turing-trials.git
cd the-turing-trials
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and update the following variables:

```env
# --- DATABASE CONFIG ---
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_local_password_here
POSTGRES_DB=turing_db

# --- FRONTEND CONFIG ---
# For local dev, the browser accesses the backend on localhost:8001
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### 3. Start the Application

```bash
docker compose up --build
```

This will spin up three services:

| Service | Container | Exposed Port |
|---|---|---|
| PostgreSQL 16 | `turing-db` | internal only |
| FastAPI Backend | `turing-backend` | `http://localhost:8001` |
| Next.js Frontend | `turing-frontend` | `http://localhost:3001` |

### 4. Access the App

- **Frontend:** [http://localhost:3001](http://localhost:3001)
- **Backend API / Docs:** [http://localhost:8001/docs](http://localhost:8001/docs)

### 5. Stopping the Application

```bash
docker compose down
```

To also remove the persisted database volume:

```bash
docker compose down -v
```

---

## Deployment

The application is hosted on an Ubuntu server with Nginx configured as a reverse proxy.

The live URL is: [http://the-turing-trials.games](http://the-turing-trials.games)

### Nginx configuration

Nginx listens on port 80 and routes traffic to the two containers:

- `GET /api/*` → FastAPI backend on `127.0.0.1:8001`
- Everything else → Next.js frontend on `127.0.0.1:3001`

### Production `.env` values

For a production deployment update your `.env` with the following before rebuilding:

```env
# Point the browser at the public domain so Nginx can route /api/* to FastAPI
NEXT_PUBLIC_API_URL=http://the-turing-trials.games

# Use a strong random secret — never use the default placeholder
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
```

After editing `.env`, rebuild and restart the containers:

```bash
docker compose up --build -d
```

> **Note:** `NEXT_PUBLIC_API_URL` is baked into the Next.js bundle at build time (Docker build arg).
> Changing it requires a full rebuild — a container restart alone is not enough.

---

## Product Backlog - User Stories

### Authentication & User Account

| ID | Story |
|---|---|
| US1 | As a visitor, I want to register using my email and password (or via Google/GitHub), **so that** I can have a dedicated profile on the platform. |
| US2 | As an authenticated user, I want to securely log out, **so that** I can protect my personal data on shared devices. |
| US3 | As a user, I want a Dashboard showing my match history (role played, case summary, verdict, date), **so that** I can track my progress and overall win rate. |

### AI Clerk & Match Setup

| ID | Story |
|---|---|
| US4 | As a player, I want to input a short prompt (1-2 sentences) describing the trial idea, **so that** I can provide a starting point for the case generation engine. |
| US5 | As a player, I want to select my role (Defense Attorney, Prosecutor, Judge, or Spectator), **so that** I can determine my level of interaction in the trial. |
| US6 | As a player, I want evidence distributed only to my appropriate role (e.g., Defense only sees defense evidence), **so that** strategic competition and surprise are maintained. |

### Courtroom UI & Evidence Inventory

| ID | Story |
|---|---|
| US7 | As a player, I want a fixed summary of the case (Crime and Charges) always visible, **so that** I don't lose track of essential details during debates. |
| US8 | As a playing attorney/prosecutor, I want a visual "Evidence Folder" displaying cards I can consult, **so that** I can build my trial strategy. |
| US9 | As a player, I want to select an evidence card and attach it to my argument draft, **so that** I can submit a valid, fact-based argument to the court. |
| US10 | As a player, I want used evidence cards to be marked or removed from my folder, **so that** I am challenged to produce new arguments each round. |

### AI Interaction & Objection Mechanic

| ID | Story |
|---|---|
| US11 | As a player, I want an "Objection" button active only during my opponent's turn, **so that** I can pause their text generation and input a reason to contest their argument. |

### AI Judge, Scales of Justice & Verdict

| ID | Story |
|---|---|
| US12 | As a player, I want a visual "Scales of Justice" progress bar that tilts toward me or my opponent after each round, **so that** I can monitor the match score in real-time. |
| US13 | As the Judge, I want to end the trial after a predefined number of rounds, analyze the chat history alongside the Scales of Justice, and generate a motivated final verdict (Guilty / Not Guilty) saved to the database, **so that** I can officially close the game session. |

---

## Contributing

Contributions, issues, and feature requests are welcome! Please follow the workflow below to keep the project history clean and traceable.

### 1. Open an Issue

Before writing any code, [open a GitHub Issue](https://github.com/georgiana-raluca-negru/the-turing-trials/issues/new) describing what you want to fix or add.

- Use a clear, descriptive title (e.g. `[Bug] Objection button visible during own turn` or `[Feature] Add spectator chat panel`)
- Describe the problem or feature request in detail
- Add relevant labels (e.g. `bug`, `enhancement`, `documentation`)
- Wait for the issue to be acknowledged/assigned before proceeding

### 2. Fork & Create a Dedicated Branch

Fork the repository and create a branch that references the issue number:

```bash

git clone https://github.com/<your-username>/the-turing-trials.git
cd the-turing-trials

# Create a branch linked to your issue
# Format: <type>/<number>-short-description
git checkout -b feature/42-spectator-chat-panel
```

> **Branch naming conventions:**
> - `feature/<N>-description` — new functionality
> - `fix/<N>-description` — bug fixes
> - `docs/<N>-description` — documentation updates
> - `chore/<N>-description` — maintenance / refactoring

### 3. Commit, Push & Open a Pull Request

```bash
# Make your changes, then commit
git commit -m 'feat: add spectator chat panel (closes #42)'

# Push your branch
git push origin feature/42-spectator-chat-panel
```

Then open a Pull Request against `main`. In the PR description, use one of the GitHub closing keywords so the issue is automatically closed when the PR is merged:

```
Closes #42
```
---