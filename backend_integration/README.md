# Backend Integration

`backend_integration/` is the backend-facing contract layer for the courtroom
demo. It leaves `ai_engine/` intact and wraps the current AI prototype behind a
shared runtime contract.

The purpose of this package is simple:

- backend code should call stable functions from here
- AI orchestration should stay behind adapters
- shared runtime objects should be defined once, not duplicated in routes, ORM
  models, and LangGraph state

This package is the intended replacement for calling the demo directly.

## Core Contract

The contract is built around four ideas:

1. `MatchConfig`
   - runtime configuration for a match
   - includes `user_prompt`, `max_rounds`, `allow_evidence_reuse`

2. `ActorConfiguration`
   - defines whether each actor is `human` or `ai`
   - currently supports:
     - prosecution
     - defense
     - judge

3. `MatchRuntimeState`
   - the canonical in-memory match state
   - this is the main state object passed through the interface

4. `MatchProgressResult`
   - result object returned by progression functions
   - tells the caller what happened and what the next step is

The backend should treat these models as the canonical runtime objects for
integration. Database rows, API payloads, and demo-internal models should adapt
to them.

## Round Model

`max_rounds` means debate cycles.

One cycle is:

1. prosecution turn
2. defense turn

After the final defense turn of the final cycle, the next actor becomes the
judge.

This means the runtime tracks both:

- `current_cycle`
- `next_actor`

That distinction matters because cycle number and speaker turn are not the same
thing.

## Package Layout

