# Product Backlog — The Turing Trials

This document tracks all user stories for the project, organized by feature area. Each story follows the format: *As a [role], I want [feature], **so that** [benefit].*

---

## Status Legend

| Status | Meaning |
|--------|---------|
| Done | Fully implemented and working |
| Partial | Implemented with known gaps |
| Not Started | Planned but not yet implemented |

---

## US1 — Authentication & User Account

| ID | Status | User Story |
|----|--------|------------|
| US1 | Partial | As a visitor, I want to register using my email and password, **so that** I can have a dedicated profile. *(OAuth via Google/GitHub is not yet implemented.)* |
| US2 | Done | As an authenticated user, I want to securely log out, **so that** I can protect my data on shared devices. |
| US3 | Done | As a user, I want a Dashboard showing my match history (role, case summary, verdict, date) and a global leaderboard, **so that** I can track my performance. |

### Acceptance Criteria

**US1 — Registration**
- User can register with a unique email and password
- Duplicate email is rejected with a clear error message
- Password is stored hashed (never in plain text)
- *(OAuth login via Google/GitHub: not implemented)*

**US2 — Logout**
- Authenticated user can log out from any page
- JWT token is invalidated on logout
- User is redirected to the login page

**US3 — Dashboard**
- Dashboard lists all past matches with: role played, case summary, verdict, date
- Global leaderboard shows all users ranked by win rate
- Stats update immediately after a match is completed

---

## US2 — AI Clerk & Match Setup

| ID | Status | User Story |
|----|--------|------------|
| US4 | Done | As a player, I want to input a short prompt describing the trial idea, **so that** I can provide a starting point for case generation. |
| US5 | Done | As a player, I want to select my role (Defense Attorney, Prosecutor, Judge, or Spectator), **so that** I can determine my level of interaction. |
| US6 | Done | As a player, I want evidence distributed only to my role, **so that** strategic competition and surprise are maintained. |

### Acceptance Criteria

**US4 — Case Prompt**
- Player can enter 1–2 sentences describing the trial scenario
- AI Clerk generates a complete structured case file (crime, charges, background story, evidence) from the prompt
- Case generation completes before the courtroom loads

**US5 — Role Selection**
- Player can choose one of four roles: Defense Attorney, Prosecutor, Judge, Spectator
- Role determines interaction level (attorney/prosecutor argue, judge delivers verdict, spectator observes)
- Role is locked for the duration of the match

**US6 — Role-Based Evidence Distribution**
- Defense attorneys see only defense + shared evidence
- Prosecutors see only prosecution + shared evidence
- Judges see all evidence
- Spectators see no evidence
- Evidence from the opposing side is never exposed via the API

---

## US3 — Courtroom UI & Evidence Inventory

| ID | Status | User Story |
|----|--------|------------|
| US7 | Done | As a player, I want a fixed case summary always visible, **so that** I don't lose track of essential details. |
| US8 | Done | As a playing attorney, I want a visual Evidence Folder showing cards I can consult, **so that** I can build my strategy. |
| US9 | Done | As a player, I want to select an evidence card and attach it to my argument, **so that** I can submit a fact-based argument. |
| US10 | Done | As a player, I want used evidence cards to be marked in my folder, **so that** I am challenged to produce new arguments each round. |

### Acceptance Criteria

**US7 — Case Summary Panel**
- Case summary (crime, charges, background) is always visible in the left panel
- Summary does not scroll away during the debate
- Current round and match status are shown

**US8 — Evidence Folder**
- Evidence Folder is shown in the right panel
- Each card displays its title and description
- Available and used cards are visually distinguished

**US9 — Evidence Attachment**
- Player can click a card to attach it to their argument
- At most one card can be attached per turn
- Submission is rejected if the attached card does not belong to the player's role

**US10 — Used Evidence Tracking**
- After a card is played it is marked as USED in the folder
- Used cards are greyed out and cannot be selected again
- AI opponents follow the same one-use rule

---

## US4 — AI Interaction & Objection Mechanic

| ID | Status | User Story |
|----|--------|------------|
| US11 | Done | As a player, I want a one-time **Objection** button available during my turn, **so that** I can challenge a flawed opponent argument and force the AI to address it directly in its next response. |

### Acceptance Criteria

**US11 — Objection**
- Objection button is visible only during the player's turn and only after the opponent has spoken
- Each side (prosecution / defense) has exactly one objection per match
- After use, the button is permanently disabled for that player
- The opponent AI must address the objection directly in its very next argument before making new points
- Objection and AI rebuttal are both persisted and visible in the transcript

---

## US5 — AI Judge, Scales of Justice & Verdict

| ID | Status | User Story |
|----|--------|------------|
| US12 | Done | As a player, I want a visual Scales of Justice bar that updates after each round, **so that** I can monitor match momentum in real time. |
| US13 | Done | As the Judge, I want to deliver a motivated final verdict after the debate concludes, **so that** I can officially close the session with a reasoned decision. |

### Acceptance Criteria

**US12 — Scales of Justice**
- Scales of Justice bar is shown at the top of the courtroom
- The bar updates after every round based on the AI Judge's scoring
- Green indicates defense advantage; red indicates prosecution advantage
- The bar animates on each update

**US13 — Final Verdict**
- After the last round, the AI Judge delivers a written Guilty / Not Guilty verdict with reasoning
- If the player is the Judge role, they write their own verdict and reasoning
- Verdict is saved to match history and counted in win rate
- Match status is set to `completed` after the verdict is recorded

---

