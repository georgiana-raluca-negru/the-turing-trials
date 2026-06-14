"use client";

import { useEffect, useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import ScalesOfJustice from "@/components/courtroom/ScalesOfJustice";
import CaseSummary from "@/components/courtroom/CaseSummary";
import EvidenceVault, { EvidenceItem } from "@/components/courtroom/EvidenceVault";
import Spinner from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import { apiJson, apiFetch } from "@/lib/api";

/* ── Backend types ────────────────────────────────────────────────────────── */
interface MatchOut {
  id: string;
  player_prompt: string;
  case_summary: string | null;
  player_role: string;
  status: string;
  total_rounds: number;
  verdict: string | null;
  verdict_reasoning: string | null;
}

interface TranscriptEntry {
  turn_index: number;
  cycle: number;
  actor: string;       // "prosecution" | "defense" | "judge"
  controller: string;  // "human" | "ai"
  text: string;
  evidence_ids: string[];
  evidence_used?: { title: string; desc: string }[];
  skipped: boolean;
  system_note: string | null;
}

interface VerdictData {
  guilty: boolean | null;
  reasoning: string;
  prosecution_score: number | null;
  defense_score: number | null;
  verdict_text: string | null;
}

interface GameState {
  match_id: string;
  status: string;
  player_role: string;
  current_round: number;
  max_rounds: number;
  current_turn: string | null;
  scales_value: number;
  case_summary: { crime: string; charges: string[]; background_story: string } | null;
  transcript: TranscriptEntry[];
  verdict: VerdictData | null;
  waiting_for: string | null;
  objection_available: boolean;
}

interface EvidenceCard {
  id: string;
  title: string;
  description: string;
  assigned_role: string;
  is_used: boolean;
  used_in_round: number | null;
  card_order: number;
}

interface ChatMessage {
  id: string;
  role: "prosecutor" | "defense" | "judge" | "user";
  content: string;
  round: number;
  evidenceItems?: { id: string; title: string; desc: string }[];
}

/* ── Constants & helpers ──────────────────────────────────────────────────── */
const ACTOR_TO_MSG_ROLE: Record<string, ChatMessage["role"]> = {
  prosecution: "prosecutor",
  defense: "defense",
  judge: "judge",
};

const PLAYER_ACTOR: Record<string, string> = {
  defense_attorney: "defense",
  prosecutor: "prosecution",
  judge: "judge",
};

// backend scales_value: -1.0 (prosecution advantage) → +1.0 (defense advantage)
// ScalesOfJustice: 0 (defense wins) → 50 (tie) → 100 (prosecution wins)
const toDisplayScore = (v: number) => Math.round((-v + 1) * 50);

function transcriptToMessages(
  entries: TranscriptEntry[],
  playerRole: string,
  knownEvidence: EvidenceItem[] = [],
): ChatMessage[] {
  const playerActor = PLAYER_ACTOR[playerRole];
  return entries
    .filter((t) => !t.skipped && t.text.trim().length > 0)
    .map((t) => ({
      id: `t-${t.turn_index}`,
      role:
        t.controller === "human" && t.actor === playerActor
          ? "user"
          : (ACTOR_TO_MSG_ROLE[t.actor] ?? "judge"),
      content: t.text,
      round: t.cycle,
      evidenceItems:
        (t.evidence_used && t.evidence_used.length > 0)
          ? t.evidence_used.map((ev) => ({ id: ev.title, title: ev.title, desc: ev.desc }))
          : t.evidence_ids.length > 0
          ? t.evidence_ids.flatMap((title) => {
              const item = knownEvidence.find((e) => e.title === title);
              return item ? [{ id: String(item.id), title: item.title, desc: item.desc }] : [];
            })
          : undefined,
    }));
}

function evidenceToItems(cards: EvidenceCard[]): EvidenceItem[] {
  return cards.map((c) => ({
    id: c.id,
    title: c.title,
    desc: c.description,
    used: c.is_used,
  }));
}

/* ── Component ────────────────────────────────────────────────────────────── */
export default function CourtroomPage({
  params,
}: {
  params: Promise<{ matchID: string }>;
}) {
  const { matchID } = use(params);
  const router = useRouter();
  const { showToast } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [match, setMatch] = useState<MatchOut | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [attachedEvidence, setAttachedEvidence] = useState<string | null>(null);
  const [displayScore, setDisplayScore] = useState(50);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [argumentBuffer, setArgumentBuffer] = useState("");
  const [verdictChoice, setVerdictChoice] = useState<"guilty" | "not_guilty" | null>(null);
  const [mobilePanelTab, setMobilePanelTab] = useState<"chat" | "case" | "evidence">("chat");
  const [caseSidebarOpen, setCaseSidebarOpen] = useState(false);
  const [verdictOverlayDismissed, setVerdictOverlayDismissed] = useState(false);
  const [abandonConfirm, setAbandonConfirm] = useState(false);
  const [isSpectating, setIsSpectating] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const spectatingActive = useRef(false);

  /* ── Apply updated game state from API response ───────────────────────── */
  function applyGameState(state: GameState, playerRole: string, currentEvidence: EvidenceItem[]) {
    setGameState(state);
    setDisplayScore(toDisplayScore(state.scales_value ?? 0));
    setMessages(transcriptToMessages(state.transcript, playerRole, currentEvidence));
    setEvidence((prev) =>
      prev.map((e) => {
        const usedInTranscript = state.transcript.some((t) =>
          t.evidence_ids.includes(e.title),
        );
        return usedInTranscript ? { ...e, used: true } : e;
      }),
    );
  }

  /* ── Spectator/judge turn-by-turn polling ─────────────────────────────── */
  async function startSpectatorLoop(playerRole: string, initialEvidence: EvidenceItem[]) {
    spectatingActive.current = true;
    setIsSpectating(true);
    while (spectatingActive.current) {
      try {
        const state = await apiJson<GameState>(`/api/sessions/${matchID}/advance`, { method: "POST" });
        if (!spectatingActive.current) break;
        applyGameState(state, playerRole, initialEvidence);
        if (state.status === "completed" || state.status === "awaiting_human_verdict" || state.status === "quit") break;
        await new Promise((r) => setTimeout(r, 400));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Stream error";
        showToast(`Stream interrupted: ${msg}`, "error");
        break;
      }
    }
    spectatingActive.current = false;
    setIsSpectating(false);
  }

  /* ── Load match + start/resume session ────────────────────────────────── */
  useEffect(() => {
    const load = async () => {
      if (!localStorage.getItem("turing_access_token")) {
        router.push("/login");
        return;
      }

      try {
        // 1. Get match metadata
        const matchData = await apiJson<MatchOut>(`/api/matches/${matchID}`);
        setMatch(matchData);

        let state: GameState;

        if (matchData.status === "lobby") {
          // 2a. Start session — triggers AI Clerk case generation
          const res = await apiFetch("/api/sessions/", {
            method: "POST",
            body: JSON.stringify({ match_id: matchID }),
          });

          if (res.ok) {
            state = await res.json();
          } else if (res.status === 409) {
            // Session already exists (page reload after start)
            state = await apiJson<GameState>(`/api/sessions/${matchID}`);
          } else {
            const err = await res.json().catch(() => ({}));
            const detail = Array.isArray(err.detail)
              ? err.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join(", ")
              : err.detail ?? `Server error ${res.status}`;
            throw new Error(detail);
          }
        } else {
          // 2b. Resume existing session
          state = await apiJson<GameState>(`/api/sessions/${matchID}`);
        }

        setGameState(state);
        setDisplayScore(toDisplayScore(state.scales_value ?? 0));

        // 3. Fetch role-specific evidence then build messages with full evidence details
        const cards = await apiJson<EvidenceCard[]>(`/api/evidence/${matchID}`);
        const items = evidenceToItems(cards);
        setEvidence(items);
        setMessages(transcriptToMessages(state.transcript, matchData.player_role, items));

        // 4. For judge/spectator, drive turns one-at-a-time so the debate appears live
        const isWatcher = matchData.player_role === "judge" || matchData.player_role === "spectator";
        if (isWatcher && state.status === "in_progress") {
          startSpectatorLoop(matchData.player_role, items);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load courtroom.";
        setError(msg);
        showToast(msg, "error");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchID]);

  useEffect(() => {
    return () => { spectatingActive.current = false; };
  }, []);

  /* ── Auto-scroll ──────────────────────────────────────────────────────── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ── Attach evidence ──────────────────────────────────────────────────── */
  function handleAttach(id: string | number) {
    const strId = String(id);
    if (attachedEvidence === strId) {
      setAttachedEvidence(null);
      return;
    }
    setAttachedEvidence(strId);
    const item = evidence.find((e) => String(e.id) === strId);
    if (item) showToast(`Attached: ${item.title}`, "info");
  }

  /* ── Submit argument ──────────────────────────────────────────────────── */
  async function handleSubmitArgument() {
    if (!argumentBuffer.trim() || isSubmitting || !match) return;

    const optimisticText = argumentBuffer.trim();
    const evidenceToAttach = attachedEvidence;
    const optimisticId = `opt-${Date.now()}`;

    // Embed the full evidence item so the description is immediately visible
    const evidenceItem = evidenceToAttach
      ? evidence.find((e) => String(e.id) === evidenceToAttach)
      : null;

    setMessages((prev) => [
      ...prev,
      {
        id: optimisticId,
        role: "user",
        content: optimisticText,
        round: gameState?.current_round ?? 0,
        evidenceItems: evidenceItem
          ? [{ id: evidenceToAttach!, title: evidenceItem.title, desc: evidenceItem.desc }]
          : undefined,
      },
    ]);
    setArgumentBuffer("");
    setAttachedEvidence(null);
    setIsSubmitting(true);

    try {
      const state = await apiJson<GameState>(`/api/sessions/${matchID}/turn`, {
        method: "POST",
        body: JSON.stringify({
          argument_text: optimisticText,
          attached_evidence_id: evidenceToAttach ?? null,
        }),
      });

      // Load updated evidence first, then rebuild all messages with correct details
      const updatedCards = await apiJson<EvidenceCard[]>(`/api/evidence/${matchID}`);
      const updatedItems = evidenceToItems(updatedCards);
      setEvidence(updatedItems);
      applyGameState(state, match.player_role, updatedItems);

      if (state.verdict) {
        const label =
          state.verdict.guilty === true
            ? "Guilty"
            : state.verdict.guilty === false
            ? "Not Guilty"
            : "Pending";
        showToast(`Trial concluded. Verdict: ${label}`, "info");
      }
    } catch (err: unknown) {
      // Roll back the optimistic message and restore the input
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      setArgumentBuffer(optimisticText);
      setAttachedEvidence(evidenceToAttach);
      const msg = err instanceof Error ? err.message : "Failed to submit argument.";
      showToast(`Transmission error: ${msg}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  /* ── Submit judge verdict ─────────────────────────────────────────────── */
  async function handleSubmitVerdict() {
    if (!verdictChoice || !argumentBuffer.trim() || isSubmitting || !match) return;
    setIsSubmitting(true);

    try {
      const state = await apiJson<GameState>(`/api/sessions/${matchID}/verdict`, {
        method: "POST",
        body: JSON.stringify({
          verdict: verdictChoice,
          verdict_reasoning: argumentBuffer.trim(),
        }),
      });

      setArgumentBuffer("");
      setVerdictChoice(null);
      applyGameState(state, match.player_role, evidence);

      const label = verdictChoice === "guilty" ? "Guilty" : "Not Guilty";
      showToast(`Verdict delivered: ${label}`, "info");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit verdict.";
      showToast(`Verdict error: ${msg}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  /* ── Raise objection ─────────────────────────────────────────────────── */
  async function handleObjection() {
    if (!match || !gameState?.objection_available || isSubmitting) return;
    try {
      const state = await apiJson<GameState>(`/api/sessions/${matchID}/objection`, { method: "POST" });
      applyGameState(state, match.player_role, evidence);
      showToast("OBJECTION! The court has been notified. Your opponent must address this challenge.", "warning");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to raise objection.";
      showToast(msg, "error");
    }
  }

  /* ── Abandon match ────────────────────────────────────────────────────── */
  async function handleAbandonMatch() {
    if (!match) return;
    try {
      const res = await apiFetch(`/api/sessions/${match.id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = Array.isArray(err.detail)
          ? err.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join(", ")
          : err.detail ?? `Error ${res.status}`;
        throw new Error(detail);
      }
      showToast("Trial abandoned.", "info");
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to abandon match.";
      showToast(msg, "error");
      setAbandonConfirm(false);
    }
  }

  /* ── Loading ──────────────────────────────────────────────────────────── */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center flex-grow min-h-[calc(100vh-57px)] bg-[rgb(var(--bg-page))]">
        <Spinner label="Initializing Courtroom..." size="lg" />
      </div>
    );
  }

  if (error || !match || !gameState) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow min-h-[calc(100vh-57px)] bg-[rgb(var(--bg-page))] gap-4">
        <p className="font-mono text-red-600 text-sm border border-red-300 bg-red-50 px-6 py-4 rounded-xl uppercase tracking-wider">
          ERR: {error || "Match not found"}
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="text-xs font-mono text-[rgb(var(--text-muted))] hover:text-[rgb(var(--heading))] uppercase tracking-widest transition-colors cursor-pointer"
        >
          Return to Archives
        </button>
      </div>
    );
  }

  /* ── Derived state ────────────────────────────────────────────────────── */
  const playerActor = PLAYER_ACTOR[match.player_role] ?? null;
  const isMyTurn = gameState.waiting_for === playerActor;
  const isCompleted = gameState.status === "completed" || gameState.status === "quit";

  const roleLabel: Record<string, string> = {
    defense_attorney: "Defense Counsel",
    prosecutor: "Prosecutor",
    judge: "Judge",
    spectator: "Spectator",
  };


  const caseSummaryText = gameState.case_summary
    ? `${gameState.case_summary.crime}: ${gameState.case_summary.charges.join(", ")}`
    : match.case_summary;

  const verdictLabel =
    gameState.verdict?.guilty === true
      ? "Guilty"
      : gameState.verdict?.guilty === false
      ? "Not Guilty"
      : match.verdict === "guilty"
      ? "Guilty"
      : match.verdict === "not_guilty"
      ? "Not Guilty"
      : "Pending";

  /* ── Message bubble ───────────────────────────────────────────────────── */
  function MessageBubble({
    msg,
    playerRole,
    maxRounds,
  }: {
    msg: ChatMessage;
    playerRole: string;
    maxRounds: number;
  }) {
    const isUser = msg.role === "user";
    const isJudge = msg.role === "judge";
    const isProsecution =
      msg.role === "prosecutor" || (isUser && playerRole === "prosecutor");
    const isDefense =
      msg.role === "defense" || (isUser && playerRole === "defense_attorney");

    // CSS variable group driving this bubble's color theme — written out as
    // literal class strings so Tailwind's scanner can pick them up.
    const THEME = {
      judge: {
        bubble: "bg-[rgb(var(--bubble-judge-bg))] border border-[rgb(var(--bubble-judge-border))]",
        text: "text-[rgb(var(--bubble-judge-text))]",
        exhibit: "bg-[rgb(var(--bubble-judge-bg))]/10 border border-[rgb(var(--bubble-judge-border))]/40",
      },
      prosecution: {
        bubble: "bg-[rgb(var(--bubble-prosecution-bg))] border border-[rgb(var(--bubble-prosecution-border))]",
        text: "text-[rgb(var(--bubble-prosecution-text))]",
        exhibit: "bg-[rgb(var(--bubble-prosecution-bg))]/10 border border-[rgb(var(--bubble-prosecution-border))]/40",
      },
      defense: {
        bubble: "bg-[rgb(var(--bubble-defense-bg))] border border-[rgb(var(--bubble-defense-border))]",
        text: "text-[rgb(var(--bubble-defense-text))]",
        exhibit: "bg-[rgb(var(--bubble-defense-bg))]/10 border border-[rgb(var(--bubble-defense-border))]/40",
      },
    } as const;

    const v = isJudge ? "judge" : isProsecution ? "prosecution" : "defense";
    const theme = THEME[v];

    const bubbleClass = isJudge
      ? `${theme.bubble} max-w-full shadow-sm`
      : `${theme.bubble} shadow-sm ${isUser ? "max-w-[92%] ml-auto" : "max-w-[92%]"}`;

    const textColor = theme.text;
    const labelColor = `${textColor} opacity-80`;
    const exhibitCardClass = theme.exhibit;

    const label = isJudge
      ? "Judge AI"
      : isUser
      ? `${roleLabel[playerRole] ?? "Counsel"} (You)`
      : isProsecution
      ? "Prosecutor AI"
      : isDefense
      ? "Defense AI"
      : "Counsel";

    return (
      <div className={`p-3 sm:p-4 rounded-xl font-mono text-xs ${bubbleClass}`}>
        <div className="flex justify-between items-center mb-1.5 border-b border-current/10 pb-1">
          <span className={`font-bold uppercase tracking-widest text-[10px] sm:text-xs ${labelColor}`}>
            {label}
          </span>
          {msg.round > 0 && (
            <span className={`text-[10px] shrink-0 ml-2 ${textColor} opacity-60`}>
              Cycle {msg.round}/{maxRounds}
            </span>
          )}
        </div>
        <p className={`font-sans leading-relaxed text-xs sm:text-sm ${textColor}`}>
          {msg.content}
        </p>
        {msg.evidenceItems && msg.evidenceItems.length > 0 && (
          <div className="mt-2 pt-2 border-t border-current/10 space-y-1.5">
            {msg.evidenceItems.map((ev) => (
              <div key={ev.id} className={`${exhibitCardClass} rounded-lg p-2`}>
                <p className={`text-[9px] font-bold uppercase tracking-wider mb-0.5 ${textColor} opacity-90`}>
                  Exhibit: {ev.title}
                </p>
                <p className={`text-[9px] leading-relaxed ${textColor} opacity-70`}>{ev.desc}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col h-[calc(100vh-56px)] sm:h-[calc(100vh-65px)] bg-[rgb(var(--bg-page))] overflow-hidden relative">

      {/* ── End-of-game overlay ── */}
      {isCompleted && gameState.verdict && !verdictOverlayDismissed && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[rgb(var(--bg-surface))] border rounded-2xl shadow-2xl font-mono overflow-hidden border-[rgb(var(--border-sub))]">

            {/* Header bar */}
            <div className={`px-6 py-4 border-b flex items-start justify-between gap-4 ${
              gameState.verdict.guilty === true
                ? "border-red-200 bg-red-50"
                : gameState.verdict.guilty === false
                ? "border-emerald-200 bg-emerald-50"
                : "border-amber-200 bg-amber-50"
            }`}>
              <div>
                <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest mb-1">Trial Concluded</p>
                <h2 className={`text-2xl font-black uppercase tracking-widest ${
                  gameState.verdict.guilty === true
                    ? "text-red-700"
                    : gameState.verdict.guilty === false
                    ? "text-emerald-700"
                    : "text-amber-700"
                }`}>
                  Verdict: {gameState.verdict.guilty === true ? "Guilty" : gameState.verdict.guilty === false ? "Not Guilty" : "Pending"}
                </h2>
              </div>
              <button
                onClick={() => setVerdictOverlayDismissed(true)}
                className="text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-fg))] text-lg leading-none mt-1 cursor-pointer transition-colors shrink-0"
                title="Dismiss and review chat"
              >
                ✕
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5 space-y-4">
              {/* Case summary */}
              {caseSummaryText && (
                <div>
                  <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest mb-1">Case</p>
                  <p className="text-xs text-[rgb(var(--text-fg))]">{caseSummaryText}</p>
                </div>
              )}

              {/* Role + rounds */}
              <div className="flex gap-6 text-xs">
                <div>
                  <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest mb-0.5">Your Role</p>
                  <p className="text-[rgb(var(--text-fg))] font-bold uppercase">{roleLabel[match.player_role] ?? match.player_role}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest mb-0.5">Rounds Played</p>
                  <p className="text-[rgb(var(--text-fg))] font-bold">{gameState.current_round} / {gameState.max_rounds}</p>
                </div>
              </div>

              {/* Reasoning */}
              {gameState.verdict.reasoning && (
                <div>
                  <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest mb-1">Judge&apos;s Reasoning</p>
                  <p className="text-xs text-[rgb(var(--text-muted))] leading-relaxed max-h-32 overflow-y-auto pr-1">
                    {gameState.verdict.reasoning}
                  </p>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="px-6 py-4 border-t border-[rgb(var(--border-sub))] flex gap-3">
              <button
                onClick={() => setVerdictOverlayDismissed(true)}
                className="flex-1 py-2.5 text-xs font-bold uppercase tracking-widest rounded-lg border border-[rgb(var(--border-sub))] text-[rgb(var(--text-muted))] bg-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--border-sub))] transition-all cursor-pointer"
              >
                Review Chat
              </button>
              <button
                onClick={() => router.push("/dashboard")}
                className="flex-1 py-2.5 text-xs font-bold uppercase tracking-widest rounded-lg border border-[rgb(var(--border-sub))] text-[rgb(var(--text-muted))] bg-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--border-sub))] transition-all cursor-pointer"
              >
                Archives
              </button>
              <button
                onClick={() => router.push("/setup")}
                className="flex-1 py-2.5 text-xs font-bold uppercase tracking-widest rounded-lg bg-[#25D366] text-white hover:bg-[#128C7E] transition-all cursor-pointer"
              >
                New Trial
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Scales of Justice bar */}
      <div className="w-full px-4 py-2 border-b border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-elevated))] shrink-0 z-10">
        <ScalesOfJustice score={displayScore} />
      </div>

      {/* Mobile tab switcher */}
      <div className="md:hidden flex border-b border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-surface))] shrink-0">
        {(["chat", "case", "evidence"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setMobilePanelTab(tab)}
            className={`flex-1 py-2 text-[10px] font-mono font-bold uppercase tracking-widest transition-colors cursor-pointer ${
              mobilePanelTab === tab
                ? "text-[rgb(var(--heading))] border-b-2 border-[#25D366]"
                : "text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-fg))]"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 3-column layout */}
      <div className="flex flex-grow overflow-hidden relative z-10">

        {/* Left: Case Parameters — collapsible slide-out sidebar (desktop), tab panel (mobile) */}
        <button
          onClick={() => setCaseSidebarOpen((v) => !v)}
          className={`hidden md:flex absolute top-1/2 -translate-y-1/2 z-40 flex-col items-center gap-1.5 py-4 px-1.5 rounded-r-lg border border-l-0 border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-elevated))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--heading))] hover:border-[#128C7E]/50 transition-all duration-300 cursor-pointer ${
            caseSidebarOpen ? "left-80" : "left-0"
          }`}
          title={caseSidebarOpen ? "Collapse case parameters" : "Expand case parameters"}
        >
          <span className="text-xs">{caseSidebarOpen ? "‹" : "›"}</span>
          <span className="text-[9px] font-mono uppercase tracking-[0.2em] [writing-mode:vertical-rl]">Case</span>
        </button>

        <aside
          className={`p-4 border-r border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-elevated))] overflow-y-auto flex-col md:absolute md:inset-y-0 md:left-0 md:z-30 md:w-80 md:shadow-2xl transition-transform duration-300 ease-in-out ${
            mobilePanelTab === "case" ? "flex w-full" : "hidden"
          } ${caseSidebarOpen ? "md:flex md:translate-x-0" : "md:flex md:-translate-x-full"}`}
        >
          <CaseSummary
            matchId={match.id}
            caseSummary={caseSummaryText}
            playerRole={match.player_role}
            totalRounds={gameState.max_rounds}
            status={gameState.status}
            verdict={verdictLabel}
          />

          {!isCompleted && (
            <div className="mt-4 pt-4 border-t border-[rgb(var(--border-sub))] font-mono">
              {!abandonConfirm ? (
                <button
                  onClick={() => setAbandonConfirm(true)}
                  className="w-full text-[10px] text-[rgb(var(--text-muted))] hover:text-red-600 uppercase tracking-widest transition-colors cursor-pointer py-2 rounded-lg hover:bg-red-50 hover:border hover:border-red-200"
                >
                  Abandon Trial
                </button>
              ) : (
                <div className="text-center space-y-2">
                  <p className="text-[10px] text-red-600 uppercase tracking-widest">Confirm abandon?</p>
                  <p className="text-[9px] text-[rgb(var(--text-muted))]">This cannot be undone. Match will be saved as abandoned.</p>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => setAbandonConfirm(false)}
                      className="flex-1 text-[10px] uppercase py-1.5 border border-[rgb(var(--border-sub))] rounded-lg text-[rgb(var(--text-muted))] hover:bg-[rgb(var(--bg-elevated))] cursor-pointer transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleAbandonMatch}
                      className="flex-1 text-[10px] uppercase py-1.5 border border-red-300 rounded-lg text-red-600 bg-red-50 hover:bg-red-100 cursor-pointer transition-colors"
                    >
                      Abandon
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </aside>

        {/* Centre: Chat + input */}
        <section
          className={`w-full md:flex-1 flex flex-col bg-[rgb(var(--bg-page))] relative border-r border-l border-[rgb(var(--border-sub))] ${
            mobilePanelTab === "chat" ? "flex" : "hidden md:flex"
          }`}
        >
          {/* Chat log */}
          <div className="flex-grow p-3 sm:p-4 overflow-y-auto space-y-3">
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full">
                <p className="font-mono text-[rgb(var(--text-muted))] text-xs uppercase tracking-widest text-center">
                  {match.player_role === "spectator" || match.player_role === "judge"
                    ? "Trial initializing… the court is in session."
                    : "Trial initializing… submit your opening argument."}
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                playerRole={match.player_role}
                maxRounds={gameState.max_rounds}
              />
            ))}

            {/* AI computing indicator */}
            {(isSubmitting || isSpectating) && (
              <div className="p-3 bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-lg max-w-[60%] font-mono text-xs shadow-sm">
                <span className="text-[rgb(var(--text-muted))] text-[10px] uppercase tracking-widest">
                  {isSpectating
                    ? (gameState.current_turn === "prosecution" ? "Prosecutor AI" : gameState.current_turn === "defense" ? "Defense AI" : "Judge AI") + " is deliberating"
                    : (match.player_role === "defense_attorney" ? "Prosecutor AI" : match.player_role === "prosecutor" ? "Defense AI" : "AI Agent") + " is deliberating"
                  }
                </span>
                <div className="flex gap-1 mt-2">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="w-1.5 h-1.5 bg-[#25D366] rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Verdict block */}
            {isCompleted && gameState.verdict && (
              <div
                className={`p-4 rounded-lg border font-mono text-xs mt-4 ${
                  gameState.verdict.guilty === true
                    ? "bg-red-50 border-red-300"
                    : gameState.verdict.guilty === false
                    ? "bg-emerald-50 border-emerald-300"
                    : "bg-amber-50 border-amber-300"
                }`}
              >
                <div
                  className={`text-sm font-bold uppercase tracking-widest mb-2 ${
                    gameState.verdict.guilty === true
                      ? "text-red-700"
                      : gameState.verdict.guilty === false
                      ? "text-emerald-700"
                      : "text-amber-700"
                  }`}
                >
                  Verdict:{" "}
                  {gameState.verdict.guilty === true
                    ? "Guilty"
                    : gameState.verdict.guilty === false
                    ? "Not Guilty"
                    : "Pending"}
                </div>
                <p className="leading-relaxed text-[rgb(var(--text-fg))]">{gameState.verdict.reasoning}</p>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Objection button — visible during player's turn, one-time use */}
          {isMyTurn && !isCompleted && (match.player_role === "defense_attorney" || match.player_role === "prosecutor") && (
            <div className="absolute bottom-32 right-4 sm:right-6 z-20">
              {gameState.objection_available ? (
                <button
                  onClick={handleObjection}
                  disabled={isSubmitting}
                  className="bg-red-950/80 hover:bg-red-900/90 text-red-400 font-mono font-bold text-xs py-2 px-4 sm:py-3 sm:px-6 rounded border border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.3)] hover:shadow-[0_0_35px_rgba(239,68,68,0.5)] transition-all duration-300 animate-pulse uppercase tracking-[0.15em] flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:animate-none"
                >
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                  Objection!
                </button>
              ) : (
                <span className="font-mono text-[9px] text-[rgb(var(--text-muted))] uppercase tracking-widest bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border-sub))] px-2 py-1 rounded opacity-60">
                  Objection used
                </span>
              )}
            </div>
          )}

          {/* Attached evidence chip */}
          {attachedEvidence && (
            <div className="px-4 pb-1 pt-1 flex gap-1 border-t border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-elevated))]">
              {(() => {
                const item = evidence.find((e) => String(e.id) === attachedEvidence);
                return item ? (
                  <span className="text-[9px] font-mono bg-[#DCF8C6] border border-[#A8D9AC] text-[#075E54] px-1.5 py-0.5 rounded uppercase flex items-center gap-1">
                    {item.title}
                    <button
                      onClick={() => setAttachedEvidence(null)}
                      className="ml-0.5 opacity-60 hover:opacity-100 cursor-pointer"
                    >
                      ×
                    </button>
                  </span>
                ) : null;
              })()}
            </div>
          )}

          {/* Input area */}
          <div className="p-3 sm:p-4 border-t border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-elevated))] shrink-0">
            {match.player_role === "spectator" ? (
              /* ── Pure spectator — no input ever ── */
              <div className="text-center py-2">
                <p className="text-[10px] font-mono text-[rgb(var(--text-muted))] uppercase tracking-widest flex items-center justify-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${isCompleted ? "bg-[rgb(var(--text-muted))]" : "bg-[#25D366] animate-pulse"}`} />
                  {isCompleted ? "Trial concluded — spectator view" : "Spectating live — no input required"}
                </p>
              </div>
            ) : match.player_role === "judge" && gameState.status !== "awaiting_human_verdict" && !isCompleted ? (
              /* ── Judge watching debate ── */
              <div className="text-center py-2">
                <p className="text-[10px] font-mono text-amber-700 uppercase tracking-widest flex items-center justify-center gap-2">
                  <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
                  {isSpectating ? "Observing the debate — verdict phase incoming" : "Debate concluded — deliver your verdict above"}
                </p>
              </div>
            ) : isMyTurn && gameState.status === "awaiting_human_verdict" ? (
              /* ── Judge verdict UI ── */
              <div className="space-y-3">
                <p className="text-[10px] font-mono text-amber-700 uppercase tracking-widest">
                  Deliver your verdict
                </p>
                <div className="flex gap-3">
                  {(["guilty", "not_guilty"] as const).map((v) => (
                    <button
                      key={v}
                      onClick={() => setVerdictChoice(v)}
                      disabled={isSubmitting}
                      className={`flex-1 py-2 font-mono text-xs font-bold uppercase tracking-widest rounded border transition-all cursor-pointer ${
                        verdictChoice === v
                          ? v === "guilty"
                            ? "bg-red-50 border-red-400 text-red-700"
                            : "bg-emerald-50 border-emerald-400 text-emerald-700"
                          : "bg-[rgb(var(--bg-surface))] border-[rgb(var(--border-sub))] text-[rgb(var(--text-muted))] hover:border-[#128C7E] hover:text-[rgb(var(--heading))]"
                      }`}
                    >
                      {v === "guilty" ? "Guilty" : "Not Guilty"}
                    </button>
                  ))}
                </div>
                <textarea
                  value={argumentBuffer}
                  onChange={(e) => setArgumentBuffer(e.target.value)}
                  className="w-full p-3 bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-lg text-[rgb(var(--text-fg))] font-mono text-xs focus:ring-2 focus:ring-amber-400 focus:border-amber-400 outline-none resize-none placeholder:text-[rgb(var(--text-muted))]/60"
                  placeholder="State your reasoning… (min 20 characters)"
                  rows={3}
                  disabled={isSubmitting}
                />
                <button
                  onClick={handleSubmitVerdict}
                  disabled={isSubmitting || !verdictChoice || argumentBuffer.trim().length < 20}
                  className={`w-full py-2.5 font-mono text-xs font-bold uppercase tracking-widest rounded border transition-all cursor-pointer ${
                    isSubmitting || !verdictChoice || argumentBuffer.trim().length < 20
                      ? "border-[rgb(var(--border-sub))] text-[rgb(var(--text-muted))] bg-[rgb(var(--bg-elevated))] cursor-not-allowed"
                      : "bg-amber-50 hover:bg-amber-100 text-amber-700 border-amber-400 hover:border-amber-500"
                  }`}
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-3 h-3 border-2 border-amber-300 border-t-amber-600 rounded-full animate-spin" />
                      Delivering verdict…
                    </span>
                  ) : (
                    "Deliver Verdict"
                  )}
                </button>
              </div>
            ) : (
              /* ── Normal argument UI ── */
              <>
                <div className="relative">
                  <div className="absolute left-3 top-3 font-mono text-xs text-[rgb(var(--text-muted))]/50 select-none">
                    &gt;
                  </div>
                  <textarea
                    value={argumentBuffer}
                    onChange={(e) => setArgumentBuffer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey))
                        handleSubmitArgument();
                    }}
                    className="w-full pl-7 p-3 bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-lg text-[rgb(var(--text-fg))] font-mono text-xs focus:ring-2 focus:ring-[#25D366] focus:border-[#25D366] outline-none resize-none placeholder:text-[rgb(var(--text-muted))]/60"
                    placeholder={
                      isCompleted
                        ? "Trial concluded."
                        : isSubmitting
                        ? "Transmitting…"
                        : isMyTurn
                        ? "Draft legal argument… (Ctrl+Enter to submit)"
                        : "Awaiting opponent's argument…"
                    }
                    rows={3}
                    disabled={isSubmitting || isCompleted || !isMyTurn}
                  />
                </div>
                <div className="mt-2 flex justify-between items-center gap-2">
                  <span className="text-[10px] font-mono text-[rgb(var(--text-muted))] uppercase shrink-0">
                    {isCompleted
                      ? "Trial Complete"
                      : isSubmitting
                      ? "Transmitting..."
                      : isMyTurn
                      ? "Ready to transmit"
                      : "Waiting for opponent"}
                  </span>
                  <button
                    onClick={handleSubmitArgument}
                    disabled={isSubmitting || isCompleted || !argumentBuffer.trim() || !isMyTurn}
                    className={`px-4 sm:px-6 py-2 font-mono text-xs font-bold uppercase tracking-wider rounded border transition-all cursor-pointer ${
                      isSubmitting || isCompleted || !argumentBuffer.trim() || !isMyTurn
                        ? "border-[rgb(var(--border-sub))] text-[rgb(var(--text-muted))] bg-[rgb(var(--bg-elevated))] cursor-not-allowed"
                        : "bg-[#25D366] text-white hover:bg-[#128C7E] shadow-sm border-transparent"
                    }`}
                  >
                    {isSubmitting ? (
                      <span className="flex items-center gap-2">
                        <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Transmitting
                      </span>
                    ) : (
                      "Transmit"
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </section>

        {/* Right: Evidence Vault */}
        <aside
          className={`w-full md:w-72 md:shrink-0 p-4 border-l border-[rgb(var(--border-sub))] bg-[rgb(var(--bg-elevated))] overflow-y-auto ${
            mobilePanelTab === "evidence" ? "block" : "hidden md:block"
          }`}
        >
          <EvidenceVault
            items={evidence}
            onAttach={isMyTurn && !isSubmitting ? handleAttach : undefined}
            attachedId={attachedEvidence}
          />
        </aside>
      </div>
    </div>
  );
}