```text
backend_integration/
|-- interface.py
|-- models/
|-- ports/
|-- adapters/
`-- services/
```

### `interface.py`

Public entrypoint for backend code.

Routes, controllers, or service-layer backend code should call functions from
here instead of importing `ai_engine` directly.

### `models/`

Canonical shared objects.

- `actors.py`
  - `ActorRole`
  - `ActorController`
  - `ActorConfiguration`
- `case_file.py`
  - `CaseSummary`
  - `EvidenceCard`
  - `CaseFileBundle`
- `turns.py`
  - `HumanTurnInput`
  - `HumanJudgeVerdictInput`
  - `TurnRecord`
  - `VerdictRecord`
- `match.py`
  - `MatchConfig`
  - `MatchRuntimeState`
  - `MatchProgressResult`
  - `MatchStatus`
  - `ProgressAction`

### `ports/`

Dependency interfaces that the backend or AI layer can implement and inject.

Current port:

- `AIRunnerPort`
  - generate a case
  - generate an AI debate turn
  - generate a judge verdict

This keeps orchestration separate from the concrete LangChain/LangGraph
implementation.

### `adapters/`

Translation layer between the canonical contract and concrete implementations.

Current adapter:

- `AIEngineAdapter`
  - adapts the current `ai_engine` demo nodes to the shared interface

### `services/`

Lifecycle and state transition logic.

This is where turn progression, validation, evidence use, human/AI branching,
and quit handling live.

## Public API

Import from `backend_integration.interface`.

### `create_match(...)`

Creates a new `MatchRuntimeState`.

Inputs:

- `config: MatchConfig`
- `actors: ActorConfiguration`
- `case_file: CaseFileBundle | None`
- `ai_runner: AIRunnerPort | None`

Behavior:

- if `case_file` is provided, it is used directly
- otherwise the interface asks the AI runner to generate the case
- initial state starts at cycle `1` with `next_actor = prosecution`

### `progress_match(...)`

Advances the match by exactly one logical step.

Inputs:

- `state`
- optional `ai_runner`
- optional `human_turn`
- optional `human_verdict`

Behavior:

- if the next actor is AI, one AI turn is generated
- if the next actor is human and no input is provided, the result returns
  `AWAITING_HUMAN_TURN`
- if the next actor is the human judge and no verdict is provided, the result
  returns `AWAITING_HUMAN_VERDICT`
- if human input is supplied for the wrong actor or wrong phase, validation
  fails

Use this when the backend wants precise control over every step.

### `progress_until_human_or_terminal(...)`

Auto-advances AI-controlled actors until one of these happens:

- a human turn is needed
- a human judge verdict is needed
- the match completes
- the match is quit

Use this when the backend wants to let the AI run until the next user-facing
pause point.

### `submit_human_turn(...)`

Convenience wrapper around `progress_match(...)` for a non-judge human turn.

### `submit_human_verdict(...)`

Convenience wrapper around `progress_match(...)` for a human judge verdict.

### `quit_match(...)`

Marks the match as quit and returns a terminal state.

Quitting is first-class. It is not treated as an exceptional crash path.

### `get_match_snapshot(...)`

Returns a deep copy of the current runtime state.

### `get_available_evidence(...)`

Returns evidence available to a given role, taking the evidence reuse toggle
into account.

## Shared Model Semantics

### `ActorConfiguration`

This controls who is responsible for each role.

Example:

```python
ActorConfiguration(
    prosecution=ActorController.HUMAN,
    defense=ActorController.AI,
    judge=ActorController.AI,
)
```

The shared interface uses this configuration to decide whether it should:

- wait for backend-provided human input
- or call the AI runner

### `EvidenceCard`

`EvidenceCard` is the shared evidence object used by the integration layer.

Important fields:

- `code`
  - stable evidence identifier for runtime use
- `backend_id`
  - optional persistence-layer identifier
- `assigned_role`
  - prosecution, defense, or shared
- `is_used`
  - whether the evidence has already been consumed
- `used_in_turn_index`
  - which turn used it

This model deliberately allows the backend to keep its own database identity
while the AI layer still uses a stable runtime evidence code.

### `TurnRecord`

Represents one speaker action.

Important fields:

- `turn_index`
  - absolute turn number in the transcript
- `cycle_number`
  - debate cycle number
- `actor_role`
  - prosecution, defense, or judge
- `controller`
  - human or ai
- `attached_evidence_ids`
  - zero to two evidence codes
- `skipped`
  - whether the turn was effectively missed
- `system_note`
  - optional system-level event note

### `MatchRuntimeState`

This is the object the backend should persist or translate into its own storage
model.

Important fields:

- `config`
- `actors`
- `case_file`
- `status`
- `current_cycle`
- `next_actor`
- `transcript`
- `system_events`
- `verdict`
- `quit_reason`
- `quit_actor`

## How the Backend Should Use This

The backend should control the match lifecycle by calling the shared interface,
not by calling demo nodes directly.

Recommended control flow:

1. create match
2. store or snapshot the returned state
3. call `progress_until_human_or_terminal(...)`
4. if the result waits for human input, collect it from the frontend
5. call `submit_human_turn(...)` or `submit_human_verdict(...)`
6. call `progress_until_human_or_terminal(...)` again
7. allow `quit_match(...)` at any time before terminal completion

Example shape:

```python
state = create_match(config=config, actors=actors)

result = progress_until_human_or_terminal(state=state)
state = result.state

if result.action == ProgressAction.AWAITING_HUMAN_TURN:
    result = submit_human_turn(
        state=state,
        human_turn=HumanTurnInput(
            actor_role=result.waiting_for_actor,
            text="My argument",
            attached_evidence_ids=["EVD-001"],
        ),
    )
    state = result.state
