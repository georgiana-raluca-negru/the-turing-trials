## The Turing Trials 
**Interactive Multi-Agent Courtroom Simulation**

## 📖 Project Overview
**The Turing Trials** is a gamified web application that simulates a courtroom environment using a multi-agent Large Language Model (LLM) architecture. Instead of a simple chatbot interface, this platform orchestrates a turn-based legal battle where human players and autonomous AI agents take on the roles of Defense Attorney, Prosecutor, and Judge. 

The core innovation lies in our **AI Clerk Agent**, which dynamically generates structured case files (JSON) based on a simple user prompt. To prevent AI hallucinations, the prosecuting and defending agents are strictly constrained by the system to argue using only the generated "Evidence Inventory". Players must strategically attach evidence cards to their arguments and can use an "Objection" mechanic to interrupt flawed AI logic in real-time. The match concludes with an objective verdict from the AI Judge, and the results are saved to the user's match history.

---

## Product Backlog: User Stories

### Authentication & User Account
* **US1:** As a visitor, I want to register for an account using my email and password (or via Google/GitHub), **so that** I can have a dedicated profile on the platform.
* **US2:** As an authenticated user, I want to securely log out of the platform, **so that** I can protect my personal data on shared devices.
* **US3:** As a user, I want to access a Dashboard where I can view my match history (role played, case summary, verdict, and date), **so that** I can track my progress and overall win rate.

### AI Clerk & Match Setup
* **US4:** As a player, I want to input a short text prompt (1-2 sentences) describing the core idea of the trial, **so that** I can provide a starting point for the case generation engine.
* **US5:** As a player, I want to select my desired role (Defense Attorney, Prosecutor, Judge, or Spectator) from the UI, **so that** I can determine my perspective and level of interaction in the trial.
* **US6:** As the Orchestrator system, I want to send the player's prompt to the AI Clerk Agent and receive a valid JSON object (containing the crime, charges, prosecution evidence, and defense evidence), **so that** I can structure the entire match on a consistent, logical basis.
* **US7:** As the backend system, I want to distribute the generated evidence only to the appropriate roles (e.g., the Defense only sees the defense evidence), **so that** I can maintain the element of surprise and strategic competition.

### Courtroom UI & Evidence Inventory
* **US8:** As a player, I want to permanently see a fixed summary of the case (Crime and Charges) on the screen, **so that** I don't lose track of essential details during the debates.
* **US9:** As a playing attorney/prosecutor, I want to have a visual "Evidence Folder" section displaying cards I can consult, **so that** I can build my trial strategy.
* **US10:** As a player, I want to visually select an evidence card from my folder and attach it to the text argument I am drafting, **so that** I can submit a valid, fact-based argument to the court.
* **US11:** As the system, I want to mark an evidence card as "Used" and remove it from the folder after submission, **so that** I can prevent players from abusively reusing the same proof in subsequent rounds.

### AI Interaction & Objection Mechanic
* **US12:** As the Orchestrator system, I want to pass the player's argument and attached evidence to the AI opponent (e.g., AI Prosecutor), forcing it via system prompt to respond strictly based on the case file, **so that** I can prevent AI hallucinations.
* **US13:** As a player, I want to have an "Objection" button active only during the opponent's turn, which I can press to pause their text generation and input a reason for contesting, **so that** I can penalize the AI's logical fallacies.
* **US14:** As the system, I want to limit the number of objections to a maximum of 3 per match for each side, **so that** I can prevent the trial flow from being permanently blocked or spammed.

### AI Judge, Scales of Justice & Verdict
* **US15:** As a player, I want to see a visual progress bar called "Scales of Justice" that tilts towards me or the opponent after each round (evaluated in the background by the AI Judge), **so that** I can monitor the current score of the match in real-time.
* **US16:** As the AI Judge Agent, I want to stop the trial after a predefined number of rounds, analyze the chat history along with the Scales of Justice, and generate a motivated final verdict (Guilty/Not Guilty), saving the result to the database, **so that** I can officially close the game session.

### 🤖 Epic 6: AI Evals & Testing (DevOps)
* **US17:** As a developer, I want to write automated test scripts that simulate false/invented arguments being submitted, **so that** I can verify if the AI Judge correctly rejects fabricated evidence (Agent Evals).
