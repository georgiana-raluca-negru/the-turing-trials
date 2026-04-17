## The Turing Trials 
**Interactive Multi-Agent Courtroom Simulation**

## Project Overview
**The Turing Trials** is a gamified web application that simulates a courtroom environment using a multi-agent Large Language Model (LLM) architecture. Instead of a simple chatbot interface, this platform orchestrates a turn-based legal battle where human players and autonomous AI agents take on the roles of Defense Attorney, Prosecutor, and Judge. 

The core innovation lies in our **AI Clerk Agent**, which dynamically generates structured case files (JSON) based on a simple user prompt. To prevent AI hallucinations, the prosecuting and defending agents are strictly constrained by the system to argue using only the generated "Evidence Inventory". Players must strategically attach evidence cards to their arguments and can use an "Objection" mechanic to interrupt flawed AI logic in real-time. The match concludes with an objective verdict from the AI Judge, and the results are saved to the user's match history.

## Product Backlog: User Stories

### Authentication & User Account
* **US1:** As a visitor, I want to register for an account using my email and password (or via Google/GitHub), **so that** I can have a dedicated profile on the platform.
* **US2:** As an authenticated user, I want to securely log out of the platform, **so that** I can protect my personal data on shared devices.
* **US3:** As a user, I want to access a Dashboard where I can view my match history (role played, case summary, verdict, and date), **so that** I can track my progress and overall win rate.

### AI Clerk & Match Setup
* **US4:** As a player, I want to input a short text prompt (1-2 sentences) describing the core idea of the trial, **so that** I can provide a starting point for the case generation engine.
* **US5:** As a player, I want to select my desired role (Defense Attorney, Prosecutor, Judge, or Spectator) from the UI, **so that** I can determine my perspective and level of interaction in the trial.
* **US6:** As a player, I want to be distributed the generated evidence only to my appropriate role (e.g., the Defense only sees the defense evidence), **so that** I can maintain the element of surprise and strategic competition.

### Courtroom UI & Evidence Inventory
* **US7:** As a player, I want to permanently see a fixed summary of the case (Crime and Charges) on the screen, **so that** I don't lose track of essential details during the debates.
* **US8:** As a playing attorney/prosecutor, I want to have a visual "Evidence Folder" section displaying cards I can consult, **so that** I can build my trial strategy.
* **US9:** As a player, I want to visually select an evidence card from my folder and attach it to the text argument I am drafting, **so that** I can submit a valid, fact-based argument to the court.
* **US10**: As a player, I want used evidence cards to be marked or removed from the folder, so that I am challenged to come up with new arguments in every round of the trial.

### AI Interaction & Objection Mechanic
* **US11:** As a player, I want to have an "Objection" button active only during the opponent's turn, which I can press to pause their text generation and input a reason for contesting, **so that** I can penalize the AI's logical fallacies.

### AI Judge, Scales of Justice & Verdict
* **US12:** As a player, I want to see a visual progress bar called "Scales of Justice" that tilts towards me or the opponent after each round (evaluated in the background by the AI Judge), **so that** I can monitor the current score of the match in real-time.
* **US13:** As user playing as Judge, I want to stop the trial after a predefined number of rounds, analyze the chat history along with the Scales of Justice, and generate a motivated final verdict (Guilty/Not Guilty), saving the result to the database, **so that** I can officially close the game session.