```

The backend is free to persist every intermediate state, every turn, or both.

## Adapters: Who Adapts What

The shared contract is the middle layer.

```text
backend ORM / API models <-> backend_integration models <-> ai_engine models
```

Current ownership:

- this package defines the canonical runtime objects
- `AIEngineAdapter` adapts the current demo to those objects
- future backend work should adapt backend tables and API payloads to those same
  objects

Recommended adaptation style:

- prefer composition over inheritance

Reason:

- ORM entities and runtime debate objects do not represent the same concern
- composition allows DB IDs, audit fields, and transport fields to coexist
  cleanly with AI-runtime fields

Example:

- backend table keeps a UUID primary key
- shared `EvidenceCard` keeps `backend_id` plus runtime `code`

## LangChain / LangGraph and Streaming

Yes, LangChain and LangGraph can still work if streaming is partly directed by
the backend engineer. The important point is to separate two layers:

1. orchestration contract
2. streaming transport

The current shared interface is a turn-level orchestration contract. It does
not currently expose token-by-token streaming. It expects the AI runner to
return a completed turn or completed verdict.

That means:

- the backend can still control when progression happens
- the backend can decide whether to advance one step or auto-run until the next
  pause point
- LangGraph can still run internally inside the adapter or AI runner

### How streaming fits today

Today, the shared interface works like this:

1. backend calls `progress_match(...)` or
   `progress_until_human_or_terminal(...)`
2. the lifecycle layer checks which actor should act next
3. if the actor is AI, the lifecycle layer calls `AIRunnerPort`
4. the concrete AI runner may use LangChain/LangGraph however it wants
5. the AI runner returns a completed shared result object
6. the lifecycle layer updates `MatchRuntimeState`

So streaming can already exist internally inside the AI runner, but the current
shared contract only receives the final structured result for that turn.

### If the backend wants visible streaming

If the backend engineer wants to stream AI output to the frontend while the turn
is being generated, there are two clean options:

1. keep the current contract and stream underneath it
   - the AI runner streams tokens/events to a websocket, SSE channel, logger,
     or callback sink
   - when generation finishes, it still returns the final `TurnRecord`

2. extend the contract with an event sink or streamed progression API
   - add a callback/event port such as `on_token`, `on_partial_turn`,
     `on_system_event`
   - or add a generator-based interface that yields progress events and ends
     with the final `MatchProgressResult`

The first option is the least invasive and fits the current implementation
without changing the shared model surface.

### Recommended streaming design for next phase

If streaming becomes a real product requirement, add a second contract layer for
events instead of overloading `MatchRuntimeState`.

Recommended split:

- state contract
  - `MatchRuntimeState`
  - `MatchProgressResult`
- event contract
  - token streamed
  - partial text updated
  - tool call started/finished
  - turn finalized
  - validation failed

That keeps persistence and deterministic match state separate from transient
streaming traffic.

## Current Limitations

These are deliberate for the current phase:

1. the shared interface is synchronous at turn granularity
2. persistence is not implemented in this package yet
3. backend database adapters are not implemented yet
4. streaming events are not exposed as a first-class port yet
5. the current AI adapter still depends on the current demo node structure

## Rules Enforced by the Lifecycle Layer

The current lifecycle service enforces:

- `max_rounds >= 1`
- exactly one next actor at a time
- evidence selection limited to at most 2 items per turn
- evidence availability filtered by role
- evidence reuse controlled by config
- human judge input must use verdict submission, not normal turn submission
- invalid wrong-step submissions fail fast
- quit is a terminal state

## What Should Be Added Next

The next integration steps should be:

1. backend persistence adapter
   - translate `MatchRuntimeState` to backend models
2. route/controller wiring
   - backend routes should call only the shared facade
3. explicit event/streaming port
   - only if real-time token streaming is needed
4. backend snapshot/view models
   - if frontend/client payloads should differ from internal runtime state
5. stronger typed verdict object from the judge node
   - to reduce verdict parsing dependence

## Development Guidance

When extending this package:

- keep `backend_integration.models` canonical
- keep game logic in `services/`
- keep translation code in `adapters/`
- keep backend-specific and AI-specific concerns out of the shared models where
  possible
- avoid calling `ai_engine` directly from backend routes
- prefer adding ports and adapters instead of hard-binding more code into the
  lifecycle layer

That separation is what will let the backend and AI sides evolve without
breaking each other.
