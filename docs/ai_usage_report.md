# AI Usage Report — The Turing Trials

> This document describes how AI tools were used during the development of **The Turing Trials**, an interactive multi-agent courtroom simulation. Each team member documents the AI tools they used, the tasks they delegated, and how the AI contributed to their area of responsibility.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Georgiana-Raluca Negru](#georgiana-raluca-negru)
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

## Colleagues

> *Each team member should add their section below following the same structure: AI tool used, tasks delegated, and how the AI contributed.*

### [Colleague Name]

*(to be filled in)*

---

*Report compiled: June 2026*
